"""Treino de repetição: contextos com frases, pontuação da fala transcrita."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.container import Container
from app.languages import DEFAULT_LANGUAGE
from app.services.drills import find_pack, load_packs, score_transcript

router = APIRouter(prefix="/drills", tags=["treino"])


class ScoreIn(BaseModel):
    pack_id: str = Field(min_length=1, max_length=80)
    sentence_index: int = Field(ge=0, le=200)
    transcript: str = Field(default="", max_length=500)


def _language(c: Container) -> str:
    return c.settings.get_all().get("target_language") or DEFAULT_LANGUAGE


@router.get("")
def list_packs(c: Container = Depends(get_container)) -> dict[str, Any]:
    language = _language(c)
    return {
        "language": language,
        "packs": [
            {
                "id": p["id"],
                "title": p["title"],
                "level": p["level"],
                "context": p["context"],
                "sentence_count": len(p["sentences"]),
            }
            for p in load_packs(language)
        ],
    }


@router.get("/{pack_id}")
def get_pack(pack_id: str, c: Container = Depends(get_container)) -> dict[str, Any]:
    pack = find_pack(_language(c), pack_id)
    if pack is None:
        raise HTTPException(status_code=404, detail="Contexto não encontrado.")
    return pack


@router.post("/score")
def score(body: ScoreIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    language = _language(c)
    pack = find_pack(language, body.pack_id)
    if pack is None or body.sentence_index >= len(pack["sentences"]):
        raise HTTPException(status_code=404, detail="Frase não encontrada.")
    expected = pack["sentences"][body.sentence_index]["text"]
    return {"expected": expected, **score_transcript(expected, body.transcript, language)}
