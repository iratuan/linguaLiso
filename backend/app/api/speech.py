"""Ponte para o servidor de voz (ai-model). O áudio é repassado sem ser salvo em disco."""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_container
from app.container import Container
from app.languages import LANGUAGES

router = APIRouter(prefix="/speech", tags=["voz"])

ALLOWED_AUDIO_TYPES = {
    "audio/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/mp4",
    "audio/mpeg",
    "application/octet-stream",
}


class SynthesizeIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    voice: str | None = None
    rate: float | None = Field(default=None, ge=0.5, le=2.0)
    volume: float | None = Field(default=None, ge=0.0, le=1.0)


@router.get("/status")
def speech_status(c: Container = Depends(get_container)) -> dict[str, Any]:
    status = c.speech.status()
    return {
        "reachable": status.reachable,
        "stt_ready": status.stt_ready,
        "tts_ready": status.tts_ready,
        "message": status.message,
    }


@router.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), c: Container = Depends(get_container)) -> dict[str, Any]:
    content_type = (audio.content_type or "").split(";")[0].strip().lower()
    if content_type and content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Formato de áudio não suportado.")

    data = await audio.read(c.config.max_audio_bytes + 1)
    if len(data) > c.config.max_audio_bytes:
        raise HTTPException(status_code=413, detail="A gravação é grande demais.")
    if not data:
        raise HTTPException(status_code=400, detail="A gravação está vazia. Fale algo e tente de novo.")

    # Chamada HTTP síncrona executada em threadpool para não bloquear o event loop.
    language = c.settings.get_all().get("target_language") or "en"
    return await run_in_threadpool(
        c.speech.transcribe, data, audio.filename or "recording.webm", content_type or "audio/webm", language
    )


@router.post("/synthesize")
def synthesize(body: SynthesizeIn, c: Container = Depends(get_container)) -> Response:
    settings = c.settings.get_all()
    # Sem voz escolhida, usa a voz do idioma-alvo (ver app/languages.py).
    default_voice = LANGUAGES[settings.get("target_language") or "en"].voice
    audio = c.speech.synthesize(
        body.text,
        voice=body.voice or settings.get("speech_voice") or default_voice,
        rate=body.rate if body.rate is not None else float(settings["speech_rate"]),
        volume=body.volume if body.volume is not None else float(settings["speech_volume"]),
    )
    return Response(content=audio, media_type="audio/wav")
