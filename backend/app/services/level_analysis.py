"""Análise de nível: o modelo lê a conversa e o app confere o resultado antes de guardar.

O modelo propõe o nível, os pontos fortes e as melhorias. O app:
- recalcula a confiança pelas contagens (falas úteis e dúvidas de transcrição), sem confiar no modelo;
- descarta as citações que não existem literalmente na fala do aluno;
- guarda o resultado com a sessão, para acompanhar a evolução.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.repositories.settings_repo import ProfileRepository, SettingsRepository
from app.services.conversation_service import BadRequest, NotFound
from app.services.llm_service import OllamaClient
from app.services.teacher_response import parse_json_object

log = logging.getLogger(__name__)

LEVELS = ("A1", "A2", "B1", "B2", "C1")
CRITERIA = ("vocabulary", "grammar", "fluency", "interaction", "coherence")
MIN_WORDS_PER_USEFUL_TURN = 4
MAX_MESSAGES_SENT = 80  # conversas mais longas enviam só as falas mais recentes

_LEVEL = {"type": "string", "enum": list(LEVELS)}
_EVIDENCE = {
    "type": "object",
    "properties": {"message_id": {"type": "integer"}, "quote": {"type": "string"}},
    "required": ["message_id", "quote"],
}

ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "level_estimate": _LEVEL,
        "confidence": {"type": "string", "enum": ["baixa", "média", "alta"]},
        "level_reasoning_pt": {"type": "string"},
        "level_vs_declared_pt": {"type": "string"},
        "criteria": {
            "type": "object",
            "properties": {c: _LEVEL for c in CRITERIA},
            "required": list(CRITERIA),
        },
        "strengths": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"text_pt": {"type": "string"}, "evidence": _EVIDENCE},
                "required": ["text_pt", "evidence"],
            },
        },
        "improvement_points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priority": {"type": "string", "enum": ["alta", "média", "baixa"]},
                    "area": {
                        "type": "string",
                        "enum": ["grammar", "vocabulary", "fluency", "interaction", "coherence", "other"],
                    },
                    "issue_pt": {"type": "string"},
                    "evidence": _EVIDENCE,
                    "suggestion_pt": {"type": "string"},
                    "better_example": {"type": "string"},
                    "practice_pt": {"type": "string"},
                },
                "required": ["priority", "area", "issue_pt", "evidence", "suggestion_pt", "better_example", "practice_pt"],
            },
        },
        "transcription_doubts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "message_id": {"type": "integer"},
                    "quote": {"type": "string"},
                    "note_pt": {"type": "string"},
                },
                "required": ["message_id", "quote", "note_pt"],
            },
        },
        "next_step_pt": {"type": "string"},
    },
    "required": [
        "level_estimate",
        "confidence",
        "level_reasoning_pt",
        "level_vs_declared_pt",
        "criteria",
        "strengths",
        "improvement_points",
        "transcription_doubts",
        "next_step_pt",
    ],
}


# ----- regras que o app aplica (independentes do modelo) ----------------------

def useful_student_turns(messages: list[dict[str, Any]]) -> int:
    """Falas do aluno com pelo menos 4 palavras (respostas de uma ou duas palavras não contam)."""
    return sum(
        1 for m in messages if m["role"] == "student" and len(m["text"].split()) >= MIN_WORDS_PER_USEFUL_TURN
    )


def confidence_for(useful_turns: int, doubts: int) -> str:
    """Confiança fixa: depende só de quantas falas úteis e de quantas dúvidas de transcrição."""
    if useful_turns < 5 or doubts > 5:
        return "baixa"
    if useful_turns >= 10 and doubts <= 2:
        return "alta"
    return "média"


def keep_verified_evidence(result: dict[str, Any], messages: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    """Mantém só as citações que aparecem literalmente na fala do aluno indicada.

    Devolve o resultado ajustado e o número de itens removidos por citação inválida.
    """
    student_text = {m["id"]: m["text"] for m in messages if m["role"] == "student"}

    def verified(evidence: dict[str, Any]) -> bool:
        quote = (evidence.get("quote") or "").strip()
        text = student_text.get(evidence.get("message_id"))
        return bool(quote) and text is not None and quote in text

    removed = 0
    strengths = []
    for item in result.get("strengths", []):
        if verified(item.get("evidence", {})):
            strengths.append(item)
        else:
            removed += 1
    improvements = []
    for item in result.get("improvement_points", []):
        if verified(item.get("evidence", {})):
            improvements.append(item)
        else:
            removed += 1
    result["strengths"] = strengths
    result["improvement_points"] = improvements[:3]
    return result, removed


def build_model_input(
    messages: list[dict[str, Any]], *, mode: str, scenario: str | None, declared_level: str
) -> dict[str, Any]:
    """Entrada no formato do prompt: papéis 'student' e 'teacher', ids reais das mensagens."""
    recent = messages[-MAX_MESSAGES_SENT:]
    return {
        "mode": mode,
        "scenario": scenario,
        "declared_level": declared_level,
        "messages": [
            {"id": m["id"], "role": "student" if m["role"] == "user" else "teacher", "text": m["content"]}
            for m in recent
        ],
    }


# ----- serviço ------------------------------------------------------------------

class LevelAnalysisService:
    def __init__(
        self,
        *,
        sessions: Any,
        profiles: ProfileRepository,
        settings: SettingsRepository,
        llm: OllamaClient,
        repo: Any,
        prompt_path: Path,
        default_model: str,
    ) -> None:
        self._sessions = sessions
        self._profiles = profiles
        self._settings = settings
        self._llm = llm
        self._repo = repo
        self._prompt_path = prompt_path
        self._default_model = default_model

    def analyze(self, session_id: int) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFound("Sessão não encontrada.")
        messages = self._sessions.list_messages(session_id)
        profile = self._profiles.get() or {"level": "A1"}
        case = build_model_input(
            messages, mode=session["mode"], scenario=session.get("scenario"), declared_level=profile["level"]
        )
        useful = useful_student_turns(case["messages"])
        if useful == 0:
            raise BadRequest("A conversa ainda não tem falas suficientes do aluno para analisar.")

        settings = self._settings.get_all()
        prompt = self._prompt_path.read_text(encoding="utf-8")
        raw = self._llm.chat(
            model=settings["llm_model"] or self._default_model,
            messages=[{"role": "user", "content": prompt + "\n\nENTRADA:\n" + json.dumps(case, ensure_ascii=False)}],
            format_schema=ANALYSIS_SCHEMA,
            temperature=0.2,
            num_ctx=int(settings["llm_num_ctx"]),
        )
        data = parse_json_object(raw)
        if data is None or not _has_required_shape(data):
            raise BadRequest("A análise não voltou no formato esperado. Tente de novo.")

        data, removed = keep_verified_evidence(data, case["messages"])
        doubts = len(data.get("transcription_doubts", []))
        data["confidence"] = confidence_for(useful, doubts)  # o app define a confiança, não o modelo
        data["student_turns"] = useful
        data["removed_citations"] = removed
        analysis_id = self._repo.add(
            session_id=session_id,
            model=settings["llm_model"] or self._default_model,
            declared_level=profile["level"],
            level_estimate=data["level_estimate"],
            confidence=data["confidence"],
            student_turns=useful,
            payload=data,
        )
        log.info("Análise %s criada para a sessão %s (removidas %s citações)", analysis_id, session_id, removed)
        return {"id": analysis_id, "session_id": session_id, **data}


def _has_required_shape(data: dict[str, Any]) -> bool:
    return (
        data.get("level_estimate") in LEVELS
        and isinstance(data.get("criteria"), dict)
        and all(data["criteria"].get(c) in LEVELS for c in CRITERIA)
        and isinstance(data.get("strengths"), list)
        and isinstance(data.get("improvement_points"), list)
        and isinstance(data.get("transcription_doubts", []), list)
        and isinstance(data.get("next_step_pt"), str)
    )
