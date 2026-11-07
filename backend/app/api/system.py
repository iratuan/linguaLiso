"""Saúde do sistema, diagnóstico, preferências e perfil do aluno."""

import shutil
from typing import Any

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_container
from app.container import Container
from app.config import PROJECT_DIR
from app.domain import ProfileIn, SettingsIn
from app.services.model_store import measure, ollama_models_dir

router = APIRouter(tags=["sistema"])
_storage_cache: dict[str, tuple[float, int]] = {}


@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": __version__}


@router.get("/diagnostics")
def diagnostics(c: Container = Depends(get_container)) -> dict[str, Any]:
    settings = c.settings.get_all()
    selected = settings["llm_model"] or c.config.default_llm_model
    llm = c.llm.status(selected)
    speech = c.speech.status()
    usage = shutil.disk_usage(c.config.data_dir if c.config.data_dir.exists() else c.config.data_dir.parent)
    return {
        "backend": {"version": __version__, "schema_version": c.db.schema_version()},
        "database": {"path": str(c.config.db_path), "exists": c.config.db_path.exists()},
        "data_dir": str(c.config.data_dir),
        "disk_free_gb": round(usage.free / 1024**3, 2),
        "llm": {
            "provider": c.llm.provider_of(selected) if hasattr(c.llm, "provider_of") else "ollama",
            "url": c.config.ollama_url,
            "reachable": llm.reachable,
            "selected_model": llm.selected_model,
            "model_installed": llm.model_installed,
            "installed_models": llm.installed_models,
            "message": llm.message,
        },
        "speech": {
            "url": c.config.speech_url,
            "reachable": speech.reachable,
            "stt_ready": speech.stt_ready,
            "tts_ready": speech.tts_ready,
            "message": speech.message,
        },
    }


@router.get("/settings")
def get_settings(c: Container = Depends(get_container)) -> dict[str, Any]:
    values = c.settings.get_all()
    values["llm_model_default"] = c.config.default_llm_model
    values["llm_model_fallback"] = c.config.fallback_llm_model
    values["llm_model_options"] = _llm_options(c)
    return values


def _llm_options(c: Container) -> list[dict[str, str]]:
    """Modelos que o aluno pode escolher: os do Ollama e, se houver chave, os provedores na nuvem."""
    options = [
        {"value": c.config.default_llm_model, "label": f"{c.config.default_llm_model} (Ollama, padrão)"},
        {"value": c.config.fallback_llm_model, "label": f"{c.config.fallback_llm_model} (Ollama, leve)"},
    ]
    cloud = getattr(c.llm, "cloud_options", None)
    if cloud is not None:
        options += [{"value": value, "label": f"{label} · nuvem"} for value, label in cloud()]
    return options


@router.put("/settings")
def update_settings(body: SettingsIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    changes = body.model_dump(exclude_none=True)
    if not changes:
        return get_settings(c)
    c.settings.update(changes)
    return get_settings(c)


@router.get("/profile")
def get_profile(c: Container = Depends(get_container)) -> dict[str, Any] | None:
    return c.profiles.get()


@router.put("/profile")
def save_profile(body: ProfileIn, c: Container = Depends(get_container)) -> dict[str, Any]:
    return c.profiles.save(body)


@router.get("/storage")
def storage(c: Container = Depends(get_container)) -> dict[str, Any]:
    """Espaço ocupado pelo programa, em bytes, separado por tipo. Cada pasta é medida no máximo a cada 60 s."""
    ai = PROJECT_DIR / "ai-model"
    groups = [
        {"id": "dependencias", "label": "Dependências (Python e Node)", "items": [
            ("backend/.venv", PROJECT_DIR / "backend" / ".venv"),
            ("ai-model/.venv", ai / ".venv"),
            ("frontend/node_modules", PROJECT_DIR / "frontend" / "node_modules"),
        ]},
        {"id": "voz", "label": "Vozes e reconhecimento de fala", "items": [
            ("ai-model/voices", ai / "voices"),
            ("ai-model/models", ai / "models"),
        ]},
        {"id": "interface", "label": "Interface compilada", "items": [
            ("frontend/dist", PROJECT_DIR / "frontend" / "dist"),
        ]},
        {"id": "dados", "label": "Seus dados (conversas, progresso, backups)", "items": [
            ("data", c.config.data_dir),
        ]},
        {"id": "ollama", "label": "Modelos do Ollama (fora da pasta do projeto)", "items": [
            ("modelos do Ollama", ollama_models_dir()),
        ]},
    ]
    out = []
    total_projeto = 0
    for group in groups:
        rows = []
        size = 0
        for name, path in group["items"]:
            b = measure(path, _storage_cache, str(path))
            size += b
            rows.append({"name": name, "bytes": b})
        if group["id"] != "ollama":
            total_projeto += size
        out.append({"id": group["id"], "label": group["label"], "bytes": size, "items": rows})
    return {"groups": out, "total_bytes": total_projeto}
