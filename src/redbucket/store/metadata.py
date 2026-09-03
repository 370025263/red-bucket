"""SQLite 元数据访问。列名与 schema-sqlite.md 一致。"""
from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from redbucket.clock import utc_now
from redbucket.store.schema import SCHEMA_SQL

SCHEMA_VERSION = 1


class MetadataStore:
    def __init__(self, sqlite_path: Path) -> None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        self.sqlite_path = sqlite_path
        self._lock = threading.Lock()
        self.connection = sqlite3.connect(
            str(sqlite_path),
            check_same_thread=False,
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(SCHEMA_SQL)
        self._record_migration()

    def _record_migration(self) -> None:
        cursor = self.connection.execute(
            "SELECT version FROM schema_migrations WHERE version = ?",
            (SCHEMA_VERSION,),
        )
        if cursor.fetchone() is None:
            self.connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) "
                "VALUES (?, ?)",
                (SCHEMA_VERSION, utc_now()),
            )
            self.connection.commit()

    def execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> sqlite3.Cursor:
        return self.connection.execute(sql, params)

    def fetchone(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> sqlite3.Row | None:
        with self._lock:
            return self.connection.execute(sql, params).fetchone()

    def fetchall(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> list[sqlite3.Row]:
        with self._lock:
            return list(self.connection.execute(sql, params).fetchall())

    def run(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> sqlite3.Cursor:
        with self._lock:
            cursor = self.connection.execute(sql, params)
            return cursor

    def run_commit(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
    ) -> sqlite3.Cursor:
        with self._lock:
            cursor = self.connection.execute(sql, params)
            self.connection.commit()
            return cursor

    def commit(self) -> None:
        with self._lock:
            self.connection.commit()

    def rollback(self) -> None:
        with self._lock:
            self.connection.rollback()

    def immediate(self) -> None:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")

    @contextmanager
    def immediate_tx(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            self.connection.execute("BEGIN IMMEDIATE")
            try:
                yield self.connection
                self.connection.commit()
            except Exception:
                self.connection.rollback()
                raise

    def close(self) -> None:
        with self._lock:
            self.connection.close()
