"""Material de apoio: transforma a conversa em um material de estudo para imprimir.

O modelo escolhe as frases das lacunas, explica a conversa e cria exercícios de fixação.
O app confere a estrutura e monta os pontos de correção e o rodapé com as palavras que o
aluno errou a partir das correções salvas, sem depender do modelo para isso.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.repositories.settings_repo import ProfileRepository, SettingsRepository
from app.services.conversation_service import BadRequest, NotFound
from app.services.llm_service import MAX_TOKENS_LONG, OllamaClient
from app.services.teacher_response import parse_json_object

log = logging.getLogger(__name__)

MAX_MESSAGES_SENT = 80
MIN_ITEMS = 1
MAX_ITEMS = 10
MAX_TIPS = 6
MAX_CORRECTIONS = 10
MAX_SUMMARY_POINTS = 6
MAX_EXERCISES = 6
EXERCISE_KINDS = ("translate", "multiple_choice")
_BLANK_RE = re.compile(r"_{3,}")

MATERIAL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "instructions_pt": {"type": "string"},
        "word_bank": {"type": "array", "items": {"type": "string"}},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentence": {"type": "string"},
                    "answers": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["sentence", "answers"],
            },
        },
        "summary_points_pt": {"type": "array", "items": {"type": "string"}},
        "exercises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(EXERCISE_KINDS)},
                    "prompt": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "answer": {"type": "string"},
                },
                "required": ["kind", "prompt", "answer"],
            },
        },
        "footer_title_pt": {"type": "string"},
    },
    "required": [
        "title",
        "instructions_pt",
        "word_bank",
        "items",
        "summary_points_pt",
        "exercises",
        "footer_title_pt",
    ],
}


def material_input(
    *,
    language: str,
    level: str,
    messages: list[dict[str, Any]],
    corrections: list[dict[str, Any]],
    vocabulary: list[dict[str, Any]],
) -> dict[str, Any]:
    """Entrada no formato do prompt. Usa só as falas mais recentes para caber no contexto."""
    recent = messages[-MAX_MESSAGES_SENT:]
    return {
        "language": language,
        "level": level,
        "messages": [
            {"id": m["id"], "role": "student" if m["role"] == "user" else "teacher", "text": m["content"]}
            for m in recent
            if m["role"] in ("user", "assistant")
        ],
        "corrections": [
            {
                "message_id": c["message_id"],
                "original_text": c["original_text"],
                "corrected_text": c["corrected_text"],
                "explanation_pt": c["explanation_pt"],
                "error_category": c["error_category"],
                "severity": c["severity"],
            }
            for c in corrections
        ],
        "new_vocabulary": [
            {"term": v["term"], "translation_pt": v["translation_pt"], "example_sentence": v["example_sentence"]}
            for v in vocabulary
        ],
    }


def _distinct_corrections(corrections: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Uma entrada por erro distinto, na ordem em que aconteceram, sem inventar nada.

    Usa as correções que a própria conversa gerou, então a forma errada é a que o aluno
    escreveu e a forma certa é a que o professor corrigiu.
    """
    distinct: list[dict[str, str]] = []
    seen: set[str] = set()
    for c in corrections:
        wrong = (c.get("original_text") or "").strip()
        right = (c.get("corrected_text") or "").strip()
        if not wrong or not right or wrong == right:
            continue
        key = wrong.lower()
        if key in seen:
            continue
        seen.add(key)
        distinct.append({"wrong": wrong, "right": right, "explanation_pt": (c.get("explanation_pt") or "").strip()})
    return distinct


