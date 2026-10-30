"""Sessões de conversa, mensagens e correções."""

from __future__ import annotations

from typing import Any

from app.db import Database, utc_now


class SessionRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(
        self,
        *,
        mode: str,
        scenario: str | None,
        title: str,
        level: str,
        model: str,
        language: str = "en",
        persona: str = "descontraido",
    ) -> dict[str, Any]:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversation_sessions (mode, scenario, title, level, model, language, persona, started_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (mode, scenario, title, level, model, language, persona, utc_now()),
            )
            session_id = cursor.lastrowid
        result = self.get(session_id)
        assert result is not None
        return result

    def get(self, session_id: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM conversation_sessions WHERE id = ?", (session_id,)).fetchone()
        return dict(row) if row else None

    def list_recent(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*, (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id) AS message_count
                FROM conversation_sessions s
                ORDER BY s.started_at DESC, s.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def end(self, session_id: int) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE conversation_sessions SET ended_at = ? WHERE id = ? AND ended_at IS NULL",
                (utc_now(), session_id),
            )

    def delete(self, session_id: int) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute("DELETE FROM conversation_sessions WHERE id = ?", (session_id,))
            return cursor.rowcount > 0

    def add_message(self, session_id: int, role: str, content: str, input_source: str = "text") -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (session_id, role, content, input_source, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, role, content, input_source, utc_now()),
            )
            return int(cursor.lastrowid)

    def count_user_messages(self, session_id: int) -> int:
        """Quantas falas o aluno já fez nesta conversa (conta a conversa inteira, não só o histórico enviado)."""
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM messages WHERE session_id = ? AND role = 'user'", (session_id,)
            ).fetchone()
        return int(row["n"])

    def list_messages(self, session_id: int, limit: int | None = None) -> list[dict[str, Any]]:
        """Mensagens em ordem cronológica. Com ``limit``, devolve as últimas N."""
        with self._db.connection() as conn:
            if limit is None:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE session_id = ? ORDER BY id", (session_id,)
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM (
                        SELECT * FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?
                    ) ORDER BY id
                    """,
                    (session_id, limit),
                ).fetchall()
        return [dict(r) for r in rows]

    def add_correction(self, *, message_id: int, session_id: int, data: dict[str, str], error_category: str,
                       severity: str) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO corrections (
                    message_id, session_id, original_text, corrected_text, explanation_pt,
                    error_category, severity, example_sentence, practice_prompt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    data["original_text"],
                    data["corrected_text"],
                    data["explanation_pt"],
                    error_category,
                    severity,
                    data["example_sentence"],
                    data["practice_prompt"],
                    utc_now(),
                ),
            )
            return int(cursor.lastrowid)

    def list_corrections(self, session_id: int) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM corrections WHERE session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]
