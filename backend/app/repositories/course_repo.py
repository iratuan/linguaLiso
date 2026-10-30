"""Progresso do curso: lições concluídas e resultado de cada exercício."""

from __future__ import annotations

import json
from typing import Any

from app.db import Database, utc_now


class CourseRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def lesson_progress(self) -> dict[str, dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute("SELECT * FROM course_lesson_progress").fetchall()
        return {r["lesson_id"]: dict(r) for r in rows}

    def started_lessons(self) -> set[str]:
        with self._db.connection() as conn:
            rows = conn.execute("SELECT DISTINCT lesson_id FROM course_exercise_results").fetchall()
        return {r["lesson_id"] for r in rows}

    def exercise_results(self, lesson_id: str) -> dict[str, dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM course_exercise_results WHERE lesson_id = ?", (lesson_id,)
            ).fetchall()
        return {r["exercise_id"]: dict(r) for r in rows}

    def save_exercise_result(self, lesson_id: str, exercise_id: str, correct: bool, answer: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO course_exercise_results (lesson_id, exercise_id, correct, last_answer, attempts, updated_at)
                VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(lesson_id, exercise_id) DO UPDATE SET
                    correct = excluded.correct,
                    last_answer = excluded.last_answer,
                    attempts = attempts + 1,
                    updated_at = excluded.updated_at
                """,
                (lesson_id, exercise_id, int(correct), answer[:500], utc_now()),
            )

    def finish_lesson(self, lesson_id: str, score: int, passed: bool) -> dict[str, Any]:
        now = utc_now()
        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO course_lesson_progress (lesson_id, score, completed, attempts, completed_at, updated_at)
                VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(lesson_id) DO UPDATE SET
                    -- A nota guardada é a melhor já obtida, mesmo ao refazer a lição.
                    score = MAX(course_lesson_progress.score, excluded.score),
                    completed = MAX(course_lesson_progress.completed, excluded.completed),
                    completed_at = COALESCE(course_lesson_progress.completed_at, excluded.completed_at),
                    attempts = course_lesson_progress.attempts + 1,
                    updated_at = excluded.updated_at
                """,
                (lesson_id, score, int(passed), now if passed else None, now),
            )
            row = conn.execute("SELECT * FROM course_lesson_progress WHERE lesson_id = ?", (lesson_id,)).fetchone()
        return dict(row)

    def log_attempt(self, lesson_id: str, exercise_id: str, exercise_type: str, correct: bool, answer: str) -> None:
        with self._db.transaction() as conn:
            conn.execute(
                """
                INSERT INTO course_attempts (lesson_id, exercise_id, exercise_type, correct, answer, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (lesson_id, exercise_id, exercise_type, int(correct), answer[:500], utc_now()),
            )

    def clear_exercise_results(self, lesson_id: str) -> None:
        with self._db.transaction() as conn:
            conn.execute("DELETE FROM course_exercise_results WHERE lesson_id = ?", (lesson_id,))

    # ----- rascunhos de lições criadas pelo modelo ----------------------------

    def add_draft(self, language: str, level: str, title: str, lesson: dict[str, Any]) -> int:
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO course_lesson_drafts (language, level, title, payload, created_at) VALUES (?, ?, ?, ?, ?)",
                (language, level, title[:200], json.dumps(lesson, ensure_ascii=False), utc_now()),
            )
            return int(cursor.lastrowid)

    def list_drafts(self) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute("SELECT * FROM course_lesson_drafts ORDER BY id").fetchall()
        return [{**dict(r), "lesson": json.loads(r["payload"])} for r in rows]

    def get_draft(self, draft_id: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM course_lesson_drafts WHERE id = ?", (draft_id,)).fetchone()
        return {**dict(row), "lesson": json.loads(row["payload"])} if row else None

    def delete_draft(self, draft_id: int) -> bool:
        with self._db.transaction() as conn:
            cursor = conn.execute("DELETE FROM course_lesson_drafts WHERE id = ?", (draft_id,))
        return cursor.rowcount > 0
