import json
from collections.abc import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.container import build_container
from app.main import create_app
from app.services.llm_service import OllamaClient
from app.services.speech_client import SpeechClient


@pytest.fixture
def config(tmp_path) -> Settings:
    return Settings(data_dir=tmp_path / "data", _env_file=None)


class FakeOllama:
    """Simula o Ollama. ``replies`` é uma fila de conteúdos devolvidos em /api/chat."""

    def __init__(self, models=("qwen3:8b",)) -> None:
        self.models = list(models)
        self.replies: list[str] = []
        self.requests: list[dict] = []
        self.offline = False

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.offline:
            raise httpx.ConnectError("refused", request=request)
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": m} for m in self.models]})
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            self.requests.append(body)
            if body["model"] not in self.models:
                return httpx.Response(404, json={"error": "model not found"})
            content = self.replies.pop(0) if self.replies else '{"reply": "Sure!", "correction": null, "new_vocabulary": []}'
            return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})
        return httpx.Response(404)


class FakeSpeech:
    def __init__(self) -> None:
        self.transcript = "hello there"

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"stt_ready": True, "tts_ready": True})
        if request.url.path == "/transcribe":
            return httpx.Response(200, json={"text": self.transcript, "language": "en"})
        if request.url.path == "/synthesize":
            return httpx.Response(200, content=b"RIFFfake", headers={"content-type": "audio/wav"})
        return httpx.Response(404)


@pytest.fixture
def fake_ollama() -> FakeOllama:
    return FakeOllama()


@pytest.fixture
def fake_speech() -> FakeSpeech:
    return FakeSpeech()


@pytest.fixture
def client_factory(config, fake_ollama, fake_speech) -> Callable[..., TestClient]:
    def make(**overrides) -> TestClient:
        cfg = config.model_copy(update=overrides)
        llm = OllamaClient(cfg.ollama_url, cfg.llm_timeout_s, transport=httpx.MockTransport(fake_ollama.handler))
        speech = SpeechClient(cfg.speech_url, cfg.speech_timeout_s, transport=httpx.MockTransport(fake_speech.handler))
        container = build_container(cfg, llm=llm, speech=speech)
        return TestClient(create_app(cfg, container=container))

    return make


@pytest.fixture
def client(client_factory) -> TestClient:
    with client_factory() as c:
        yield c