def tips_from_corrections(corrections: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Rodapé: as primeiras correções distintas, em formato curto."""
    return [
        {"wrong": d["wrong"], "right": d["right"], "tip_pt": d["explanation_pt"]}
        for d in _distinct_corrections(corrections)[:MAX_TIPS]
    ]


def correction_points(corrections: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Seção "Pontos de correção": cada erro com a explicação completa do professor."""
    return _distinct_corrections(corrections)[:MAX_CORRECTIONS]


def validate_summary(points: Any) -> list[str]:
    """Explicação da conversa: só frases não vazias, no máximo MAX_SUMMARY_POINTS."""
    if not isinstance(points, list):
        return []
    cleaned = [str(p).strip() for p in points if isinstance(p, str) and p.strip()]
    return cleaned[:MAX_SUMMARY_POINTS]


def validate_exercises(exercises: Any) -> list[dict[str, Any]]:
    """Mantém só exercícios completos e coerentes.

    - "translate": a resposta é uma frase, sem alternativas.
    - "multiple_choice": precisa de pelo menos duas alternativas, e a resposta tem de ser uma delas.
    """
    valid: list[dict[str, Any]] = []
    if not isinstance(exercises, list):
        return valid
    for ex in exercises:
        if not isinstance(ex, dict):
            continue
        kind = ex.get("kind")
        prompt = ex.get("prompt")
        answer = ex.get("answer")
        if kind not in EXERCISE_KINDS or not isinstance(prompt, str) or not prompt.strip():
            continue
        if not isinstance(answer, str) or not answer.strip():
            continue
        prompt, answer = prompt.strip(), answer.strip()
        if kind == "translate":
            valid.append({"kind": kind, "prompt": prompt, "options": [], "answer": answer})
            continue
        options = [str(o).strip() for o in ex.get("options") or [] if str(o).strip()]
        if len(options) < 2 or answer not in options:
            continue
        valid.append({"kind": kind, "prompt": prompt, "options": options, "answer": answer})
    return valid[:MAX_EXERCISES]


def validate_items(items: Any) -> list[dict[str, Any]]:
    """Mantém só os itens cujo número de lacunas bate com o número de respostas."""
    valid: list[dict[str, Any]] = []
    if not isinstance(items, list):
        return valid
    for item in items:
        if not isinstance(item, dict):
            continue
        sentence = item.get("sentence")
        answers = item.get("answers")
        if not isinstance(sentence, str) or not isinstance(answers, list) or not answers:
            continue
        answers = [str(a).strip() for a in answers]
        if not all(answers) or len(_BLANK_RE.findall(sentence)) != len(answers):
            continue
        valid.append({"sentence": sentence.strip(), "answers": answers})
    return valid[:MAX_ITEMS]


class StudyMaterialService:
    def __init__(
        self,
        *,
        sessions: Any,
        vocabulary: Any,
        profiles: ProfileRepository,
        settings: SettingsRepository,
        llm: OllamaClient,
        prompt_path: Path,
        default_model: str,
    ) -> None:
        self._sessions = sessions
        self._vocabulary = vocabulary
        self._profiles = profiles
        self._settings = settings
        self._llm = llm
        self._prompt_path = prompt_path
        self._default_model = default_model

    def build(self, session_id: int) -> dict[str, Any]:
        session = self._sessions.get(session_id)
        if session is None:
            raise NotFound("Sessão não encontrada.")
        messages = self._sessions.list_messages(session_id)
        corrections = self._sessions.list_corrections(session_id)
        if not any(m["role"] == "user" for m in messages):
            raise BadRequest("A conversa ainda não tem falas suas para gerar o material.")

        profile = self._profiles.get() or {"level": "A1"}
        language = session.get("language") or "en"
        case = material_input(
            language=language,
            level=session["level"] or profile["level"],
            messages=messages,
            corrections=corrections,
            vocabulary=self._vocabulary.list_for_session(session_id),
        )

        settings = self._settings.get_all()
        prompt = self._prompt_path.read_text(encoding="utf-8")
        raw = self._llm.chat(
            model=settings["llm_model"] or self._default_model,
            messages=[{"role": "user", "content": prompt + "\n\nENTRADA:\n" + json.dumps(case, ensure_ascii=False)}],
            format_schema=MATERIAL_SCHEMA,
            temperature=0.4,
            num_ctx=int(settings["llm_num_ctx"]),
            max_tokens=MAX_TOKENS_LONG,
        )
        data = parse_json_object(raw)
        items = validate_items(data.get("items")) if data else []
        if len(items) < MIN_ITEMS:
            raise BadRequest("O material não voltou no formato esperado. Tente de novo.")

        word_bank = [str(w).strip() for w in data.get("word_bank", []) if str(w).strip()]
        log.info("Material gerado para a sessão %s (%s itens)", session_id, len(items))
        return {
            "session_id": session_id,
            "language": language,
            "level": session["level"],
            "title": str(data.get("title") or session["title"]).strip(),
            "instructions_pt": str(data.get("instructions_pt") or "").strip(),
            "word_bank": word_bank if session["level"] in ("A1", "A2") else [],
            "items": items,
            "summary_points_pt": validate_summary(data.get("summary_points_pt")),
            "exercises": validate_exercises(data.get("exercises")),
            "corrections": correction_points(corrections),
            "footer_title_pt": str(data.get("footer_title_pt") or "Palavras para revisar").strip(),
            "tips": tips_from_corrections(corrections),
        }
