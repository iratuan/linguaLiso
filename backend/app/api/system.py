"""Saúde do sistema, diagnóstico, preferências e perfil do aluno."""

import shutil
from typing import Any

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_container
from app.container import Container
from app.domain import ProfileIn, SettingsIn

router = APIRouter(tags=["sistema"])


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
    return values


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
