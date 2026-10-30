"""Aulas guiadas: geração pela LLM, correção de exercícios e resumo."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.repositories.lesson_repo import LessonRepository
from app.repositories.settings_repo import ProfileRepository, SettingsRepository
from app.services.conversation_service import BadRequest, Conflict, NotFound
from app.services.llm_service import MAX_TOKENS_LONG, OllamaClient
from app.services.prompt_library import PromptLibrary
from app.services.teacher_response import parse_json_object


class ExerciseDraft(BaseModel):
    prompt: str = Field(min_length=1, max_length=400)
    expected_answer: str = Field(default="", max_length=400)


class LessonDraft(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1, max_length=300)
    content_md: str = Field(default="", max_length=4000)
    exercises: list[ExerciseDraft] = Field(min_length=1, max_length=8)


class AnswerVerdict(BaseModel):
    is_correct: bool
    feedback_pt: str = Field(default="", max_length=600)


LESSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "objective": {"type": "string"},
        "content_md": {"type": "string"},
        "exercises": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"prompt": {"type": "string"}, "expected_answer": {"type": "string"}},
                "required": ["prompt", "expected_answer"],
            },
        },
    },
    "required": ["title", "objective", "content_md", "exercises"],
}

VERDICT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"is_correct": {"type": "boolean"}, "feedback_pt": {"type": "string"}},
    "required": ["is_correct", "feedback_pt"],
}


class LessonService:
    def __init__(
        self,
        *,
        lessons: LessonRepository,
        profiles: ProfileRepository,
        settings: SettingsRepository,
        llm: OllamaClient,
        prompts: PromptLibrary,
        default_model: str,
    ) -> None:
        self._lessons = lessons
        self._profiles = profiles
        self._settings = settings
        self._llm = llm
        self._prompts = prompts
        self._default_model = default_model

    def _model(self) -> str:
        return self._settings.get_all()["llm_model"] or self._default_model

    def create(self, objective: str, exercise_count: int) -> dict[str, Any]:
        objective = objective.strip()
        if not objective:
            raise BadRequest("Informe o tema da aula.")
        profile = self._profiles.get() or {"level": "A1", "english_variant": "american"}
        settings = self._settings.get_all()
        lang = settings.get("target_language") or "en"
        prompt = self._prompts.lesson_prompt(lang).format(
            level=profile["level"],
            variant="americano" if profile["english_variant"] == "american" else "britânico",
            objective=objective,
            exercise_count=exercise_count,
        )
        raw = self._llm.chat(
            model=self._model(),
            messages=[{"role": "user", "content": prompt}],
            format_schema=LESSON_SCHEMA,
            temperature=float(settings["llm_temperature"]),
            num_ctx=int(settings["llm_num_ctx"]),
            max_tokens=MAX_TOKENS_LONG,
        )
        draft = _validate(raw, LessonDraft, "A aula gerada não tem a estrutura esperada. Tente outro tema.")
        exercises = [e.model_dump() for e in draft.exercises][:exercise_count]
        lesson_id = self._lessons.create(
            title=draft.title,
            objective=draft.objective,
            content_md=draft.content_md,
            exercises=exercises,
        )
        lesson = self.get(lesson_id)
        return lesson

    def get(self, lesson_id: int) -> dict[str, Any]:
        lesson = self._lessons.get(lesson_id)
        if lesson is None:
            raise NotFound("Aula não encontrada.")
        return lesson

    def list_recent(self) -> list[dict[str, Any]]:
        return self._lessons.list_recent()

    def answer(self, lesson_id: int, position: int, answer: str) -> dict[str, Any]:
        lesson = self.get(lesson_id)
        if lesson["status"] == "completed":
            raise Conflict("Esta aula já foi concluída.")
        exercise = self._lessons.get_exercise(lesson_id, position)
        if exercise is None:
            raise NotFound("Exercício não encontrado.")
        if exercise["answered_at"] is not None:
            raise Conflict("Este exercício já foi respondido.")
        answer = answer.strip()
        if not answer:
            raise BadRequest("Escreva uma resposta antes de enviar.")

        settings = self._settings.get_all()
        lang = settings.get("target_language") or "en"
        prompt = self._prompts.lesson_check_prompt(lang).format(
            prompt=exercise["prompt"], expected=exercise["expected_answer"], answer=answer
        )
        raw = self._llm.chat(
            model=self._model(),
            messages=[{"role": "user", "content": prompt}],
            format_schema=VERDICT_SCHEMA,
            temperature=0.1,
            num_ctx=int(settings["llm_num_ctx"]),
        )
        verdict = _validate(raw, AnswerVerdict, "Não consegui avaliar sua resposta. Tente enviar de novo.")
        self._lessons.save_answer(lesson_id, position, answer, verdict.is_correct, verdict.feedback_pt)
        return self.get(lesson_id)

    def complete(self, lesson_id: int) -> dict[str, Any]:
        lesson = self.get(lesson_id)
        if lesson["status"] == "completed":
            raise Conflict("Esta aula já foi concluída.")
        answered = [e for e in lesson["exercises"] if e["answered_at"] is not None]
        if not answered:
            raise BadRequest("Responda pelo menos um exercício antes de concluir a aula.")
        correct = sum(1 for e in answered if e["is_correct"])
        summary = f"Acertos: {correct} de {len(lesson['exercises'])} exercícios."
        self._lessons.complete(lesson_id, summary)
        return self.get(lesson_id)


def _validate(raw: str, model: type[BaseModel], error_message: str):
    data = parse_json_object(raw)
    if data is None:
        raise LessonOutputError(error_message)
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise LessonOutputError(error_message) from exc


class LessonOutputError(Exception):
    pass
