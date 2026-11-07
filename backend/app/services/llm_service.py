"""Ponto único de contato com o modelo de linguagem.

Padrão: Ollama (local). Opcionalmente, provedores na nuvem (Claude, Groq, GPT).
O provedor é escolhido pelo prefixo do nome do modelo:
  - "groq/openai/gpt-oss-20b"   -> Groq
  - "anthropic/claude-haiku-5-5" -> Anthropic
  - "openai/gpt-4.1-nano"        -> OpenAI
  - "qwen3:8b" (sem prefixo)     -> Ollama
Os serviços chamam apenas ``chat`` e ``status`` do ``LLMRouter``; não sabem qual provedor está por trás.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from app.services.model_store import key_hint

log = logging.getLogger(__name__)


class LLMUnavailable(Exception):
    """Modelo indisponível, ausente, sem chave ou com falha de comunicação."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        # "ollama_offline" | "model_missing" | "timeout" | "llm_error" |
        # "not_configured" | "provider_offline" | "auth" | "rate_limit"
        self.code = code


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
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            # Qwen3 tem modo de raciocínio; desligado para respostas rápidas e JSON limpo.
            "think": False,
            "options": {"temperature": temperature, "num_ctx": num_ctx},
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


# ---------------------------------------------------------------------------
# Provedores na nuvem
# ---------------------------------------------------------------------------


class ChatLLM(Protocol):
    def status(self, selected_model: str) -> LLMStatus: ...

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        format_schema: dict[str, Any] | None,
        temperature: float,
        num_ctx: int,
    ) -> str: ...


def _schema_instruction(format_schema: dict[str, Any]) -> str:
    # Provedores na nuvem não recebem o schema como o Ollama: ele vai como instrução.
    return (
        "Responda somente com um objeto JSON válido, sem texto antes ou depois, "
        "que siga exatamente este JSON Schema:\n" + json.dumps(format_schema, ensure_ascii=False)
    )


def _log_usage(provider: str, model: str, tokens_in: int | None, tokens_out: int | None) -> None:
    # Só contagens de tokens, nunca conteúdo: serve para acompanhar o gasto.
    log.info("llm uso provider=%s model=%s tokens_in=%s tokens_out=%s", provider, model, tokens_in, tokens_out)


class CloudClient:
    """Base dos provedores pagos. Subclasses dizem como montar o pedido e ler a resposta."""

    provider: str = ""  # prefixo do modelo, ex.: "groq"
    label: str = ""  # nome exibido ao aluno
    key_env: str = ""  # variável de ambiente da chave
    base_url: str = ""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_s: float,
        max_output_tokens: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key.strip()
        self.model = model
        self._timeout = timeout_s
        self._max_tokens = max_output_tokens
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._api_key)

    def status(self, selected_model: str) -> LLMStatus:
        # Não faz chamada de rede: a diagnose roda a cada 15 s e cada chamada custaria tempo (e às vezes dinheiro).
        if not self.configured:
            return LLMStatus(
                reachable=False,
                installed_models=[],
                selected_model=selected_model,
                model_installed=False,
                message=f"{self.label}: chave não configurada. Defina {self.key_env} em backend/.env.",
            )
        return LLMStatus(
            reachable=True,
            installed_models=[selected_model],
            selected_model=selected_model,
            model_installed=True,
            message=f"Pronto. {self.label} usa a internet e cobra por token.",
        )

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        format_schema: dict[str, Any] | None,
        temperature: float,
        num_ctx: int,  # não se aplica à nuvem; mantido pela mesma assinatura do Ollama
    ) -> str:
        if not self.configured:
            raise LLMUnavailable(
                f"{self.label} não está configurado. Defina {self.key_env} em backend/.env.", code="not_configured"
            )
        url, headers, payload = self._build(model, messages, format_schema, temperature)
        data = self._post(url, headers, payload, model)
        text, tokens_in, tokens_out = self._read(data)
        _log_usage(self.provider, model, tokens_in, tokens_out)
        return text

    def _post(self, url: str, headers: dict[str, str], payload: dict[str, Any], model: str) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=self._timeout, transport=self._transport) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMUnavailable(f"{self.label} demorou demais para responder.", code="timeout") from exc
        except httpx.HTTPError as exc:
            raise LLMUnavailable(
                f"Não consegui falar com {self.label}. Verifique a conexão com a internet.", code="provider_offline"
            ) from exc

        status = response.status_code
        if status in (401, 403):
            raise LLMUnavailable(
                f"A chave de {self.label} foi recusada. Confira {self.key_env} em backend/.env.", code="auth"
            )
        if status == 404:
            raise LLMUnavailable(
                f"O modelo '{model}' não existe em {self.label}. Confira o nome em backend/.env.", code="model_missing"
            )
        if status == 429:
            raise LLMUnavailable(
                f"Limite de uso de {self.label} atingido. Aguarde um pouco ou troque de modelo.", code="rate_limit"
            )
        if status >= 400:
            # Sem o corpo da resposta no log: pode ecoar partes do pedido.
            log.error("%s retornou HTTP %s", self.label, status)
            raise LLMUnavailable(f"{self.label} devolveu um erro ao processar a mensagem.", code="llm_error")
        try:
            return response.json()
        except ValueError as exc:
            raise LLMUnavailable(f"Resposta inesperada de {self.label}.", code="llm_error") from exc

    def _build(
        self, model: str, messages: list[dict[str, str]], format_schema: dict[str, Any] | None, temperature: float
    ) -> tuple[str, dict[str, str], dict[str, Any]]:
        raise NotImplementedError

    def _read(self, data: dict[str, Any]) -> tuple[str, int | None, int | None]:
        raise NotImplementedError


