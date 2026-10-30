"""Trilha de curso: visão geral, lições, correção de exercícios e conclusão."""

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.container import Container

router = APIRouter(prefix="/course", tags=["curso"])


class CheckIn(BaseModel):
    # Múltipla escolha envia o índice (int); os demais tipos enviam texto.
    answer: str | int | None = Field(default=None)


@router.get("")
def overview(c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.course.overview()


@router.get("/lessons/{lesson_id}")
def lesson(lesson_id: str, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.course.lesson(lesson_id)


@router.post("/lessons/{lesson_id}/retry")
def retry(lesson_id: str, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.course.retry(lesson_id)


@router.post("/lessons/{lesson_id}/complete")
def complete(lesson_id: str, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.course.complete(lesson_id)


@router.post("/exercises/{exercise_id}/check")
def check(exercise_id: str, body: CheckIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.course.check(exercise_id, body.answer)


@router.get("/exercises/{exercise_id}/audio")
def exercise_audio(exercise_id: str, c: Container = Depends(get_container)) -> Response:
    return Response(content=c.course.listening_audio(exercise_id), media_type="audio/wav")


# ----- criação de lições (rascunhos, aprovação manual) ----------------------

class DraftRequest(BaseModel):
    level: str = Field(min_length=2, max_length=2)
    topic: str = Field(default="", max_length=120)
    count: int = Field(default=1, ge=1, le=3)


@router.get("/drafts")
def list_drafts(c: Container = Depends(get_container)) -> dict[str, Any]:
    return {"drafts": c.curriculum_builder.list_drafts()}


@router.post("/drafts")
def generate_drafts(body: DraftRequest, c: Container = Depends(get_container)) -> dict[str, Any]:
    # Geração pelo modelo local: demora alguns segundos por lição. Nada entra na trilha sem aprovação.
    return c.curriculum_builder.generate(body.level, body.topic, body.count)


@router.post("/drafts/{draft_id}/approve")
def approve_draft(draft_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.curriculum_builder.approve(draft_id)


@router.delete("/drafts/{draft_id}")
def discard_draft(draft_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    c.curriculum_builder.discard(draft_id)
    return {"ok": True}
