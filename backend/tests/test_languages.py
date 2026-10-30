import shutil
import sqlite3

import pytest

from app.config import BACKEND_DIR, Settings
from app.curriculum.loader import normalize
from app.curriculum.registry import CurriculumRegistry
from app.db import Database
from app.languages import DEFAULT_LANGUAGE, LANGUAGES, get_language


# ----- cadastro e normalização ----------------------------------------------

def test_default_language_is_registered():
    assert DEFAULT_LANGUAGE in LANGUAGES
    assert get_language("en").voice == "en_US-lessac-medium"


def test_unknown_language_is_rejected():
    with pytest.raises(ValueError):
        get_language("de")


def test_accents_are_ignored_for_english_but_kept_for_french():
    assert normalize("Café", keep_accents=False) == normalize("cafe", keep_accents=False)
    # Em francês "été" (verão) e "ete" não são a mesma palavra.
    assert normalize("été", keep_accents=True) != normalize("ete", keep_accents=True)
    assert normalize("Été !", keep_accents=True) == "été"


def test_registry_loads_english_curriculum():
    registry = CurriculumRegistry.load(BACKEND_DIR / "app" / "curriculum")
    assert "en" in registry.languages()
    assert registry.get("en").exercise_count == 360
    assert registry.lesson("a1-1-1") is not None


# ----- configuração e sessões ----------------------------------------------

def test_target_language_defaults_to_english(client):
    assert client.get("/api/settings").json()["target_language"] == "en"


def test_target_language_rejects_unknown_code(client):
    assert client.put("/api/settings", json={"target_language": "de"}).status_code == 422


def test_new_session_records_the_target_language(client):
    session = client.post("/api/sessions", json={"mode": "free"}).json()
    assert session["language"] == "en"


def test_course_overview_reports_its_language(client):
    overview = client.get("/api/course").json()
    assert overview["language"] == {"code": "en", "name": "Inglês"}


def test_switching_to_french_shows_the_french_track(client):
    client.put("/api/settings", json={"target_language": "fr"})
    try:
        overview = client.get("/api/course").json()
        assert overview["language"] == {"code": "fr", "name": "Francês"}
        assert overview["next_lesson_id"] == "fr-a1-1-1"
    finally:
        client.put("/api/settings", json={"target_language": "en"})


def test_new_sessions_follow_the_target_language(client):
    client.put("/api/settings", json={"target_language": "fr"})
    try:
        session = client.post("/api/sessions", json={"mode": "free"}).json()
        assert session["language"] == "fr"
    finally:
        client.put("/api/settings", json={"target_language": "en"})


def test_french_exercise_is_case_insensitive_but_not_loose(client):
    """Maiúsculas não importam, mas outra palavra continua errada."""
    client.put("/api/settings", json={"target_language": "fr"})
    try:
        overview = client.get("/api/course").json()
        lesson = client.get("/api/course/lessons/fr-a1-1-1").json()
        exercise = lesson["exercises"][1]  # "Elle ___ de Paris." -> est
        assert overview["next_lesson_id"] == "fr-a1-1-1"
        assert client.post(f"/api/course/exercises/{exercise['id']}/check", json={"answer": "EST"}).json()["correct"]
        wrong = client.post(f"/api/course/exercises/{exercise['id']}/check", json={"answer": "és"}).json()
        assert wrong["correct"] is False
    finally:
        client.put("/api/settings", json={"target_language": "en"})


# ----- migração 0004 em banco existente ------------------------------------

def test_migration_keeps_existing_vocabulary_and_reviews(tmp_path):
    """Um banco da versão 3 (anterior ao suporte a idiomas) é atualizado sem perder dados."""
    real = BACKEND_DIR / "migrations"
    old = tmp_path / "old_migrations"
    old.mkdir()
    for path in sorted(real.glob("*.sql"))[:3]:  # só 0001..0003
        shutil.copy(path, old / path.name)

    cfg = Settings(data_dir=tmp_path / "data", _env_file=None)
    before = Database(cfg.db_path, old, cfg.backups_dir)
    assert before.migrate() == 3
    with before.connection() as conn:
        conn.execute(
            "INSERT INTO conversation_sessions (mode, title, level, model, started_at) "
            "VALUES ('free', 't', 'A1', 'qwen3:8b', '2026-10-01T10:00:00+00:00')"
        )
        conn.execute(
            "INSERT INTO vocabulary_items (term, translation_pt, box, next_review_at, created_at) "
            "VALUES ('hello', 'olá', 2, '2026-10-02T10:00:00+00:00', '2026-10-01T10:00:00+00:00')"
        )
        item_id = conn.execute("SELECT id FROM vocabulary_items WHERE term = 'hello'").fetchone()[0]
        conn.execute(
            "INSERT INTO vocabulary_reviews (item_id, rating, box_before, box_after, reviewed_at) "
            "VALUES (?, 'good', 1, 2, '2026-10-01T11:00:00+00:00')",
            (item_id,),
        )

    after = Database(cfg.db_path, real, cfg.backups_dir)
    assert after.migrate() == 7
    with after.connection() as conn:
        row = conn.execute("SELECT language, term, box FROM vocabulary_items").fetchone()
        assert (row["language"], row["term"], row["box"]) == ("en", "hello", 2)
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_reviews").fetchone()[0] == 1
        assert conn.execute("SELECT language FROM conversation_sessions").fetchone()[0] == "en"
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_same_word_can_exist_in_two_languages(tmp_path):
    cfg = Settings(data_dir=tmp_path / "data", _env_file=None)
    db = Database(cfg.db_path, cfg.migrations_dir, cfg.backups_dir)
    db.migrate()
    with db.transaction() as conn:
        conn.execute(
            "INSERT INTO vocabulary_items (language, term, next_review_at, created_at) VALUES ('en', 'chat', 'a', 'a')"
        )
        conn.execute(
            "INSERT INTO vocabulary_items (language, term, next_review_at, created_at) VALUES ('fr', 'chat', 'a', 'a')"
        )
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM vocabulary_items WHERE term = 'chat'").fetchone()[0] == 2
    with pytest.raises(sqlite3.IntegrityError):
        with db.transaction() as conn:
            conn.execute(
                "INSERT INTO vocabulary_items (language, term, next_review_at, created_at) VALUES ('fr', 'CHAT', 'a', 'a')"
            )
