"""Limite de tokens por chamada ao Ollama: sem ele, uma resposta pode seguir até o timeout."""

import json

import httpx

from app.services.llm_service import MAX_TOKENS_LONG, MAX_TOKENS_SHORT, OllamaClient


def _client_capturing(payloads: list[dict]) -> OllamaClient:
    def handler(request: httpx.Request) -> httpx.Response:
        payloads.append(json.loads(request.content))
        return httpx.Response(200, json={"message": {"content": "{}"}})

    return OllamaClient("http://ollama.test", timeout_s=5, transport=httpx.MockTransport(handler))


def _call(client: OllamaClient, **extra) -> None:
    client.chat(
        model="qwen3:8b",
        messages=[{"role": "user", "content": "oi"}],
        format_schema=None,
        temperature=0.5,
        num_ctx=4096,
        **extra,
    )


def test_default_limit_is_the_short_one():
    payloads: list[dict] = []
    _call(_client_capturing(payloads))
    assert payloads[0]["options"]["num_predict"] == MAX_TOKENS_SHORT


def test_long_outputs_can_ask_for_more_tokens():
    payloads: list[dict] = []
    _call(_client_capturing(payloads), max_tokens=MAX_TOKENS_LONG)
    assert payloads[0]["options"]["num_predict"] == MAX_TOKENS_LONG


def test_limits_fit_inside_the_generation_timeout():
    # ~33 tokens/s medidos no teste; o pior caso precisa caber no timeout de 120 s.
    assert MAX_TOKENS_LONG / 33 < 120
    assert MAX_TOKENS_SHORT < MAX_TOKENS_LONG
