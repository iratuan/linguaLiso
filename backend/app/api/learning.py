"""Vocabulário, revisão espaçada, aulas guiadas e progresso."""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.container import Container
from app.services.conversation_service import NotFound
from app.services.evolution import build_evolution

router = APIRouter(tags=["aprendizagem"])


class VocabularyCreate(BaseModel):
    term: str = Field(min_length=1, max_length=80)
    translation_pt: str = Field(default="", max_length=200)
    example_sentence: str = Field(default="", max_length=300)


class ReviewIn(BaseModel):
    rating: Literal["forgot", "hard", "good"]


class LessonCreate(BaseModel):
    objective: str = Field(min_length=3, max_length=300)
    exercise_count: int = Field(default=3, ge=1, le=8)


class AnswerIn(BaseModel):
    position: int = Field(ge=1, le=8)
    answer: str = Field(min_length=1, max_length=500)


# ----- vocabulário ---------------------------------------------------------

@router.get("/vocabulary")
def list_vocabulary(due_only: bool = False, c: Container = Depends(get_container)) -> dict[str, Any]:
    return {"items": c.vocabulary.list_items(due_only=due_only), "counts": c.vocabulary.counts()}


@router.post("/vocabulary", status_code=201)
def create_vocabulary(body: VocabularyCreate, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.vocabulary.create(body.term.strip(), body.translation_pt, body.example_sentence)


@router.post("/vocabulary/{item_id}/review")
def review_vocabulary(item_id: int, body: ReviewIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        return c.vocabulary.record_review(item_id, body.rating)
    except LookupError as exc:
        raise NotFound("Item de vocabulário não encontrado.") from exc


@router.delete("/vocabulary/{item_id}", status_code=204)
def delete_vocabulary(item_id: int, c: Container = Depends(get_container)) -> Response:
    if not c.vocabulary.delete(item_id):
        raise NotFound("Item de vocabulário não encontrado.")
    return Response(status_code=204)


# ----- aulas guiadas ------------------------------------------------------

@router.get("/lessons")
def list_lessons(c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    return c.lesson_service.list_recent()


@router.post("/lessons", status_code=201)
def create_lesson(body: LessonCreate, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.lesson_service.create(body.objective, body.exercise_count)


@router.get("/lessons/{lesson_id}")
def get_lesson(lesson_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.lesson_service.get(lesson_id)


@router.post("/lessons/{lesson_id}/answers")
def answer_lesson(lesson_id: int, body: AnswerIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.lesson_service.answer(lesson_id, body.position, body.answer)


@router.post("/lessons/{lesson_id}/complete")
def complete_lesson(lesson_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.lesson_service.complete(lesson_id)


# ----- progresso e erros --------------------------------------------------

@router.get("/progress")
def progress(c: Container = Depends(get_container)) -> dict[str, Any]:
    summary = c.progress.summary()
    summary["vocabulary"] = c.vocabulary.counts()
    summary["profile"] = c.profiles.get()
    return summary


@router.get("/progress/evolution")
def evolution(days: int = 60, c: Container = Depends(get_container)) -> dict[str, Any]:
    """Séries diárias para a curva de aprendizado: acertos, frases, vocabulário e lições."""
    days = min(max(days, 7), 365)
    today = datetime.now(timezone.utc).date()
    since = (today - timedelta(days=days - 1)).isoformat() + "T00:00:00+00:00"
    lessons = c.progress.lessons_completed()
    return build_evolution(
        today=today,
        days=days,
        messages=c.progress.user_messages_since(since),
        corrections=c.progress.corrections_since(since),
        attempts=c.progress.attempts_since(since),
        vocabulary=c.progress.vocabulary_since(since),
        lessons=lessons,
        lesson_titles={lesson.id: lesson.title for lesson in c.curriculum.all_lessons()},
    )


@router.get("/errors/recurring")
def recurring_errors(c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    return c.progress.recurring_errors()
