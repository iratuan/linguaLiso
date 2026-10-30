"""Configuração do backend.

Valores podem ser sobrescritos com variáveis de ambiente prefixadas por ``ETL_``
ou por um arquivo ``.env`` na pasta ``backend/``.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ETL_", env_file=BACKEND_DIR / ".env", extra="ignore")

    data_dir: Path = PROJECT_DIR / "data"
    db_filename: str = "english_teacher.sqlite3"

    prompts_dir: Path = BACKEND_DIR / "prompts"
    migrations_dir: Path = BACKEND_DIR / "migrations"
    curriculum_dir: Path = BACKEND_DIR / "app" / "curriculum"

    # LLM (Ollama, sempre local)
    ollama_url: str = "http://127.0.0.1:11434"
    default_llm_model: str = "qwen3:8b"
    fallback_llm_model: str = "qwen3:4b"
    llm_temperature: float = 0.7
    llm_num_ctx: int = 4096
    llm_timeout_s: float = 120.0

    # Servidor de voz (ai-model)
    speech_url: str = "http://127.0.0.1:8001"
    speech_timeout_s: float = 60.0

    # Limites
    history_limit: int = 12
    max_message_chars: int = 2000
    max_audio_bytes: int = 10 * 1024 * 1024

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",  # renderer carregado via file:// no Electron empacotado
    ]

    @property
    def db_path(self) -> Path:
        return self.data_dir / self.db_filename

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"


@lru_cache
def get_settings() -> Settings:
    return Settings()
