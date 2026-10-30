"""Sessões de conversa e turnos com o professor."""

from typing import Any

from fastapi import APIRouter, Depends, Response

from app.api.deps import get_container
from app.container import Container
from app.domain import MessageCreate, SessionCreate

router = APIRouter(prefix="/sessions", tags=["conversa"])


@router.get("")
def list_sessions(limit: int = 50, c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    return c.sessions.list_recent(limit=min(max(limit, 1), 200))


@router.post("", status_code=201)
def create_session(body: SessionCreate, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.conversation.create_session(body)


@router.get("/{session_id}")
def get_session(session_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.conversation.transcript(session_id)


@router.post("/{session_id}/messages")
def send_message(session_id: int, body: MessageCreate, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.conversation.send_message(session_id, body)


@router.post("/{session_id}/end")
def end_session(session_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.conversation.end_session(session_id)


@router.post("/{session_id}/study-material")
def study_material(session_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    # Leva alguns segundos (modelo local). Nada é guardado: o material é gerado sob demanda para imprimir.
    return c.study_material.build(session_id)


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, c: Container = Depends(get_container)) -> Response:
    c.conversation.delete_session(session_id)
    return Response(status_code=204)
