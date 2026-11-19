"""analytics_db.py — dynamic SQLite persistence for NUCLEUS Analytics streams.

Each analytics stream (Compute / Network / Facility) is backed by its own table
in a local SQLite database (``nucleus_database.db``). Tables are created
dynamically from whatever columns the uploaded DataFrame contains — no
hardcoded schema.

Uploads are merged row by row (``AnalyticsDB.upsert``):

* the key is the detected time column (``ds`` / ``timestamp`` / ...) plus any
  identifier columns (device, host, interface, metric, ...);
* a row whose key is new is inserted;
* a row whose key exists with different values is updated;
* a row whose key exists with identical values is left alone (no duplicates).

Dependency-light (pandas + stdlib sqlite3 + data_loader's timestamp parser) and
importable without Streamlit so it can be unit-tested in isolation.
"""
from __future__ import annotations

import io
import os
import re
import sqlite3
import warnings
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

import data_loader

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "nucleus_database.db")

# Canonical stream ids -> SQLite table names.
STREAMS = ("compute", "network", "facility")
_TABLE = {
    "compute": "compute_data",
    "network": "network_data",
    "facility": "facility_data",
}


def table_name(stream: str) -> str:
    """Return the SQLite table name for a stream id (validated)."""
    key = (stream or "").lower()
    if key not in _TABLE:
        raise ValueError(f"unknown_stream:{stream}")
    return _TABLE[key]


@dataclass
class IngestResult:
    """Transparent summary of an upload mapped into SQLite."""
    stream: str
    table: str
    rows: int
    columns: list
    replaced: bool  # True if an existing table was overwritten


@dataclass
class UpsertResult:
    """Row-level summary of merging an upload into a stream table."""
    stream: str
    table: str
    mode: str            # "created" | "upsert" | "dedupe" | "replaced"
    rows_in: int         # rows in the file after basic cleaning
    inserted: int = 0    # new keys added
    updated: int = 0     # existing keys whose values changed
    unchanged: int = 0   # existing keys with identical values (skipped)
    skipped: int = 0     # rows dropped because the timestamp was invalid
    duplicates_in_file: int = 0   # rows merged because they repeated a key
    columns: list = field(default_factory=list)
    key_cols: list = field(default_factory=list)
    time_col: str = ""
    added_columns: list = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Reading uploads
