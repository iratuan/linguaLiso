"""Cliente do Ollama (LLM local). Único ponto de contato com o modelo de linguagem."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Limite de tokens gerados por chamada. Sem ele, o modelo pode continuar gerando até o timeout
# (visto em teste: quase 14 mil tokens numa única resposta, com 503 no fim).
# Ao gerar ~33 tokens/s, 1024 tokens levam ~30 s e 3072 levam ~90 s, dentro do timeout de 120 s.
MAX_TOKENS_SHORT = 1024  # respostas da conversa, correções e análises
MAX_TOKENS_LONG = 3072  # lições, material de apoio e trilha, que geram JSON maior


class LLMUnavailable(Exception):
    """Ollama fora do ar, modelo ausente ou falha de comunicação."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code  # "ollama_offline" | "model_missing" | "timeout" | "llm_error"


@dataclass(frozen=True)
class LLMStatus:
    reachable: bool
    installed_models: list[str]
    selected_model: str
    model_installed: bool
    message: str


class OllamaClient:
    def __init__(self, base_url: str, timeout_s: float, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_s
        self._transport = transport

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self._base_url, timeout=self._timeout, transport=self._transport)

    def list_models(self) -> list[str]:
        with self._client() as client:
            response = client.get("/api/tags", timeout=5.0)
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]

    def status(self, selected_model: str) -> LLMStatus:
        try:
            installed = self.list_models()
        except (httpx.HTTPError, ValueError) as exc:
            return LLMStatus(
                reachable=False,
                installed_models=[],
                selected_model=selected_model,
                model_installed=False,
                message=f"Ollama não está respondendo em {self._base_url}. Inicie o Ollama e tente de novo. ({type(exc).__name__})",
            )
        available = selected_model in installed or f"{selected_model}:latest" in installed
        message = "Pronto." if available else (
            f"O modelo '{selected_model}' não está instalado. Execute: ollama pull {selected_model}"
        )
        return LLMStatus(True, installed, selected_model, available, message)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        format_schema: dict[str, Any] | None,
        temperature: float,
        num_ctx: int,
        max_tokens: int = MAX_TOKENS_SHORT,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            # Qwen3 tem modo de raciocínio; desligado para respostas rápidas e JSON limpo.
            "think": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx, "num_predict": max_tokens},
        }
        if format_schema is not None:
            payload["format"] = format_schema

        try:
            with self._client() as client:
                response = client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise LLMUnavailable("O modelo demorou demais para responder.", code="timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable(
                "Não consegui falar com o Ollama. Verifique se ele está em execução.", code="ollama_offline"
            ) from exc

        if response.status_code == 404:
            raise LLMUnavailable(
                f"O modelo '{model}' não está instalado. Execute: ollama pull {model}", code="model_missing"
            )
        if response.status_code >= 400:
            log.error("Ollama retornou HTTP %s", response.status_code)
            raise LLMUnavailable("O Ollama devolveu um erro ao processar a mensagem.", code="llm_error")

        try:
            return response.json()["message"]["content"]
        except (ValueError, KeyError) as exc:
            raise LLMUnavailable("Resposta inesperada do Ollama.", code="llm_error") from exc
