"""database_admin.py — administration of the local NUCLEUS SQLite repository.

Backs the admin-only Database module: table browsing, a read-only query
console, clearing/dropping tables, resetting the database, and import/export.

Safety rules:
* Table names are never interpolated from user input directly; every name is
  checked against ``sqlite_master`` and quoted.
* The query console opens the file read-only (``mode=ro``), so a typed
  statement can never change data. Changes go through the confirmed actions.
* Every destructive action (clear, drop, reset, import) first writes a
  timestamped backup next to the database; the newest ``KEEP_BACKUPS`` are kept.
* A replacement database is validated (SQLite header + integrity check) and
  swapped in atomically with ``os.replace``.

The module never imports Streamlit, so it stays unit-testable in isolation.
"""
from __future__ import annotations

import glob
import os
import sqlite3
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import pandas as pd

import analytics_db

SQLITE_HEADER = b"SQLite format 3\x00"
MAX_RESULT_ROWS = 1000          # rows shown by the query console
QUERY_TIMEOUT_SECONDS = 10.0    # a console query is aborted after this
KEEP_BACKUPS = 5


class DatabaseError(Exception):
    """A user-facing failure (bad SQL, invalid file, unknown table, I/O)."""


@dataclass
class ColumnInfo:
    name: str
    type: str
    not_null: bool
    primary_key: bool


@dataclass
class TableInfo:
    name: str
    rows: int
    columns: list = field(default_factory=list)   # list[ColumnInfo]


@dataclass
class QueryResult:
    frame: pd.DataFrame
    truncated: bool          # more rows existed than MAX_RESULT_ROWS
    elapsed_ms: float


def quote(name: str) -> str:
    """SQLite identifier quoting."""
    return '"' + name.replace('"', '""') + '"'


def format_bytes(size: Optional[int]) -> str:
    if size is None:
        return "-"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _user_tables(conn: sqlite3.Connection) -> list:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
    return [r[0] for r in rows]


def validate_sqlite_bytes(data: bytes) -> list:
    """Table names of an uploaded SQLite file, or DatabaseError if invalid."""
    if not data or not data.startswith(SQLITE_HEADER):
        raise DatabaseError("not_sqlite")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "upload.db")
        with open(path, "wb") as fh:
            fh.write(data)
        try:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                status = conn.execute("PRAGMA integrity_check").fetchone()[0]
                if status != "ok":
                    raise DatabaseError("integrity")
                return _user_tables(conn)
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise DatabaseError("not_sqlite") from exc