class AnthropicClient(CloudClient):
    provider = "anthropic"
    label = "Claude (Anthropic)"
    key_env = "ETL_ANTHROPIC_API_KEY"
    base_url = "https://api.anthropic.com/v1"

    def _build(self, model, messages, format_schema, temperature):
        # A API da Anthropic recebe o system à parte e exige turnos alternados user/assistant.
        system: list[str] = []
        turns: list[dict[str, str]] = []
        for m in messages:
            if m["role"] == "system":
                system.append(m["content"])
                continue
            role = "assistant" if m["role"] == "assistant" else "user"
            if turns and turns[-1]["role"] == role:
                turns[-1]["content"] += "\n\n" + m["content"]
            else:
                turns.append({"role": role, "content": m["content"]})
        if not turns or turns[0]["role"] == "assistant":
            turns.insert(0, {"role": "user", "content": "Vamos começar."})
        if format_schema is not None:
            system.append(_schema_instruction(format_schema))

        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": self._max_tokens,
            "temperature": min(temperature, 1.0),  # Anthropic aceita 0 a 1
            "messages": turns,
        }
        if system:
            payload["system"] = "\n\n".join(system)
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        return f"{self.base_url}/messages", headers, payload

    def _read(self, data):
        try:
            text = "".join(b["text"] for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError) as exc:
            raise LLMUnavailable("Resposta inesperada de Claude.", code="llm_error") from exc
        usage = data.get("usage") or {}
        return text, usage.get("input_tokens"), usage.get("output_tokens")


class OpenAICompatibleClient(CloudClient):
    """Protocolo de chat/completions da OpenAI, também usado pelo Groq."""

    _max_tokens_key = "max_completion_tokens"

    def _build(self, model, messages, format_schema, temperature):
        msgs: list[dict[str, str]] = [dict(m) for m in messages]
        payload: dict[str, Any] = {
            "model": model,
            "messages": msgs,
            "temperature": temperature,
            self._max_tokens_key: self._max_tokens,
        }
        if format_schema is not None:
            msgs.insert(0, {"role": "system", "content": _schema_instruction(format_schema)})
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}
        return f"{self.base_url}/chat/completions", headers, payload

    def _read(self, data):
        try:
            text = data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailable(f"Resposta inesperada de {self.label}.", code="llm_error") from exc
        usage = data.get("usage") or {}
        return text, usage.get("prompt_tokens"), usage.get("completion_tokens")


class GroqClient(OpenAICompatibleClient):
    provider = "groq"
    label = "Groq"
    key_env = "ETL_GROQ_API_KEY"
    base_url = "https://api.groq.com/openai/v1"
    _max_tokens_key = "max_tokens"


class OpenAIClient(OpenAICompatibleClient):
    provider = "openai"
    label = "OpenAI (GPT)"
    key_env = "ETL_OPENAI_API_KEY"
    base_url = "https://api.openai.com/v1"


class LLMRouter:
    """Escolhe o cliente pelo prefixo do modelo. Sem prefixo de provedor, usa o Ollama."""

    def __init__(self, ollama: OllamaClient, clouds: list[CloudClient] | None = None) -> None:
        self._ollama = ollama
        self._clouds = {c.provider: c for c in clouds or []}

    def _route(self, model: str) -> tuple[ChatLLM, str, str]:
        for name, client in self._clouds.items():
            prefix = f"{name}/"
            if model.startswith(prefix):
                return client, model[len(prefix):], name
        return self._ollama, model, "ollama"

    def provider_of(self, model: str) -> str:
        return self._route(model)[2]

    def status(self, selected_model: str) -> LLMStatus:
        client, _, _ = self._route(selected_model)
        return client.status(selected_model)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        format_schema: dict[str, Any] | None,
        temperature: float,
        num_ctx: int,
    ) -> str:
        client, bare, _ = self._route(model)
        return client.chat(
            model=bare, messages=messages, format_schema=format_schema, temperature=temperature, num_ctx=num_ctx
        )

    def cloud_options(self) -> list[tuple[str, str]]:
        """(nome do modelo com prefixo, rótulo) dos provedores com chave configurada."""
        return [(f"{c.provider}/{c.model}", c.label) for c in self._clouds.values() if c.configured]

    def list_local_models(self) -> list[str]:
        return self._ollama.list_models()

    def cloud_providers(self) -> list[dict[str, Any]]:
        """Estado dos provedores para a tela de Ajustes. Nunca devolve a chave, só um trecho dela."""
        return [
            {
                "provider": c.provider,
                "label": c.label,
                "key_env": c.key_env,
                "configured": c.configured,
                "key_hint": key_hint(c._api_key),
                "model": c.model,
            }
            for c in self._clouds.values()
        ]

    def configure_provider(self, provider: str, *, api_key: str | None, model: str | None) -> None:
        """Troca chave e modelo de um provedor em execução (o arquivo .env é gravado pelo chamador)."""
        client = self._clouds.get(provider)
        if client is None:
            raise KeyError(provider)
        if api_key is not None:
            client._api_key = api_key.strip()
        if model:
            client.model = model


def build_llm(config: Any) -> LLMRouter:
    """Monta o roteador a partir da configuração (``app.config.Settings``)."""
    common = {"timeout_s": config.llm_timeout_s, "max_output_tokens": config.cloud_max_output_tokens}
    clouds: list[CloudClient] = [
        AnthropicClient(api_key=config.anthropic_api_key, model=config.anthropic_model, **common),
        GroqClient(api_key=config.groq_api_key, model=config.groq_model, **common),
        OpenAIClient(api_key=config.openai_api_key, model=config.openai_model, **common),
    ]
    return LLMRouter(OllamaClient(config.ollama_url, config.llm_timeout_s), clouds)
