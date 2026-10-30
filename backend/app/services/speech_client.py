"""Cliente do servidor de voz (componente ai-model: faster-whisper + Piper)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx


class SpeechUnavailable(Exception):
    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code  # "speech_offline" | "speech_error" | "timeout"


@dataclass(frozen=True)
class SpeechStatus:
    reachable: bool
    stt_ready: bool
    tts_ready: bool
    message: str


class SpeechClient:
    def __init__(self, base_url: str, timeout_s: float, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_s
        self._transport = transport

    def _client(self, timeout: float | None = None) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            timeout=timeout or self._timeout,
            transport=self._transport,
        )

    def status(self) -> SpeechStatus:
        try:
            with self._client(timeout=3.0) as client:
                data = client.get("/health").json()
        except (httpx.HTTPError, ValueError) as exc:
            return SpeechStatus(False, False, False, f"Servidor de voz indisponível ({type(exc).__name__}).")
        stt = bool(data.get("stt_ready"))
        tts = bool(data.get("tts_ready"))
        message = "Pronto." if stt and tts else "Voz parcialmente disponível. Verifique os modelos em ai-model/."
        return SpeechStatus(True, stt, tts, message)

    def transcribe(self, audio: bytes, filename: str, content_type: str, language: str = "en") -> dict:
        try:
            with self._client() as client:
                response = client.post(
                    "/transcribe",
                    files={"audio": (filename, audio, content_type or "application/octet-stream")},
                    data={"language": language},
                )
        except httpx.TimeoutException as exc:
            raise SpeechUnavailable("A transcrição demorou demais.", code="timeout") from exc
        except httpx.HTTPError as exc:
            raise SpeechUnavailable(
                "O servidor de voz não está disponível. Inicie o ai-model antes de usar o microfone.",
                code="speech_offline",
            ) from exc
        if response.status_code >= 400:
            raise SpeechUnavailable(_detail(response, "Falha ao transcrever o áudio."), code="speech_error")
        return response.json()

    def synthesize(self, text: str, voice: str | None, rate: float, volume: float) -> bytes:
        payload = {"text": text, "voice": voice, "rate": rate, "volume": volume}
        try:
            with self._client() as client:
                response = client.post("/synthesize", json=payload)
        except httpx.TimeoutException as exc:
            raise SpeechUnavailable("A geração de voz demorou demais.", code="timeout") from exc
        except httpx.HTTPError as exc:
            raise SpeechUnavailable("O servidor de voz não está disponível.", code="speech_offline") from exc
        if response.status_code >= 400:
            raise SpeechUnavailable(_detail(response, "Falha ao gerar a voz."), code="speech_error")
        return response.content


def _detail(response: httpx.Response, fallback: str) -> str:
    try:
        return str(response.json().get("detail") or fallback)
    except ValueError:
        return fallback
