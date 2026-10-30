"""Privacidade: exportação do histórico em JSON aberto e exclusão dos dados do aluno."""

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.api.deps import get_container
from app.container import Container

router = APIRouter(prefix="/data", tags=["dados"])

CONFIRMATION_TEXT = "APAGAR MEUS DADOS"


class DeleteIn(BaseModel):
    confirm: str


@router.get("/export")
def export_data(c: Container = Depends(get_container)) -> Response:
    payload = c.progress.export_all()
    body = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    filename = f"english-teacher-export-{datetime.now():%Y%m%d-%H%M%S}.json"
    return Response(
        content=body,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/delete")
def delete_data(body: DeleteIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    if body.confirm != CONFIRMATION_TEXT:
        raise HTTPException(status_code=400, detail=f"Para confirmar, envie exatamente: {CONFIRMATION_TEXT}")
    c.progress.delete_learner_data()
    return {"deleted": True}
