"""Análise de nível das conversas: executar, listar e abrir."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_container
from app.container import Container

router = APIRouter(tags=["análise"])


@router.post("/sessions/{session_id}/analysis")
def analyze_session(session_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    # Leva alguns segundos (modelo local). A análise só é guardada depois de passar pelas verificações.
    return c.level_analysis.analyze(session_id)


@router.get("/analyses")
def list_analyses(c: Container = Depends(get_container)) -> dict[str, Any]:
    return {"analyses": c.analyses.list_recent()}


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: int, c: Container = Depends(get_container)) -> dict[str, Any]:
    analysis = c.analyses.get(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    return analysis
