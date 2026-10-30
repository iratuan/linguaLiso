"""Acesso ao SQLite com migrações versionadas.

A versão do esquema fica em ``PRAGMA user_version``. Cada arquivo ``NNNN_nome.sql``
em ``migrations/`` é aplicado uma única vez, dentro de uma transação. Antes de
aplicar migrações sobre um banco que já tem dados, o arquivo é copiado para
``data/backups/``.
"""

from __future__ import annotations

import logging
import re
import shutil
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_MIGRATION_RE = re.compile(r"^(\d{4})_[\w-]+\.sql$")


def utc_now() -> str:
    """Timestamp ISO 8601 em UTC, usado em todas as colunas de data."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Database:
    def __init__(self, path: Path, migrations_dir: Path, backups_dir: Path) -> None:
        self.path = path
        self.migrations_dir = migrations_dir
        self.backups_dir = backups_dir

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
            except BaseException:
                conn.execute("ROLLBACK")
                raise
            else:
                conn.execute("COMMIT")

    def available_migrations(self) -> list[tuple[int, Path]]:
        found: list[tuple[int, Path]] = []
        for path in sorted(self.migrations_dir.glob("*.sql")):
            match = _MIGRATION_RE.match(path.name)
            if not match:
                raise RuntimeError(f"Nome de migração inválido: {path.name}")
            found.append((int(match.group(1)), path))
        versions = [v for v, _ in found]
        if versions != list(range(1, len(versions) + 1)):
            raise RuntimeError("As migrações devem ser numeradas sem lacunas, começando em 0001.")
        return found

    def schema_version(self) -> int:
        with self.connection() as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])

    def migrate(self) -> int:
        """Aplica migrações pendentes. Retorna a versão final do esquema."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        current = self.schema_version()
        pending = [(v, p) for v, p in self.available_migrations() if v > current]
        if not pending:
            return current

        if current > 0 and self.path.exists():
            self._backup(current)

        for version, path in pending:
            log.info("Aplicando migração %04d (%s)", version, path.name)
            sql = path.read_text(encoding="utf-8")
            conn = self.connect()
            try:
                # Reconstruções de tabela (DROP + RENAME) não podem disparar ON DELETE CASCADE.
                # O PRAGMA só tem efeito fora de transação, então é definido antes do BEGIN.
                conn.execute("PRAGMA foreign_keys = OFF")
                conn.execute("BEGIN IMMEDIATE")
                for statement in _split_statements(sql):
                    conn.execute(statement)
                violations = conn.execute("PRAGMA foreign_key_check").fetchall()
                if violations:
                    raise RuntimeError(f"Migração {version:04d} deixou {len(violations)} referências quebradas.")
                conn.execute(f"PRAGMA user_version = {int(version)}")
                conn.execute("COMMIT")
            except BaseException:
                if conn.in_transaction:
                    conn.execute("ROLLBACK")
                raise
            finally:
                conn.execute("PRAGMA foreign_keys = ON")
                conn.close()
        return self.schema_version()

    def _backup(self, version: int) -> Path:
        self.backups_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.backups_dir / f"{self.path.stem}-v{version}-{stamp}.sqlite3"
        # Checkpoint do WAL antes de copiar, para o arquivo principal ficar completo.
        with self.connection() as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copy2(self.path, target)
        log.info("Backup do banco criado em %s", target)
        return target


def _split_statements(sql: str) -> list[str]:
    """Separa um script SQL em instruções individuais (sem comentários de linha)."""
    lines = [line for line in sql.splitlines() if not line.strip().startswith("--")]
    statements: list[str] = []
    buffer = ""
    for line in lines:
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            if buffer.strip():
                statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise RuntimeError("Migração termina com instrução SQL incompleta.")
    return statements
