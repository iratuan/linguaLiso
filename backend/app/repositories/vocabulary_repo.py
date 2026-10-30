"""Vocabulário e revisão espaçada (tabelas ``vocabulary_items`` e ``vocabulary_reviews``)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.db import Database, utc_now
from app.services.srs import Rating, schedule_review


class VocabularyRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    def add_many(self, items: list[dict[str, str]], source_session_id: int | None, language: str = "en") -> list[int]:
        """Insere itens novos. Um termo já existente no mesmo idioma é ignorado (sem duplicar)."""
        now = utc_now()
        inserted: list[int] = []
        with self._db.transaction() as conn:
            for item in items:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO vocabulary_items
                        (language, term, translation_pt, example_sentence, source_session_id, box, next_review_at, created_at)
                    VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        language,
                        item["term"].strip(),
                        item.get("translation_pt", ""),
                        item.get("example_sentence", ""),
                        source_session_id,
                        now,
                        now,
                    ),
                )
                if cursor.rowcount:
                    inserted.append(int(cursor.lastrowid))
        return inserted

    def create(self, term: str, translation_pt: str, example_sentence: str, language: str = "en") -> dict[str, Any]:
        ids = self.add_many(
            [{"term": term, "translation_pt": translation_pt, "example_sentence": example_sentence}],
            source_session_id=None,
            language=language,
        )
        if not ids:
            raise ValueError(f"O termo '{term}' já está no vocabulário.")
        result = self.get(ids[0])
        assert result is not None
        return result

    def get(self, item_id: int) -> dict[str, Any] | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM vocabulary_items WHERE id = ?", (item_id,)).fetchone()
        return dict(row) if row else None

    def list_for_session(self, session_id: int) -> list[dict[str, Any]]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM vocabulary_items WHERE source_session_id = ? ORDER BY id", (session_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_items(self, due_only: bool = False, limit: int = 200) -> list[dict[str, Any]]:
        sql = "SELECT * FROM vocabulary_items"
        params: list[Any] = []
        if due_only:
            sql += " WHERE next_review_at <= ?"
            params.append(utc_now())
        sql += " ORDER BY next_review_at, id LIMIT ?"
        params.append(limit)
        with self._db.connection() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def record_review(self, item_id: int, rating: Rating, now: datetime | None = None) -> dict[str, Any]:
        with self._db.transaction() as conn:
            row = conn.execute("SELECT box FROM vocabulary_items WHERE id = ?", (item_id,)).fetchone()
            if row is None:
                raise LookupError("Item de vocabulário não encontrado.")
            box_before = int(row["box"])
            box_after, next_at = schedule_review(box_before, rating, now)
            reviewed_at = utc_now()
            conn.execute(
                "UPDATE vocabulary_items SET box = ?, next_review_at = ? WHERE id = ?",
                (box_after, next_at.isoformat(timespec="seconds"), item_id),
            )
            conn.execute(
                """
                INSERT INTO vocabulary_reviews (item_id, rating, box_before, box_after, reviewed_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (item_id, rating, box_before, box_after, reviewed_at),
            )
        result = self.get(item_id)
        assert result is not None
        return result

    def delete(self, item_id: int) -> bool:
        with self._db.transaction() as conn:
            return conn.execute("DELETE FROM vocabulary_items WHERE id = ?", (item_id,)).rowcount > 0

    def counts(self) -> dict[str, int]:
        now = utc_now()
        with self._db.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN next_review_at <= ? THEN 1 ELSE 0 END) AS due,
                    SUM(CASE WHEN box >= 4 THEN 1 ELSE 0 END) AS mastered
                FROM vocabulary_items
                """,
                (now,),
            ).fetchone()
        return {k: int(row[k] or 0) for k in ("total", "due", "mastered")}
