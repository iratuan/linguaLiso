"""Configuração do backend.

Valores podem ser sobrescritos com variáveis de ambiente prefixadas por ``ETL_``
ou por um arquivo ``.env`` na pasta ``backend/``.
"""

import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent

# backend/.env (desenvolvimento) e, no app instalado, o arquivo em %APPDATA% indicado por ETL_ENV_FILE.
_ENV_FILES = [BACKEND_DIR / ".env"] + ([Path(os.environ["ETL_ENV_FILE"])] if os.environ.get("ETL_ENV_FILE") else [])


def env_file_path() -> Path:
    """Arquivo onde as chaves dos provedores são gravadas pela tela de Ajustes."""
    return Path(os.environ["ETL_ENV_FILE"]) if os.environ.get("ETL_ENV_FILE") else BACKEND_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ETL_", env_file=_ENV_FILES, extra="ignore")

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

    # Provedores na nuvem (opcionais). Só são usados quando o modelo escolhido tem o prefixo do provedor
    # (ex.: "groq/..."). Sem chave, o provedor aparece como indisponível e nada é enviado para fora.
    # As chaves ficam em backend/.env (nunca versionado).
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-haiku-5-5"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-nano"
    # Teto de tokens de resposta por chamada na nuvem: limita o custo e evita JSON cortado no meio.
    cloud_max_output_tokens: int = 2048

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
