"""Criação de lições para a trilha: o modelo propõe, o app valida, e só o usuário aprova.

Fluxo: ``generate`` cria rascunhos (guardados no banco, fora da trilha); ``approve`` grava a lição
em ``<dados>/curriculo_usuario/<idioma>/<nível>.json`` e recarrega o currículo; ``discard`` apaga o rascunho.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from app.curriculum.loader import MIN_EXERCISES_PER_LESSON, CurriculumError, check_exercise, check_lesson
from app.curriculum.registry import CurriculumRegistry
from app.languages import DEFAULT_LANGUAGE, LANGUAGES
from app.repositories.course_repo import CourseRepository
from app.repositories.settings_repo import SettingsRepository
from app.services.conversation_service import BadRequest, NotFound
from app.services.llm_service import OllamaClient
from app.services.prompt_library import PromptLibrary
from app.services.teacher_response import parse_json_object

log = logging.getLogger(__name__)

LEVELS = ("A1", "A2", "B1", "B2", "C1")
MAX_COUNT = 3
MAX_ATTEMPTS_PER_LESSON = 2
USER_UNIT_TITLE = "Temas extras"
USER_LEVEL_TITLE = "Temas extras"
USER_LEVEL_DESCRIPTION = "Lições criadas por você e revisadas antes de entrar na trilha."
USER_LEVEL_GOAL = "Praticar temas à sua escolha."


class _Phrase(BaseModel):
    en: str = Field(min_length=1, max_length=200)
    pt: str = Field(default="", max_length=200)


class _Exercise(BaseModel):
    type: Literal["multiple_choice", "fill_blank", "translate", "reorder", "listen"]
    prompt: str = Field(min_length=1, max_length=400)
    options: list[str] = Field(default_factory=list, max_length=4)
    answer: int | None = None
    answers: list[str] = Field(default_factory=list, max_length=5)
    words: list[str] = Field(default_factory=list, max_length=20)
    text: str = Field(default="", max_length=300)
    hint: str = Field(default="", max_length=200)
    explanation: str = Field(default="", max_length=400)


class _Lesson(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=300)
    explanation: str = Field(min_length=1, max_length=2500)
    key_phrases: list[_Phrase] = Field(default_factory=list, max_length=6)
    exercises: list[_Exercise] = Field(min_length=4, max_length=6)


_EXERCISE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["multiple_choice", "fill_blank", "translate", "reorder", "listen"]},
        "prompt": {"type": "string"},
        "options": {"type": "array", "items": {"type": "string"}},
        "answer": {"type": "integer"},
        "answers": {"type": "array", "items": {"type": "string"}},
        "words": {"type": "array", "items": {"type": "string"}},
        "text": {"type": "string"},
        "hint": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["type", "prompt", "explanation"],
}

LESSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "objective": {"type": "string"},
        "explanation": {"type": "string"},
        "key_phrases": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"en": {"type": "string"}, "pt": {"type": "string"}},
                "required": ["en", "pt"],
            },
        },
        "exercises": {"type": "array", "items": _EXERCISE_SCHEMA},
    },
    "required": ["title", "objective", "explanation", "exercises"],
}


class CurriculumBuilder:
    def __init__(
        self,
        *,
        registry: CurriculumRegistry,
        repo: CourseRepository,
        settings: SettingsRepository,
        llm: OllamaClient,
        prompts: PromptLibrary,
        default_model: str,
        curriculum_root: Path,
        user_root: Path,
    ) -> None:
        self._registry = registry
        self._repo = repo
        self._settings = settings
        self._llm = llm
        self._prompts = prompts
        self._default_model = default_model
        self._curriculum_root = curriculum_root
        self._user_root = user_root

    # ----- geração -------------------------------------------------------------

    def generate(self, level: str, topic: str, count: int) -> dict[str, Any]:
        level = level.upper()
        if level not in LEVELS:
            raise BadRequest("Nível inválido.")
        if not 1 <= count <= MAX_COUNT:
            raise BadRequest(f"Gere de 1 a {MAX_COUNT} lições por vez.")
        settings = self._settings.get_all()
        lang = settings.get("target_language") or DEFAULT_LANGUAGE
        if lang not in self._registry.languages():
            raise BadRequest("A trilha deste idioma ainda não está disponível.")

        existing = [lesson.title for lesson in self._registry.get(lang).lessons if lesson.level == level]
        created: list[dict[str, Any]] = []
        problems: list[str] = []
        for _ in range(count):
            lesson = None
            # Uma lição pode falhar por formato; tenta de novo antes de desistir dela.
            for _attempt in range(MAX_ATTEMPTS_PER_LESSON):
                prompt = self._prompts.read(lang, "curriculum_lesson.txt").format(
                    language_name=LANGUAGES[lang].name_pt.lower(),
                    level=level,
                    topic=topic.strip() or "escolha um tema útil que ainda não esteja na trilha, em sequência lógica",
                    existing="; ".join(existing[-60:]) or "(nenhum ainda)",
                )
                raw = self._llm.chat(
                    model=settings["llm_model"] or self._default_model,
                    messages=[{"role": "user", "content": prompt}],
                    format_schema=LESSON_SCHEMA,
                    temperature=float(settings["llm_temperature"]),
                    num_ctx=int(settings["llm_num_ctx"]),
                )
                lesson = self._build(raw, lang, level, problems)
                if lesson is not None:
                    break
            if lesson is None:
                continue
            draft_id = self._repo.add_draft(lang, level, lesson["title"], lesson)
            existing.append(lesson["title"])
            created.append(_public_draft(self._repo.get_draft(draft_id)))

        # "failed" conta lições perdidas (não tentativas); "problems" mostra o motivo das falhas.
        return {"drafts": created, "failed": count - len(created), "problems": problems[:3]}

    def _build(self, raw: str, lang: str, level: str, problems: list[str]) -> dict[str, Any] | None:
        """Converte a saída do modelo numa lição válida. Exercícios inválidos são descartados,
        desde que sobrem exercícios suficientes; caso contrário a lição é recusada."""
        try:
            return _to_curriculum_lesson(raw, lang, level)
        except _LessonRejected as exc:
            problems.append(str(exc))
            return None
        except (CurriculumError, KeyError, ValueError) as exc:
            problems.append(str(exc) or "resposta fora do formato esperado")
            return None

    # ----- rascunhos -----------------------------------------------------------

    def list_drafts(self) -> list[dict[str, Any]]:
        return [_public_draft(row) for row in self._repo.list_drafts()]

    def discard(self, draft_id: int) -> None:
        if not self._repo.delete_draft(draft_id):
            raise NotFound("Rascunho não encontrado.")

    def approve(self, draft_id: int) -> dict[str, Any]:
        draft = self._repo.get_draft(draft_id)
        if draft is None:
            raise NotFound("Rascunho não encontrado.")
        lesson = draft["lesson"]
        path = self._user_file(draft["language"], draft["level"])
        previous = path.read_bytes() if path.exists() else None

        document = json.loads(previous) if previous else _new_user_level(draft["level"])
        unit_id = _user_unit_id(draft["level"])
        unit = next((u for u in document["units"] if u["id"] == unit_id), None)
        if unit is None:
            unit = {"id": unit_id, "title": USER_UNIT_TITLE, "goal": "Lições criadas por você.", "lessons": []}
            document["units"].append(unit)
        unit["lessons"].append(lesson)

        _write_atomic(path, json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8"))
        try:
            self._registry.reload(self._curriculum_root, self._user_root)
        except CurriculumError as exc:
            # Lição inválida no conjunto: volta ao estado anterior e não remove o rascunho.
            _restore(path, previous)
            raise BadRequest(f"Não foi possível adicionar a lição: {exc}") from exc

        self._repo.delete_draft(draft_id)
        return {"lesson_id": lesson["id"], "title": lesson["title"], "level": draft["level"]}

    def _user_file(self, language: str, level: str) -> Path:
        return self._user_root / language / f"{level.lower()}.json"


# ----- conversão e validação -------------------------------------------------

class _LessonRejected(ValueError):
    """Lição com poucos exercícios válidos para ser aproveitada."""


def _to_curriculum_lesson(raw: str, lang: str, level: str) -> dict[str, Any]:
    data = parse_json_object(raw)
    if data is None:
        raise ValueError("o modelo não devolveu um objeto JSON")
    try:
        draft = _Lesson.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"estrutura incompleta: {exc.errors()[0]['loc'][0]}") from exc

    lesson_id = f"usr-{lang}-{level.lower()}-{uuid.uuid4().hex[:8]}"
    exercises: list[dict[str, Any]] = []
    dropped: list[str] = []
    for i, item in enumerate(draft.exercises, start=1):
        candidate = _to_exercise(item, f"{lesson_id}-e{i}")
        try:
            check_exercise(candidate, lesson_id)
            exercises.append(candidate)
        except (CurriculumError, KeyError, ValueError) as exc:
            dropped.append(str(exc))
    if len(exercises) < MIN_EXERCISES_PER_LESSON:
        raise _LessonRejected(f"{draft.title}: exercícios inválidos ({'; '.join(dropped)[:200]})")

    lesson = {
        "id": lesson_id,
        "title": draft.title.strip(),
        "objective": draft.objective.strip(),
        "explanation": draft.explanation.strip(),
        "key_phrases": [{"en": p.en.strip(), "pt": p.pt.strip()} for p in draft.key_phrases],
        "exercises": exercises,
    }
    check_lesson(lesson, level)  # mesmas regras da trilha oficial
    return lesson


def _to_exercise(item: _Exercise, exercise_id: str) -> dict[str, Any]:
    base: dict[str, Any] = {"id": exercise_id, "type": item.type, "prompt": item.prompt.strip(),
                            "explanation": item.explanation.strip()}
    if item.hint.strip():
        base["hint"] = item.hint.strip()
    if item.type == "multiple_choice":
        base.update(options=[o.strip() for o in item.options], answer=item.answer)
    elif item.type == "reorder":
        base.update(words=[w.strip() for w in item.words], answers=[a.strip() for a in item.answers[:1]])
    elif item.type == "listen":
        text = item.text.strip()
        base.update(text=text, answers=list(dict.fromkeys([text, *[a.strip() for a in item.answers]])))
    else:
        base.update(answers=[a.strip() for a in item.answers])
    return base


def _public_draft(row: dict[str, Any]) -> dict[str, Any]:
    lesson = row["lesson"]
    return {
        "id": row["id"],
        "language": row["language"],
        "level": row["level"],
        "title": lesson["title"],
        "objective": lesson["objective"],
        "explanation": lesson["explanation"],
        "key_phrases": lesson["key_phrases"],
        "exercises": [
            {"type": ex["type"], "prompt": ex["prompt"], "explanation": ex.get("explanation", "")}
            for ex in lesson["exercises"]
        ],
        "created_at": row["created_at"],
    }


# ----- arquivos ----------------------------------------------------------------

def _user_unit_id(level: str) -> str:
    return f"{level.lower()}-usuario"


def _new_user_level(level: str) -> dict[str, Any]:
    return {
        "level": level,
        "title": USER_LEVEL_TITLE,
        "description": USER_LEVEL_DESCRIPTION,
        "goal": USER_LEVEL_GOAL,
        "units": [],
    }


def _write_atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, path)


def _restore(path: Path, previous: bytes | None) -> None:
    if previous is None:
        path.unlink(missing_ok=True)
    else:
        _write_atomic(path, previous)
