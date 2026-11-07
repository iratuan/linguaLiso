"""Provedores na nuvem (Claude, Groq, GPT) e roteamento pelo prefixo do modelo.

Nenhum teste fala com a internet: o httpx usa MockTransport.
"""

import json

import httpx
import pytest

from app.services.llm_service import (
    AnthropicClient,
    GroqClient,
    LLMRouter,
    LLMUnavailable,
    OllamaClient,
    OpenAIClient,
)

SCHEMA = {"type": "object", "properties": {"reply": {"type": "string"}}, "required": ["reply"]}
MESSAGES = [
    {"role": "system", "content": "Você é um professor."},
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
    {"role": "user", "content": "How are you?"},
]


class Recorder:
    """Transporte falso que guarda os pedidos e responde com o que for configurado."""

    def __init__(self, status: int = 200, body: dict | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.status = status
        self.body = body if body is not None else {}

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body)

    @property
    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def anthropic_body(text: str = '{"reply": "Fine!"}') -> dict:
    return {
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 120, "output_tokens": 15},
    }


def openai_body(text: str = '{"reply": "Fine!"}') -> dict:
    return {
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 120, "completion_tokens": 15},
    }


def sent(recorder: Recorder) -> dict:
    return json.loads(recorder.requests[-1].content)


# ----- Anthropic ------------------------------------------------------------


def test_anthropic_moves_system_out_and_asks_for_json():
    rec = Recorder(body=anthropic_body())
    client = AnthropicClient(api_key="sk-test", model="claude-haiku-5-5", timeout_s=5, max_output_tokens=900,
                             transport=rec.transport)

    text = client.chat(model="claude-haiku-5-5", messages=MESSAGES, format_schema=SCHEMA, temperature=1.5, num_ctx=4096)

    assert text == '{"reply": "Fine!"}'
    req = rec.requests[-1]
    assert req.url.path == "/v1/messages"
    assert req.headers["x-api-key"] == "sk-test"
    assert req.headers["anthropic-version"] == "2023-06-01"
    body = sent(rec)
    assert body["model"] == "claude-haiku-5-5"
    assert body["max_tokens"] == 900
    assert body["temperature"] == 1.0  # Anthropic aceita no máximo 1
    assert [m["role"] for m in body["messages"]] == ["user", "assistant", "user"]
    assert "Você é um professor." in body["system"]
    assert "JSON Schema" in body["system"]


def test_anthropic_merges_consecutive_turns_and_starts_with_user():
    rec = Recorder(body=anthropic_body())
    client = AnthropicClient(api_key="k", model="m", timeout_s=5, max_output_tokens=100, transport=rec.transport)

    client.chat(
        model="m",
        messages=[{"role": "assistant", "content": "a"}, {"role": "user", "content": "b"}, {"role": "user", "content": "c"}],
        format_schema=None,
        temperature=0.2,
        num_ctx=0,
    )

    msgs = sent(rec)["messages"]
    assert msgs[0]["role"] == "user"  # API exige começar com user
    assert msgs[-1] == {"role": "user", "content": "b\n\nc"}
    assert "system" not in sent(rec)


# ----- Groq e OpenAI (mesmo protocolo) -------------------------------------


def test_groq_sends_bearer_key_json_mode_and_token_cap():
    rec = Recorder(body=openai_body())
    client = GroqClient(api_key="gsk-test", model="openai/gpt-oss-20b", timeout_s=5, max_output_tokens=700,
                        transport=rec.transport)

    text = client.chat(model="openai/gpt-oss-20b", messages=MESSAGES, format_schema=SCHEMA, temperature=0.7, num_ctx=0)

    assert text == '{"reply": "Fine!"}'
    req = rec.requests[-1]
    assert req.url == "https://api.groq.com/openai/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer gsk-test"
    body = sent(rec)
    assert body["model"] == "openai/gpt-oss-20b"
    assert body["response_format"] == {"type": "json_object"}
    assert body["max_tokens"] == 700
    assert body["messages"][0]["role"] == "system"  # instrução do schema vem primeiro


