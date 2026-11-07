"""Tela de Ajustes: espaço em disco, download de modelos do Ollama e chaves dos provedores.

Nada aqui fala com a internet nem grava fora de pytest's tmp_path.
"""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.container import build_container
from app.main import create_app
from app.services.llm_service import AnthropicClient, GroqClient, LLMRouter, OllamaClient
from app.services.model_store import ModelPuller, measure, write_env_values
from app.services.speech_client import SpeechClient


@pytest.fixture
def router_client(config, fake_ollama, fake_speech, tmp_path, monkeypatch):
    """App com o roteador de IA real (e chaves de teste), gravando o .env dentro do tmp_path."""
    env_file = tmp_path / "provedores.env"
    monkeypatch.setenv("ETL_ENV_FILE", str(env_file))
    llm = LLMRouter(
        OllamaClient(config.ollama_url, 5, transport=httpx.MockTransport(fake_ollama.handler)),
        [
            AnthropicClient(api_key="", model="claude-haiku-5-5", timeout_s=5, max_output_tokens=100),
            GroqClient(api_key="gsk_abcdefghijklmnop", model="openai/gpt-oss-20b", timeout_s=5, max_output_tokens=100),
        ],
    )
    speech = SpeechClient(config.speech_url, 5, transport=httpx.MockTransport(fake_speech.handler))
    container = build_container(config, llm=llm, speech=speech)
    with TestClient(create_app(config, container=container)) as c:
        c.env_file = env_file  # type: ignore[attr-defined]
        yield c


def test_providers_list_never_returns_the_key(router_client):
    body = router_client.get("/api/llm/providers").json()

    by_name = {p["provider"]: p for p in body}
    assert by_name["groq"]["configured"] is True
    assert by_name["groq"]["key_hint"] == "…mnop"
    assert "gsk_abcdefghijklmnop" not in json.dumps(body)
    assert by_name["anthropic"]["configured"] is False


def test_saving_a_key_updates_the_running_client_and_the_env_file(router_client):
    r = router_client.put("/api/llm/providers/anthropic", json={"api_key": "sk-ant-XYZW1234", "model": "claude-haiku-5-5"})

    assert r.status_code == 200
    anthropic = next(p for p in r.json() if p["provider"] == "anthropic")
    assert anthropic["configured"] is True
    text = router_client.app.state.container.llm.cloud_options()
    assert ("anthropic/claude-haiku-5-5", "Claude (Anthropic)") in text
    saved = router_client.env_file.read_text(encoding="utf-8")
    assert "ETL_ANTHROPIC_API_KEY=sk-ant-XYZW1234" in saved
    assert "ETL_ANTHROPIC_MODEL=claude-haiku-5-5" in saved


def test_empty_key_removes_the_saved_key(router_client):
    router_client.put("/api/llm/providers/groq", json={"api_key": ""})

    assert "ETL_GROQ_API_KEY" not in router_client.env_file.read_text(encoding="utf-8")
    groq = next(p for p in router_client.get("/api/llm/providers").json() if p["provider"] == "groq")
    assert groq["configured"] is False


def test_unknown_provider_is_refused(router_client):
    r = router_client.put("/api/llm/providers/inventado", json={"api_key": "x"})
    assert r.status_code == 400


def test_ollama_status_reports_suggested_models_and_install_state(client):
    body = client.get("/api/llm/ollama").json()

    roles = {s["role"]: s for s in body["suggested"]}
    assert set(roles) == {"principal", "leve"}
    assert roles["principal"]["installed"] is True  # o FakeOllama declara qwen3:8b
    assert roles["leve"]["installed"] is False
    assert body["reachable"] is True
    assert body["download"]["status"] == "idle"


def test_pull_rejects_names_that_are_not_ollama_models(client):
    r = client.post("/api/llm/ollama/pull", json={"model": "groq/../../etc"})
    assert r.status_code == 400


def test_puller_reports_progress_and_finishes():
    lines = [
        {"status": "pulling", "total": 100, "completed": 25},
        {"status": "pulling", "total": 100, "completed": 100},
        {"status": "success"},
    ]
    body = "\n".join(json.dumps(x) for x in lines).encode()

    def handler(request):
        assert json.loads(request.content) == {"model": "qwen3:4b", "stream": True}
        return httpx.Response(200, content=body)

    puller = ModelPuller("http://ollama.test", transport=httpx.MockTransport(handler))
    puller.start("qwen3:4b")
    for _ in range(100):
        state = puller.state()
        if state["status"] != "downloading":
            break
        import time
        time.sleep(0.01)
    assert state["status"] == "done"
    assert state["percent"] == 100.0


def test_puller_hides_technical_errors_from_the_student():
    def handler(request):
        return httpx.Response(500, text="stack trace interno")

    puller = ModelPuller("http://ollama.test", transport=httpx.MockTransport(handler))
    puller.start("qwen3:4b")
    import time
    for _ in range(100):
        state = puller.state()
        if state["status"] != "downloading":
            break
        time.sleep(0.01)
    assert state["status"] == "error"
    assert "stack trace" not in state["error"]


def test_storage_endpoint_lists_groups_and_measures_files(client):
    body = client.get("/api/storage").json()

    ids = [g["id"] for g in body["groups"]]
    assert ids == ["dependencias", "voz", "interface", "dados", "ollama"]
    assert body["total_bytes"] >= 0


def test_measure_sums_nested_files(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "x.bin").write_bytes(b"x" * 1000)
    (tmp_path / "y.bin").write_bytes(b"y" * 24)

    assert measure(tmp_path) == 1024
    assert measure(tmp_path / "nao-existe") == 0


def test_write_env_values_replaces_removes_and_keeps_other_lines(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# comentário\nETL_GROQ_API_KEY=antiga\nETL_DEFAULT_LLM_MODEL=qwen3:8b\n", encoding="utf-8")

    write_env_values(env, {"ETL_GROQ_API_KEY": "nova", "ETL_OPENAI_API_KEY": "sk", "ETL_DEFAULT_LLM_MODEL": None})

    text = env.read_text(encoding="utf-8")
    assert "# comentário" in text
    assert "ETL_GROQ_API_KEY=nova" in text
    assert "ETL_OPENAI_API_KEY=sk" in text
    assert "ETL_DEFAULT_LLM_MODEL" not in text
