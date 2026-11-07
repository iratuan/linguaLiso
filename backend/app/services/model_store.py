"""Gerência local: download de modelos do Ollama com progresso, espaço em disco e chaves dos provedores.

Nada aqui é usado no caminho da conversa; são as ações da tela de Ajustes.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

MODEL_NAME_RE = re.compile(r"^[A-Za-z0-9._:/-]{1,120}$")


def find_ollama_binary() -> str | None:
    """Mesma regra do script de início: PATH primeiro, depois a instalação padrão do Ollama no Windows."""
    found = shutil.which("ollama")
    if found:
        return found
    local = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return str(local) if local.is_file() else None


def ollama_models_dir() -> Path:
    """Onde o Ollama guarda os modelos (OLLAMA_MODELS ou a pasta padrão do usuário)."""
    custom = os.environ.get("OLLAMA_MODELS")
    return Path(custom) if custom else Path.home() / ".ollama" / "models"


class ModelPuller:
    """Baixa um modelo pelo endpoint /api/pull do Ollama, em segundo plano, com progresso."""

    def __init__(self, base_url: str, transport: httpx.BaseTransport | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._transport = transport
        self._lock = threading.Lock()
        self._state: dict[str, Any] = {"model": None, "status": "idle", "percent": None, "error": None}

    def state(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def start(self, model: str) -> dict[str, Any]:
        if not MODEL_NAME_RE.match(model) or ".." in model or model.startswith("/"):
            raise ValueError("Nome de modelo inválido.")
        with self._lock:
            if self._state["status"] == "downloading":
                raise RuntimeError("Já existe um download em andamento.")
            self._state = {"model": model, "status": "downloading", "percent": 0.0, "error": None}
        threading.Thread(target=self._run, args=(model,), daemon=True).start()
        return self.state()

    def _set(self, **changes: Any) -> None:
        with self._lock:
            self._state.update(changes)

    def _run(self, model: str) -> None:
        try:
            with httpx.Client(base_url=self._base_url, timeout=httpx.Timeout(30.0, read=None),
                              transport=self._transport) as client:
                with client.stream("POST", "/api/pull", json={"model": model, "stream": True}) as response:
                    if response.status_code >= 400:
                        raise RuntimeError(f"o Ollama recusou o download (HTTP {response.status_code}).")
                    for line in response.iter_lines():
                        if not line:
                            continue
                        event = json.loads(line)
                        if event.get("error"):
                            raise RuntimeError(str(event["error"]))
                        total, done = event.get("total"), event.get("completed")
                        if total and done is not None:
                            self._set(percent=round(100.0 * done / total, 1))
            self._set(status="done", percent=100.0)
        except (httpx.HTTPError, RuntimeError, ValueError) as exc:
            # Mensagem curta para o aluno; o detalhe técnico vai para o log.
            log.warning("Falha ao baixar o modelo %s: %s", model, exc)
            self._set(status="error", error=f"Não foi possível baixar {model}. Verifique a conexão e se o Ollama está aberto.")


def measure(path: Path, ttl_cache: dict[str, tuple[float, int]] | None = None, key: str | None = None) -> int:
    """Tamanho total em bytes de uma pasta (0 se não existir). Usa cache curto para não varrer a cada requisição."""
    if ttl_cache is not None and key is not None:
        hit = ttl_cache.get(key)
        if hit and time.monotonic() - hit[0] < 60:
            return hit[1]
    total = 0
    if path.is_dir():
        stack = [path]
        while stack:
            current = stack.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(Path(entry.path))
                            else:
                                total += entry.stat(follow_symlinks=False).st_size
                        except OSError:
                            continue
            except OSError:
                continue
    elif path.is_file():
        total = path.stat().st_size
    if ttl_cache is not None and key is not None:
        ttl_cache[key] = (time.monotonic(), total)
    return total


def write_env_values(path: Path, values: dict[str, str | None]) -> None:
    """Atualiza chaves num arquivo .env. Valor None remove a linha. Preserva as demais linhas."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    remaining = dict(values)
    out: list[str] = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        if key in remaining:
            value = remaining.pop(key)
            if value is not None:
                out.append(f"{key}={value}")
            continue
        out.append(line)
    for key, value in remaining.items():
        if value is not None:
            out.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")


def key_hint(key: str) -> str:
    """Só os últimos 4 caracteres, para o aluno reconhecer qual chave está salva."""
    return f"…{key[-4:]}" if len(key) > 8 else ("configurada" if key else "")
