"""Preferências do app (tabela ``app_settings``) e perfil do aluno (``learner_profile``)."""

from __future__ import annotations

import json
from typing import Any

from app.db import Database, utc_now
from app.domain import ProfileIn

DEFAULT_SETTINGS: dict[str, Any] = {
    "llm_model": None,  # None = usar o padrão da configuração do backend
    "llm_temperature": 0.7,
    "llm_num_ctx": 4096,
    "history_limit": 12,
    # Idioma-alvo da trilha e das conversas. Novas sessões usam este idioma.
    "target_language": "en",
    # None = usa a voz padrão do idioma (ver app/languages.py).
    "speech_voice": None,
    "speech_rate": 1.0,
    "speech_volume": 1.0,
    "confirm_transcription": True,
    # "audio": o professor responde em voz (padrão); "text": somente texto.
    "response_mode": "audio",
    # Personalidade do professor nas novas conversas: formal, descontraido ou nativo.
    "teacher_persona": "descontraido",
    # Transparência da interface, em %: 0 é opaca e 80 é quase transparente.
    "ui_transparency": 45,
    # Tema visual: "escuro" (padrão) ou "papel" (estilo Kindle, fundo claro e fonte serifada).
    "app_theme": "escuro",
}


class SettingsRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_all(self) -> dict[str, Any]:
        merged = dict(DEFAULT_SETTINGS)
        with self._db.connection() as conn:
            rows = conn.execute("SELECT key, value FROM app_settings").fetchall()
        for row in rows:
            if row["key"] in merged:
                merged[row["key"]] = json.loads(row["value"])
        return merged

    def update(self, values: dict[str, Any]) -> dict[str, Any]:
        unknown = set(values) - set(DEFAULT_SETTINGS)
        if unknown:
            raise ValueError(f"Configurações desconhecidas: {', '.join(sorted(unknown))}")
        now = utc_now()
        with self._db.transaction() as conn:
            for key, value in values.items():
                conn.execute(
                    """
                    INSERT INTO app_settings (key, value, updated_at) VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                    """,
                    (key, json.dumps(value), now),
                )
        return self.get_all()


class ProfileRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def get(self) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM learner_profile WHERE id = 1").fetchone()
        return dict(row) if row else None

    def save(self, profile: ProfileIn) -> dict[str, Any]:
        now = utc_now()
        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO learner_profile
                    (id, display_name, level, english_variant, explanation_language,
                     study_minutes_goal, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name = excluded.display_name,
                    level = excluded.level,
                    english_variant = excluded.english_variant,
                    explanation_language = excluded.explanation_language,
                    study_minutes_goal = excluded.study_minutes_goal,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.display_name,
                    profile.level,
                    profile.english_variant,
                    profile.explanation_language,
                    profile.study_minutes_goal,
                    now,
                    now,
                ),
            )
        result = self.get()
        assert result is not None
        return result
