"""Consultas de progresso, histórico de erros e exportação/exclusão dos dados do aluno."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import Database, utc_now

_LEARNER_TABLES = (
    "corrections",
    "messages",
    "conversation_sessions",
    "vocabulary_reviews",
    "vocabulary_items",
    "lesson_exercises",
    "lessons",
    "learning_goals",
    "course_exercise_results",
    "course_lesson_progress",
    "course_attempts",
)


class ProgressRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def summary(self, days: int = 14) -> dict[str, Any]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
        with self._db.connection() as conn:
            totals = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM conversation_sessions) AS sessions,
                    (SELECT COUNT(*) FROM messages WHERE role = 'user') AS user_messages,
                    (SELECT COUNT(*) FROM corrections) AS corrections,
                    (SELECT COUNT(*) FROM lessons WHERE status = 'completed') AS lessons_completed
                """
            ).fetchone()
            by_category = conn.execute(
                """
                SELECT error_category AS category, COUNT(*) AS count
                FROM corrections GROUP BY error_category ORDER BY count DESC
                """
            ).fetchall()
            daily = conn.execute(
                """
                SELECT substr(started_at, 1, 10) AS day, COUNT(*) AS sessions
                FROM conversation_sessions
                WHERE started_at >= ?
                GROUP BY day ORDER BY day
                """,
                (since,),
            ).fetchall()
            recent = conn.execute(
                """
                SELECT c.original_text, c.corrected_text, c.error_category, c.created_at
                FROM corrections c ORDER BY c.id DESC LIMIT 10
                """
            ).fetchall()
        return {
            "totals": {k: int(totals[k] or 0) for k in totals.keys()},
            "errors_by_category": [dict(r) for r in by_category],
            "daily_sessions": [dict(r) for r in daily],
            "recent_corrections": [dict(r) for r in recent],
        }

    # ----- séries para a curva de evolução -------------------------------

    def user_messages_since(self, since: str) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT substr(created_at, 1, 10) AS day, content FROM messages "
                "WHERE role = 'user' AND created_at >= ?",
                (since,),
            ).fetchall()
        return [dict(r) for r in rows]

    def corrections_since(self, since: str) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM corrections "
                "WHERE created_at >= ? GROUP BY day",
                (since,),
            ).fetchall()
        return [dict(r) for r in rows]

    def attempts_since(self, since: str) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT substr(created_at, 1, 10) AS day, SUM(correct) AS correct, COUNT(*) AS total "
                "FROM course_attempts WHERE created_at >= ? GROUP BY day",
                (since,),
            ).fetchall()
        return [dict(r) for r in rows]

    def vocabulary_since(self, since: str) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM vocabulary_items "
                "WHERE created_at >= ? GROUP BY day",
                (since,),
            ).fetchall()
        return [dict(r) for r in rows]

    def lessons_completed(self) -> list[dict[str, Any]]:
        """Lições do curso concluídas, com a nota e o dia, na ordem em que foram terminadas."""
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT lesson_id, score, completed_at FROM course_lesson_progress "
                "WHERE completed = 1 ORDER BY completed_at"
            ).fetchall()
        return [dict(r) for r in rows]

    def recurring_errors(self, limit: int = 8) -> list[dict[str, Any]]:
        """Erros mais frequentes, agrupados pela forma corrigida. Usado para revisão de erros."""
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT corrected_text, error_category, explanation_pt, MAX(practice_prompt) AS practice_prompt,
                       COUNT(*) AS occurrences
                FROM corrections
                GROUP BY corrected_text, error_category
                ORDER BY occurrences DESC, MAX(id) DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def export_all(self) -> dict[str, Any]:
        """Exporta o histórico do aluno em JSON aberto (sem preferências do app)."""
        data: dict[str, Any] = {"exported_at": utc_now(), "format": "english-teacher-local/1"}
        with self._db.connection() as conn:
            for table in ("learner_profile", "learning_goals", "conversation_sessions", "messages", "corrections",
                          "lessons", "lesson_exercises", "vocabulary_items", "vocabulary_reviews",
                          "course_lesson_progress", "course_exercise_results", "course_attempts"):
                data[table] = [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]
        return data

    def delete_learner_data(self) -> None:
        """Apaga perfil, sessões, correções, aulas e vocabulário. Preferências do app são mantidas."""
        with self._db.transaction() as conn:
            for table in _LEARNER_TABLES:
                conn.execute(f"DELETE FROM {table}")
            conn.execute("DELETE FROM learner_profile")
