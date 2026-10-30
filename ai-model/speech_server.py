"""Servidor de voz local (componente ai-model): faster-whisper (STT) e Piper (TTS).

Roda somente em 127.0.0.1. Nenhuma chamada externa é feita durante o uso: os
modelos precisam estar baixados antes (ver scripts/setup_models.ps1).

Endpoints:
  GET  /health        estado dos componentes (não carrega modelos)
  POST /transcribe    multipart com o campo "audio" (WebM, WAV, OGG...) -> texto
  POST /synthesize    JSON {text, voice, rate, volume} -> WAV

Execução:
  .venv\\Scripts\\python.exe -m uvicorn speech_server:app --host 127.0.0.1 --port 8001
"""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import os
import threading
import wave
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

AI_MODEL_DIR = Path(__file__).resolve().parent
log = logging.getLogger("speech")


def _load_catalog() -> dict[str, Any]:
    path = AI_MODEL_DIR / "models.json"
    return json.loads(path.read_text(encoding="utf-8"))


CATALOG = _load_catalog()
STT_MODEL = os.environ.get("ETL_STT_MODEL", CATALOG["stt"]["model"])
STT_DEVICE = os.environ.get("ETL_STT_DEVICE", CATALOG["stt"]["device"])
STT_COMPUTE = os.environ.get("ETL_STT_COMPUTE_TYPE", CATALOG["stt"]["compute_type"])
STT_DOWNLOAD_ROOT = os.environ.get("ETL_MODELS_DIR", str(AI_MODEL_DIR / "models" / "whisper"))
VOICES_DIR = Path(os.environ.get("ETL_VOICES_DIR", AI_MODEL_DIR / CATALOG["tts"]["voices_dir"]))
DEFAULT_VOICE = os.environ.get("ETL_DEFAULT_VOICE", CATALOG["tts"]["voice"])
MAX_AUDIO_BYTES = int(os.environ.get("ETL_MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
MAX_TTS_CHARS = 1000
NO_SPEECH_THRESHOLD = 0.6  # segmentos com alta probabilidade de silêncio são descartados


class SynthesizeIn(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TTS_CHARS)
    voice: str | None = None
    rate: float = Field(default=1.0, ge=0.5, le=2.0)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class ModelHolder:
    """Carrega cada modelo uma única vez e reutiliza a instância."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._stt = None
        self._voices: dict[str, Any] = {}

    def stt(self):
        with self._lock:
            if self._stt is None:
                from faster_whisper import WhisperModel

                log.info("Carregando Whisper %s (%s, %s)", STT_MODEL, STT_DEVICE, STT_COMPUTE)
                self._stt = WhisperModel(
                    STT_MODEL,
                    device=STT_DEVICE,
                    compute_type=STT_COMPUTE,
                    download_root=STT_DOWNLOAD_ROOT,
                    local_files_only=True,  # nunca baixar durante o uso
                )
            return self._stt

    def voice(self, name: str):
        with self._lock:
            if name not in self._voices:
                model_path = _voice_path(name)
                from piper import PiperVoice

                log.info("Carregando voz Piper %s", name)
                self._voices[name] = PiperVoice.load(model_path, config_path=Path(f"{model_path}.json"))
            return self._voices[name]


models = ModelHolder()
app = FastAPI(title="English Teacher Local - Speech", version="0.1.0")


def _voice_path(name: str) -> Path:
    if not name or any(sep in name for sep in ("/", "\\", "..")):
        raise HTTPException(status_code=400, detail="Nome de voz inválido.")
    path = VOICES_DIR / f"{name}.onnx"
    if not path.is_file() or not Path(f"{path}.json").is_file():
        raise HTTPException(
            status_code=503,
            detail=f"Voz '{name}' não encontrada em {VOICES_DIR}. Execute scripts/setup_models.ps1.",
        )
    return path


@lru_cache(maxsize=1)
def _stt_package_available() -> bool:
    return importlib.util.find_spec("faster_whisper") is not None


@lru_cache(maxsize=1)
def _tts_package_available() -> bool:
    return importlib.util.find_spec("piper") is not None


@app.get("/health")
def health() -> dict[str, Any]:
    default_voice_ready = (VOICES_DIR / f"{DEFAULT_VOICE}.onnx").is_file()
    whisper_cached = any(Path(STT_DOWNLOAD_ROOT).glob("models--*")) if Path(STT_DOWNLOAD_ROOT).exists() else False
    return {
        "status": "ok",
        "stt_model": STT_MODEL,
        "stt_ready": _stt_package_available() and whisper_cached,
        "tts_voice": DEFAULT_VOICE,
        "tts_ready": _tts_package_available() and default_voice_ready,
        "voices_dir": str(VOICES_DIR),
    }


SUPPORTED_STT_LANGUAGES = {"en", "fr"}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = Form("en")) -> dict[str, Any]:
    if language not in SUPPORTED_STT_LANGUAGES:
        raise HTTPException(status_code=400, detail=f"Idioma de reconhecimento não suportado: {language}.")
    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Áudio grande demais.")
    if not data:
        raise HTTPException(status_code=400, detail="Áudio vazio.")

    try:
        model = models.stt()
    except Exception as exc:  # modelo ausente ou falha de carga
        log.exception("Falha ao carregar Whisper")
        raise HTTPException(
            status_code=503,
            detail=f"Modelo de voz '{STT_MODEL}' indisponível. Execute scripts/setup_models.ps1. ({type(exc).__name__})",
        ) from exc

    try:
        segments, info = model.transcribe(
            io.BytesIO(data),
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        kept = [s.text.strip() for s in segments if s.no_speech_prob < NO_SPEECH_THRESHOLD and s.text.strip()]
    except Exception as exc:  # áudio inválido ou corrompido
        log.exception("Falha ao decodificar áudio")
        raise HTTPException(status_code=422, detail="Não consegui entender este áudio. Grave de novo.") from exc

    text = " ".join(kept).strip()
    return {
        "text": text,
        "language": info.language,
        "duration_s": round(float(info.duration), 2),
        "empty": text == "",
    }


@app.post("/synthesize")
def synthesize(body: SynthesizeIn) -> Response:
    voice_name = body.voice or DEFAULT_VOICE
    try:
        voice = models.voice(voice_name)
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("Falha ao carregar voz")
        raise HTTPException(status_code=503, detail=f"Voz '{voice_name}' indisponível. ({type(exc).__name__})") from exc

    from piper.config import SynthesisConfig

    # length_scale > 1 deixa a fala mais lenta; por isso o inverso da taxa.
    syn = SynthesisConfig(length_scale=1.0 / body.rate, volume=body.volume)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        voice.synthesize_wav(body.text, wav_file, syn_config=syn)
    return Response(content=buffer.getvalue(), media_type="audio/wav")
