"""Ajustes de IA: estado do Ollama, download de modelos e chaves dos provedores na nuvem."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import get_container
from app.config import env_file_path
from app.container import Container
from app.services.conversation_service import BadRequest
from app.services.llm_service import LLMRouter
from app.services.model_store import (
    ModelPuller,
    find_ollama_binary,
    write_env_values,
)

router = APIRouter(prefix="/llm", tags=["ia"])

_pullers: dict[str, ModelPuller] = {}


def _puller(c: Container) -> ModelPuller:
    base = c.config.ollama_url
    if base not in _pullers:
        _pullers[base] = ModelPuller(base)
    return _pullers[base]


class PullIn(BaseModel):
    model: str = Field(min_length=1, max_length=120)


class ProviderIn(BaseModel):
    # None = não mexe na chave; string vazia = apaga a chave salva.
    api_key: str | None = Field(default=None, max_length=300)
    model: str | None = Field(default=None, max_length=120)


@router.get("/ollama")
def ollama_status(c: Container = Depends(get_container)) -> dict[str, Any]:
    installed: list[str] = []
    reachable = False
    try:
        listar = c.llm.list_local_models if hasattr(c.llm, "list_local_models") else c.llm.list_models
        installed = listar()
        reachable = True
    except Exception:  # noqa: BLE001 - qualquer falha aqui é só "não está respondendo"
        reachable = False
    suggested = []
    for role, model in (("principal", c.config.default_llm_model), ("leve", c.config.fallback_llm_model)):
        ok = model in installed or f"{model}:latest" in installed
        suggested.append({"role": role, "model": model, "installed": ok})
    return {
        "binary_found": find_ollama_binary() is not None,
        "reachable": reachable,
        "suggested": suggested,
        "installed_models": installed,
        "download": _puller(c).state(),
    }


@router.post("/ollama/pull")
def ollama_pull(body: PullIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    try:
        return _puller(c).start(body.model)
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc
    except RuntimeError as exc:
        raise BadRequest(str(exc)) from exc


@router.get("/ollama/pull")
def ollama_pull_state(c: Container = Depends(get_container)) -> dict[str, Any]:
    return _puller(c).state()


@router.get("/providers")
def providers(c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    if not isinstance(c.llm, LLMRouter):
        return []
    return c.llm.cloud_providers()


@router.put("/providers/{provider}")
def save_provider(provider: str, body: ProviderIn, c: Container = Depends(get_container)) -> list[dict[str, Any]]:
    if not isinstance(c.llm, LLMRouter):
        return []
    known = {p["provider"]: p for p in c.llm.cloud_providers()}
    if provider not in known:
        raise BadRequest("Provedor desconhecido.")
    env_key = known[provider]["key_env"]
    env_model = env_key.replace("_API_KEY", "_MODEL")

    changes: dict[str, str | None] = {}
    if body.api_key is not None:
        key = body.api_key.strip()
        changes[env_key] = key or None
        c.llm.configure_provider(provider, api_key=key, model=None)
    if body.model is not None:
        model = body.model.strip()
        if model:
            changes[env_model] = model
            c.llm.configure_provider(provider, api_key=None, model=model)
    if changes:
        write_env_values(env_file_path(), changes)
    return c.llm.cloud_providers()
