"""Aulas guiadas e seus exercícios."""

from __future__ import annotations

from typing import Any

from app.db import Database, utc_now


class LessonRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def create(self, *, title: str, objective: str, content_md: str, exercises: list[dict[str, str]]) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO lessons (title, objective, content_md, created_at) VALUES (?, ?, ?, ?)",
                (title, objective, content_md, utc_now()),
            )
            lesson_id = int(cursor.lastrowid)
            for position, exercise in enumerate(exercises, start=1):
                conn.execute(
                    """
                    INSERT INTO lesson_exercises (lesson_id, position, prompt, expected_answer)
                    VALUES (?, ?, ?, ?)
                    """,
                    (lesson_id, position, exercise["prompt"], exercise.get("expected_answer", "")),
                )
        return lesson_id

    def get(self, lesson_id: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            lesson = conn.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,)).fetchone()
            if lesson is None:
                return None
            exercises = conn.execute(
                "SELECT * FROM lesson_exercises WHERE lesson_id = ? ORDER BY position", (lesson_id,)
            ).fetchall()
        result = dict(lesson)
        result["exercises"] = [dict(e) for e in exercises]
        return result

    def list_recent(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT id, title, objective, status, created_at, completed_at FROM lessons "
                "ORDER BY created_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_exercise(self, lesson_id: int, position: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM lesson_exercises WHERE lesson_id = ? AND position = ?",
                (lesson_id, position),
            ).fetchone()
        return dict(row) if row else None

    def save_answer(self, lesson_id: int, position: int, user_answer: str, is_correct: bool, feedback: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                """
                UPDATE lesson_exercises
                SET user_answer = ?, is_correct = ?, feedback = ?, answered_at = ?
                WHERE lesson_id = ? AND position = ?
                """,
                (user_answer, int(is_correct), feedback, utc_now(), lesson_id, position),
            )

    def complete(self, lesson_id: int, summary: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE lessons SET status = 'completed', summary = ?, completed_at = ? WHERE id = ?",
                (summary, utc_now(), lesson_id),
            )