def test_openai_uses_max_completion_tokens():
    rec = Recorder(body=openai_body())
    client = OpenAIClient(api_key="sk", model="gpt-4.1-nano", timeout_s=5, max_output_tokens=512, transport=rec.transport)

    client.chat(model="gpt-4.1-nano", messages=MESSAGES, format_schema=None, temperature=0.7, num_ctx=0)

    body = sent(rec)
    assert body["max_completion_tokens"] == 512
    assert "response_format" not in body  # sem schema, não força JSON


# ----- Erros e chave ausente ----------------------------------------------


@pytest.mark.parametrize(
    ("status", "code"),
    [(401, "auth"), (403, "auth"), (404, "model_missing"), (429, "rate_limit"), (500, "llm_error")],
)
def test_provider_errors_map_to_clear_codes(status, code):
    rec = Recorder(status=status, body={"error": "x"})
    client = GroqClient(api_key="k", model="m", timeout_s=5, max_output_tokens=100, transport=rec.transport)

    with pytest.raises(LLMUnavailable) as exc:
        client.chat(model="m", messages=MESSAGES, format_schema=None, temperature=0.7, num_ctx=0)
    assert exc.value.code == code


def test_timeout_and_network_failure_are_reported():
    def boom(request):
        raise httpx.ConnectError("sem rede", request=request)

    client = GroqClient(api_key="k", model="m", timeout_s=5, max_output_tokens=100,
                        transport=httpx.MockTransport(boom))
    with pytest.raises(LLMUnavailable) as exc:
        client.chat(model="m", messages=MESSAGES, format_schema=None, temperature=0.7, num_ctx=0)
    assert exc.value.code == "provider_offline"


def test_missing_key_never_touches_the_network():
    rec = Recorder()
    client = AnthropicClient(api_key="   ", model="m", timeout_s=5, max_output_tokens=100, transport=rec.transport)

    with pytest.raises(LLMUnavailable) as exc:
        client.chat(model="m", messages=MESSAGES, format_schema=None, temperature=0.7, num_ctx=0)

    assert exc.value.code == "not_configured"
    assert "ETL_ANTHROPIC_API_KEY" in str(exc.value)
    assert rec.requests == []


def test_status_without_key_is_down_and_offline():
    rec = Recorder()
    client = GroqClient(api_key="", model="m", timeout_s=5, max_output_tokens=100, transport=rec.transport)

    status = client.status("groq/m")

    assert status.reachable is False
    assert "ETL_GROQ_API_KEY" in status.message
    assert rec.requests == []  # diagnóstico não gasta chamada


# ----- Roteamento ----------------------------------------------------------


def test_router_sends_prefixed_models_to_the_provider_and_the_rest_to_ollama():
    cloud_rec = Recorder(body=openai_body())
    ollama_rec = Recorder(body={"message": {"content": "local"}})
    router = LLMRouter(
        OllamaClient("http://ollama.test", 5, transport=ollama_rec.transport),
        [GroqClient(api_key="k", model="openai/gpt-oss-20b", timeout_s=5, max_output_tokens=100,
                    transport=cloud_rec.transport)],
    )

    assert router.chat(model="groq/openai/gpt-oss-20b", messages=MESSAGES, format_schema=None,
                       temperature=0.7, num_ctx=4096) == '{"reply": "Fine!"}'
    assert sent(cloud_rec)["model"] == "openai/gpt-oss-20b"  # prefixo removido

    assert router.chat(model="qwen3:8b", messages=MESSAGES, format_schema=None,
                       temperature=0.7, num_ctx=4096) == "local"
    assert ollama_rec.requests[-1].url.path == "/api/chat"
    assert router.provider_of("qwen3:8b") == "ollama"
    assert router.provider_of("groq/x") == "groq"


def test_cloud_options_list_only_providers_with_a_key():
    router = LLMRouter(
        OllamaClient("http://ollama.test", 5),
        [
            AnthropicClient(api_key="", model="claude-haiku-5-5", timeout_s=5, max_output_tokens=100),
            OpenAIClient(api_key="sk", model="gpt-4.1-nano", timeout_s=5, max_output_tokens=100),
        ],
    )

    assert router.cloud_options() == [("openai/gpt-4.1-nano", "OpenAI (GPT)")]


def test_settings_endpoint_exposes_model_options(client):
    body = client.get("/api/settings").json()

    values = [o["value"] for o in body["llm_model_options"]]
    assert body["llm_model_default"] in values
    assert body["llm_model_fallback"] in values