class DatabaseAdmin:
    def __init__(self, path: Optional[str] = None):
        self.path = path or analytics_db.AnalyticsDB().path

    # ------------------------------------------------------------ inspect --
    def exists(self) -> bool:
        return os.path.exists(self.path)

    def file_size(self) -> Optional[int]:
        try:
            return os.path.getsize(self.path)
        except OSError:
            return None

    def modified(self) -> Optional[datetime]:
        try:
            return datetime.fromtimestamp(os.path.getmtime(self.path))
        except OSError:
            return None

    def _read_only(self) -> sqlite3.Connection:
        if not self.exists():
            raise DatabaseError("missing")
        return sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)

    def tables(self) -> list:
        """TableInfo for every user table (empty list without a database)."""
        if not self.exists():
            return []
        conn = self._read_only()
        try:
            out = []
            for name in _user_tables(conn):
                rows = conn.execute(f"SELECT COUNT(*) FROM {quote(name)}").fetchone()[0]
                cols = [ColumnInfo(c[1], c[2] or "", bool(c[3]), bool(c[5]))
                        for c in conn.execute(f"PRAGMA table_info({quote(name)})")]
                out.append(TableInfo(name, int(rows), cols))
            return out
        finally:
            conn.close()

    def table_names(self) -> list:
        return [t.name for t in self.tables()]

    def _checked(self, table: str) -> str:
        if table not in self.table_names():
            raise DatabaseError("unknown_table")
        return table

    def preview(self, table: str, limit: int = 100) -> pd.DataFrame:
        table = self._checked(table)
        conn = self._read_only()
        try:
            return pd.read_sql_query(
                f"SELECT * FROM {quote(table)} LIMIT ?", conn, params=(int(limit),))
        finally:
            conn.close()

    # -------------------------------------------------------------- query --
    def run_query(self, sql: str, max_rows: int = MAX_RESULT_ROWS,
                  timeout: float = QUERY_TIMEOUT_SECONDS) -> QueryResult:
        """Run one statement on a read-only connection.

        Writes fail with "attempt to write a readonly database"; a query that
        runs longer than ``timeout`` seconds is interrupted.
        """
        sql = (sql or "").strip()
        if not sql:
            raise DatabaseError("empty_query")
        conn = self._read_only()
        deadline = time.monotonic() + timeout
        conn.set_progress_handler(lambda: int(time.monotonic() > deadline), 10_000)
        start = time.perf_counter()
        try:
            cur = conn.execute(sql)
            if cur.description is None:          # e.g. PRAGMA with no output
                frame = pd.DataFrame()
                truncated = False
            else:
                rows = cur.fetchmany(max_rows + 1)
                truncated = len(rows) > max_rows
                frame = pd.DataFrame(rows[:max_rows],
                                     columns=[d[0] for d in cur.description])
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc):
                raise DatabaseError("timeout") from exc
            raise DatabaseError(str(exc)) from exc
        except (sqlite3.Error, sqlite3.Warning, ValueError) as exc:
            raise DatabaseError(str(exc)) from exc
        finally:
            conn.close()
        return QueryResult(frame, truncated, (time.perf_counter() - start) * 1000)

    # ------------------------------------------------------------- backup --
    def backup(self) -> Optional[str]:
        """Copy the current database next to it; returns the backup path."""
        if not self.exists():
            return None
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = f"{self.path}.backup-{stamp}"
        try:
            src = sqlite3.connect(f"file:{self.path}?mode=ro", uri=True)
            dst = sqlite3.connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
        except (sqlite3.Error, OSError) as exc:
            raise DatabaseError(f"backup_failed: {exc}") from exc
        for old in self.backups()[KEEP_BACKUPS:]:
            try:
                os.remove(old)
            except OSError:
                pass
        return target

    def backups(self) -> list:
        """Backup files, newest first."""
        return sorted(glob.glob(glob.escape(self.path) + ".backup-*"), reverse=True)

    # ------------------------------------------------------------ mutate --
    def _write(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _mutate(self, statements: list) -> None:
        try:
            conn = self._write()
            try:
                with conn:
                    for stmt in statements:
                        conn.execute(stmt)
                conn.execute("VACUUM")
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise DatabaseError(str(exc)) from exc

    def clear_table(self, table: str) -> int:
        """Delete every row of ``table`` (schema kept). Returns rows removed."""
        table = self._checked(table)
        rows = next(t.rows for t in self.tables() if t.name == table)
        self.backup()
        self._mutate([f"DELETE FROM {quote(table)}"])
        return rows

    def drop_table(self, table: str) -> None:
        table = self._checked(table)
        self.backup()
        self._mutate([f"DROP TABLE {quote(table)}"])

    def reset(self) -> int:
        """Drop every user table. Returns the number of tables removed."""
        names = self.table_names()
        if not names:
            return 0
        self.backup()
        self._mutate([f"DROP TABLE {quote(n)}" for n in names])
        return len(names)

    # ------------------------------------------------------ import/export --
    def export_bytes(self) -> bytes:
        """A consistent snapshot of the whole database as .db bytes."""
        if not self.exists():
            raise DatabaseError("missing")
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "export.db")
            src = self._read_only()
            dst = sqlite3.connect(target)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
            with open(target, "rb") as fh:
                return fh.read()

    def export_csv(self, table: str) -> bytes:
        table = self._checked(table)
        conn = self._read_only()
        try:
            frame = pd.read_sql_query(f"SELECT * FROM {quote(table)}", conn)
        finally:
            conn.close()
        return frame.to_csv(index=False).encode("utf-8")

    def import_replace(self, data: bytes) -> list:
        """Replace the whole database with ``data`` (validated, atomic swap)."""
        tables = validate_sqlite_bytes(data)
        self.backup()
        folder = os.path.dirname(os.path.abspath(self.path))
        try:
            fd, tmp = tempfile.mkstemp(prefix=".import-", suffix=".db", dir=folder)
            with os.fdopen(fd, "wb") as fh:
                fh.write(data)
            os.replace(tmp, self.path)
        except OSError as exc:
            raise DatabaseError(f"write_failed: {exc}") from exc
        return tables

    def import_update(self, data: bytes) -> list:
        """Copy every table of ``data`` in; same-named tables are replaced and
        other existing tables are kept."""
        tables = validate_sqlite_bytes(data)
        if not tables:
            return []
        self.backup()
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "upload.db")
            with open(src, "wb") as fh:
                fh.write(data)
            try:
                conn = self._write()
                try:
                    conn.execute("ATTACH DATABASE ? AS src", (src,))
                    schema = conn.execute(
                        "SELECT type, name, tbl_name, sql FROM src.sqlite_master "
                        "WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
                    ).fetchall()
                    with conn:
                        for name in tables:
                            conn.execute(f"DROP TABLE IF EXISTS main.{quote(name)}")
                            create = next(s for t, n, _, s in schema
                                          if t == "table" and n == name)
                            conn.execute(create)
                            conn.execute(f"INSERT INTO main.{quote(name)} "
                                         f"SELECT * FROM src.{quote(name)}")
                        for kind, _, _, sql in schema:
                            if kind == "index":
                                conn.execute(sql)
                    conn.execute("DETACH DATABASE src")
                finally:
                    conn.close()
            except sqlite3.Error as exc:
                raise DatabaseError(str(exc)) from exc
        return tables
