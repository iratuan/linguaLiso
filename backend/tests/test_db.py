import sqlite3

import pytest

from app.db import Database
from app.config import Settings


def make_db(tmp_path, migrations_dir=None):
    cfg = Settings(data_dir=tmp_path / "data", _env_file=None)
    return Database(cfg.db_path, migrations_dir or cfg.migrations_dir, cfg.backups_dir), cfg


def test_initializes_schema_on_empty_database(tmp_path):
    db, _ = make_db(tmp_path)
    assert db.migrate() == 7
    with db.connection() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    expected = {
        "learner_profile", "learning_goals", "conversation_sessions", "messages", "corrections",
        "lessons", "lesson_exercises", "vocabulary_items", "vocabulary_reviews", "app_settings",
    }
    assert expected <= tables


def test_migrate_is_idempotent(tmp_path):
    db, _ = make_db(tmp_path)
    db.migrate()
    assert db.migrate() == 7
    assert db.schema_version() == 7


def test_foreign_keys_are_enforced(tmp_path):
    db, _ = make_db(tmp_path)
    db.migrate()
    with db.connection() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (999, 'user', 'x', 'now')"
        )


def test_check_constraints_reject_invalid_level(tmp_path):
    db, _ = make_db(tmp_path)
    db.migrate()
    with db.connection() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO learner_profile (id, level, created_at, updated_at) VALUES (1, 'Z9', 'a', 'a')"
        )


def test_transaction_rolls_back_on_error(tmp_path):
    db, _ = make_db(tmp_path)
    db.migrate()
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES ('k', '1', 'a')")
            raise RuntimeError("boom")
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM app_settings").fetchone()[0] == 0


def test_backup_created_before_applying_new_migration(tmp_path):
    db, cfg = make_db(tmp_path)
    db.migrate()
    with db.transaction() as conn:
        conn.execute("INSERT INTO app_settings (key, value, updated_at) VALUES ('keep', '1', 'a')")

    migrations = tmp_path / "migrations"
    migrations.mkdir()
    for src in cfg.migrations_dir.glob("*.sql"):
        (migrations / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    (migrations / "0008_extra.sql").write_text(
        "CREATE TABLE extra (id INTEGER PRIMARY KEY);", encoding="utf-8"
    )
    upgraded = Database(cfg.db_path, migrations, cfg.backups_dir)
    assert upgraded.migrate() == 8
    backups = list(cfg.backups_dir.glob("*.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as backup:
        assert backup.execute("PRAGMA user_version").fetchone()[0] == 7


def test_numbering_gap_is_rejected(tmp_path):
    migrations = tmp_path / "m"
    migrations.mkdir()
    (migrations / "0001_a.sql").write_text("SELECT 1;")
    (migrations / "0003_c.sql").write_text("SELECT 1;")
    db = Database(tmp_path / "x.sqlite3", migrations, tmp_path / "b")
    with pytest.raises(RuntimeError, match="sem lacunas"):
        db.available_migrations()
