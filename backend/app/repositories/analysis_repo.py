"""Análises de nível guardadas com a sessão analisada."""

from __future__ import annotations

import json
from typing import Any

from app.db import Database, utc_now


class AnalysisRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, *, session_id: int, model: str, declared_level: str, level_estimate: str,
            confidence: str, student_turns: int, payload: dict[str, Any]) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO level_analyses (session_id, created_at, model, declared_level, level_estimate,
                                            confidence, student_turns, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, utc_now(), model, declared_level, level_estimate, confidence, student_turns,
                 json.dumps(payload, ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def list_recent(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT a.id, a.session_id, a.created_at, a.level_estimate, a.confidence, a.declared_level,
                       a.student_turns, s.title AS session_title
                FROM level_analyses a JOIN conversation_sessions s ON s.id = a.session_id
                ORDER BY a.id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get(self, analysis_id: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM level_analyses WHERE id = ?", (analysis_id,)).fetchone()
        if row is None:
            return None
        return {"id": row["id"], "session_id": row["session_id"], "created_at": row["created_at"],
                "model": row["model"], **json.loads(row["payload"])}