# --------------------------------------------------------------------------- #
def read_upload(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read an uploaded .csv/.xlsx/.xls byte payload into a DataFrame.

    Performs basic cleaning: strips column names, drops fully-empty rows and
    columns, and de-duplicates identical rows. Raises ValueError on failure.
    """
    name = (filename or "").lower()
    buf = io.BytesIO(file_bytes)
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(buf)
        elif name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(buf, engine="openpyxl")
        else:
            # Fall back on content sniffing: try Excel, then CSV.
            try:
                df = pd.read_excel(buf, engine="openpyxl")
            except Exception:  # noqa: BLE001
                buf.seek(0)
                df = pd.read_csv(buf)
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"read_failed:{exc}") from exc

    return clean_dataframe(df)


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Basic data cleaning shared by all streams."""
    if df is None or df.empty:
        raise ValueError("empty_file")
    # Normalize column names (string, trimmed, no stray whitespace).
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    # Drop fully-empty rows/columns that spreadsheets/exports often carry.
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    # Remove exact duplicate rows (basic de-duplication).
    df = df.drop_duplicates().reset_index(drop=True)
    if df.empty:
        raise ValueError("empty_after_clean")
    return df


# --------------------------------------------------------------------------- #
# Key detection + value canonicalization (row-level upsert)
# --------------------------------------------------------------------------- #
_TIME_TOKENS = {"timestamp", "ds", "time", "datetime", "date", "waktu",
                "tanggal", "created", "recorded"}
_ID_TOKENS = {"device", "host", "hostname", "node", "server", "interface",
              "ifname", "port", "metric", "sensor", "rack", "site", "location",
              "asset", "instance", "id", "name"}
# Columns that merely describe a measurement are never part of the key.
_VALUE_TOKENS = {"value", "val", "usage", "avg", "min", "max", "sum", "total",
                 "count", "pct", "percent", "rate", "unit", "units"}
_TIME_FMT = "%Y-%m-%d %H:%M:%S"


def _tokens(col: str) -> set:
    """Lower-case word tokens of a column name (splits _, -, spaces, camelCase)."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(col))
    return {tok for tok in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if tok}


def _parses_as_time(series: pd.Series) -> bool:
    """True when at least 80% of the non-null values parse as timestamps."""
    s = series.dropna()
    if s.empty:
        return False
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            parsed = data_loader.parse_timestamps(s)
        return bool(parsed.notna().mean() >= 0.8)
    except Exception:  # noqa: BLE001
        return False


def detect_keys(df: pd.DataFrame) -> tuple:
    """Return ``(time_col, id_cols)`` used as the upsert key for ``df``.

    The time column is the first column named like a timestamp (``ds``,
    ``timestamp``, ``time``, ``date``, ...) whose values parse as dates; failing
    that, any datetime-typed or date-like text column. Identifier columns are
    those named like a device/host/interface/metric (and not like a measured
    value or unit). ``time_col`` is ``None`` when no time column exists.
    """
    time_col = None
    for col in df.columns:
        if _tokens(col) & _TIME_TOKENS and _parses_as_time(df[col]):
            time_col = col
            break
    if time_col is None:
        for col in df.columns:
            series = df[col]
            if pd.api.types.is_datetime64_any_dtype(series) or (
                    series.dtype == object and _parses_as_time(series)):
                time_col = col
                break
    if time_col is None:
        return None, []
    id_cols = [
        c for c in df.columns
        if c != time_col and _tokens(c) & _ID_TOKENS
        and not _tokens(c) & _VALUE_TOKENS
    ]
    return time_col, id_cols


def _time_strings(series: pd.Series) -> pd.Series:
    """Normalize a time column to ``YYYY-MM-DD HH:MM:SS`` (NaN if unparseable)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = pd.to_datetime(data_loader.parse_timestamps(series),
                                errors="coerce")
    return parsed.dt.strftime(_TIME_FMT)


def _canon(value) -> str:
    """Canonical text form of a cell, so 5, 5.0 and ' 5 ' compare equal."""
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime(_TIME_FMT)
    text = str(value).strip()
    try:
        return f"{float(text):.10g}"
    except ValueError:
        return text


def _py(value):
    """Convert a pandas/numpy scalar to a plain Python value sqlite can bind."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime(_TIME_FMT)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001
            return str(value)
    return value


def _q(name: str) -> str:
    """Quote an SQLite identifier."""
    return '"' + str(name).replace('"', '""') + '"'


def _sql_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series) or pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    return "TEXT"


# --------------------------------------------------------------------------- #
# Dynamic SQLite store
# --------------------------------------------------------------------------- #
class AnalyticsDB:
    """Per-stream SQLite store with dynamic (schema-free) table mapping."""

    def __init__(self, path: str = None):
        # ``NUCLEUS_DB_PATH`` lets deployments and tests point at another file.
        self.path = path or os.environ.get("NUCLEUS_DB_PATH") or _DEFAULT_PATH

    def fingerprint(self):
        """Cheap change marker for the database file (None if it is missing).

        Any write changes the modification time or size, so callers can cache
        a loaded table and reload it only when this value changes.
        """
        try:
            info = os.stat(self.path)
        except OSError:
            return None
        return (info.st_mtime_ns, info.st_size)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def ingest(self, stream: str, df: pd.DataFrame,
               replace: bool = True) -> IngestResult:
        """Write ``df`` into the stream's table, creating it dynamically.

        The table schema follows the DataFrame columns exactly. ``replace``
        (default) overwrites any existing table so re-uploading the same data
        updates it without duplication; pass ``replace=False`` to append.
        """
        table = table_name(stream)
        df = clean_dataframe(df)
        existed = self.has_data(stream)
        with self._connect() as conn:
            df.to_sql(table, conn, if_exists="replace" if replace else "append",
                      index=False)
        return IngestResult(
            stream=stream.lower(), table=table, rows=len(df),
            columns=list(df.columns), replaced=existed and replace,
        )

    def has_data(self, stream: str) -> bool:
        table = table_name(stream)
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            )
            return cur.fetchone() is not None

    def load(self, stream: str) -> pd.DataFrame:
        """Return the stream's stored table as a DataFrame (empty if none)."""
        table = table_name(stream)
        if not self.has_data(stream):
            return pd.DataFrame()
        with self._connect() as conn:
            return pd.read_sql_query(f'SELECT * FROM "{table}"', conn)

    def columns(self, stream: str) -> list:
        """Column names of the stored table (empty list if none)."""
        if not self.has_data(stream):
            return []
        table = table_name(stream)
        with self._connect() as conn:
            cur = conn.execute(f'PRAGMA table_info("{table}")')
            return [row[1] for row in cur.fetchall()]

    def row_count(self, stream: str) -> int:
        if not self.has_data(stream):
            return 0
        table = table_name(stream)
        with self._connect() as conn:
            cur = conn.execute(f'SELECT COUNT(*) FROM "{table}"')
            return int(cur.fetchone()[0])

    def drop(self, stream: str) -> None:
        table = table_name(stream)
        with self._connect() as conn:
            conn.execute(f'DROP TABLE IF EXISTS "{table}"')

    # ---- row-level upsert ------------------------------------------------- #
    @staticmethod
    def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
        cur = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        )
        return cur.fetchone() is not None

    def upsert(self, stream: str, df: pd.DataFrame) -> UpsertResult:
        """Merge ``df`` into the stream table row by row.

        The key is the detected time column plus identifier columns (see
        ``detect_keys``). New keys are inserted, keys whose values changed are
        updated, identical rows are skipped. Without a time column the key is
        the whole row, so only genuinely new rows are added. Columns that the
        table does not have yet are added with ``ALTER TABLE``. If the upload
        does not share the stored table's key columns it is a different dataset
        and the table is replaced.
        """
        table = table_name(stream)
        df = clean_dataframe(df)
        rows_in = len(df)
        time_col, id_cols = detect_keys(df)

        skipped = 0
        if time_col:
            norm = _time_strings(df[time_col])
            valid = norm.notna()
            skipped = int((~valid).sum())
            df = df.loc[valid].copy()
            df[time_col] = norm[valid]
            if df.empty:
                raise ValueError("no_valid_timestamps")
            key_cols = [time_col] + id_cols
        else:
            key_cols = list(df.columns)
        df = df.copy()
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                df[col] = df[col].dt.strftime(_TIME_FMT)
        df_cols = list(df.columns)

        def collapse(keys: list):
            """Collapse repeated keys inside the file; the last one wins."""
            rows: dict = {}
            for row in df.to_dict("records"):
                rows[tuple(_canon(row[c]) for c in keys)] = row
            return rows, len(df) - len(rows)

        def summary(keys: list, dups: int) -> dict:
            return dict(stream=stream.lower(), table=table, rows_in=rows_in,
                        skipped=skipped, duplicates_in_file=dups,
                        columns=df_cols, key_cols=keys,
                        time_col=time_col or "")

        with self._connect() as conn:
            if not self._table_exists(conn, table):
                latest, dups = collapse(key_cols)
                incoming = pd.DataFrame(list(latest.values()), columns=df_cols)
                incoming.to_sql(table, conn, index=False)
                return UpsertResult(mode="created", inserted=len(incoming),
                                    **summary(key_cols, dups))

            existing_cols = [r[1] for r in conn.execute(
                f"PRAGMA table_info({_q(table)})")]
            if time_col:
                # Only identifiers the table already has can be part of the
                # key; a brand-new identifier-like column is added as a plain
                # column instead of invalidating the stored data. The upload is
                # a different dataset when it lacks the time column or shares
                # none of its identifier columns with the table.
                shared_ids = [c for c in id_cols if c in existing_cols]
                compatible = time_col in existing_cols and (
                    not id_cols or bool(shared_ids))
                key_cols = [time_col] + shared_ids
            else:
                compatible = set(existing_cols) == set(df_cols)

            latest, dups = collapse(key_cols)
            incoming = pd.DataFrame(list(latest.values()), columns=df_cols)
            base = summary(key_cols, dups)
            if not compatible:
                incoming.to_sql(table, conn, if_exists="replace", index=False)
                return UpsertResult(mode="replaced", inserted=len(incoming),
                                    **base)

            added = [c for c in df_cols if c not in existing_cols]
            for col in added:
                conn.execute(f"ALTER TABLE {_q(table)} ADD COLUMN {_q(col)} "
                             f"{_sql_type(incoming[col])}")

            stored = pd.read_sql_query(
                f"SELECT rowid AS __rid__, * FROM {_q(table)}", conn)
            keyed = stored.copy()
            if time_col and not keyed.empty:
                norm_old = _time_strings(keyed[time_col])
                keyed[time_col] = norm_old.where(
                    norm_old.notna(), keyed[time_col].astype(object))
            index: dict = {}
            for key_vals, rid, rec in zip(
                    keyed[key_cols].itertuples(index=False, name=None),
                    stored["__rid__"], stored.to_dict("records")):
                index.setdefault(tuple(_canon(v) for v in key_vals),
                                 (int(rid), rec))

            non_key = [c for c in df_cols if c not in key_cols]
            inserts, updates, unchanged = [], [], 0
            for key, row in latest.items():
                hit = index.get(key)
                if hit is None:
                    inserts.append(row)
                    continue
                rid, old = hit
                changes = {c: row[c] for c in non_key
                           if _canon(old.get(c)) != _canon(row[c])}
                if changes:
                    updates.append((rid, changes))
                else:
                    unchanged += 1

            for rid, changes in updates:
                sets = ", ".join(f"{_q(c)} = ?" for c in changes)
                conn.execute(
                    f"UPDATE {_q(table)} SET {sets} WHERE rowid = ?",
                    [*(_py(v) for v in changes.values()), rid])
            if inserts:
                cols_sql = ", ".join(_q(c) for c in df_cols)
                marks = ", ".join("?" for _ in df_cols)
                conn.executemany(
                    f"INSERT INTO {_q(table)} ({cols_sql}) VALUES ({marks})",
                    [[_py(r.get(c)) for c in df_cols] for r in inserts])

        return UpsertResult(
            mode="upsert" if time_col else "dedupe",
            inserted=len(inserts), updated=len(updates), unchanged=unchanged,
            added_columns=added, **base)


def latest_timestamp(df: pd.DataFrame):
    """Most recent value of the detected time column (None if there is none)."""
    time_col, _ = detect_keys(df)
    if not time_col:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        parsed = data_loader.parse_timestamps(df[time_col]).dropna()
    return parsed.max() if len(parsed) else None
