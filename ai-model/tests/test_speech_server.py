"""Testes do servidor de voz que não exigem os modelos baixados.

Os caminhos de sucesso (transcrição e síntese reais) são verificados pelo script
scripts/smoke_test.ps1 quando os modelos estão instalados.
"""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("ETL_VOICES_DIR", str(tmp_path / "voices"))
    monkeypatch.setenv("ETL_MODELS_DIR", str(tmp_path / "whisper"))
    import speech_server

    speech_server = importlib.reload(speech_server)
    return speech_server


def test_health_reports_not_ready_without_models(server):
    with TestClient(server.app) as client:
        body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["tts_ready"] is False
    assert body["stt_ready"] is False


def test_synthesize_without_voice_file_is_503_with_instructions(server):
    with TestClient(server.app) as client:
        response = client.post("/synthesize", json={"text": "Hello"})
    assert response.status_code == 503
    assert "setup_models.ps1" in response.json()["detail"]


@pytest.mark.parametrize("name", ["../etc/passwd", "a\\b"])
def test_voice_name_is_validated(server, name):
    with TestClient(server.app) as client:
        response = client.post("/synthesize", json={"text": "Hello", "voice": name})
    assert response.status_code in (400, 422)


def test_synthesize_rejects_text_too_long(server):
    with TestClient(server.app) as client:
        response = client.post("/synthesize", json={"text": "a" * (server.MAX_TTS_CHARS + 1)})
    assert response.status_code == 422


def test_transcribe_rejects_empty_upload(server):
    with TestClient(server.app) as client:
        response = client.post("/transcribe", files={"audio": ("a.webm", b"", "audio/webm")})
    assert response.status_code == 400


def test_transcribe_reports_missing_whisper_model(server, monkeypatch):
    def broken():
        raise OSError("model not cached")

    monkeypatch.setattr(server.models, "stt", broken)
    with TestClient(server.app) as client:
        response = client.post("/transcribe", files={"audio": ("a.webm", b"abc", "audio/webm")})
    assert response.status_code == 503
    assert "setup_models.ps1" in response.json()["detail"]


def test_transcribe_rejects_undecodable_audio(server, monkeypatch):
    class Boom:
        def transcribe(self, *args, **kwargs):
            raise ValueError("invalid data")

    monkeypatch.setattr(server.models, "stt", lambda: Boom())
    with TestClient(server.app) as client:
        response = client.post("/transcribe", files={"audio": ("a.webm", b"abc", "audio/webm")})
    assert response.status_code == 422
