"""data_loader.py — Excel ingestion, flexible detection, cleaning and aggregation
for NUCLEUS.

Pure module: no Streamlit, no other project imports. Everything here is unit
testable in isolation.

The loader is tolerant of real-world spreadsheets:
  * column names are matched case-insensitively and via common aliases
  * the timestamp column is auto-detected when not named explicitly
  * both LONG format (one row per reading with a Metric_Name column) and
    WIDE format (one column per metric) are supported and auto-unpivoted
  * units are optional and inferred from metric names when absent
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Optional, Union

import numpy as np
import pandas as pd

REQUIRED_COLUMNS = ["Timestamp", "Device_Name", "Interface", "Metric_Name", "Value", "Unit"]

NO_INTERFACE = "—"  # placeholder when a dataset has no interface dimension

FileLike = Union[str, bytes, "io.BufferedReader", "io.BytesIO"]

# Common aliases for each canonical column (lower-cased, non-alphanumeric stripped).
_ALIASES = {
    "Timestamp": [
        "timestamp", "time", "datetime", "date", "ds", "waktu", "tanggal",
        "collectiontime", "polltime", "recordedat", "capturedat", "ts",
    ],
    "Device_Name": [
        "devicename", "device", "host", "hostname", "server", "node", "nodename",
        "instance", "entity", "resource", "perangkat", "machine", "equipment",
        "deviceid", "sysname",
    ],
    "Interface": [
        "interface", "interfacename", "ifname", "ifdescr", "port", "portname",
        "iface", "antarmuka", "circuit", "link",
    ],
    "Metric_Name": [
        "metricname", "metric", "counter", "kpi", "measurement", "indicator",
        "parameter", "metrik", "sensor", "signal",
    ],
    "Value": [
        "value", "val", "reading", "measure", "amount", "nilai", "y", "data",
        "result", "usage",
    ],
    "Unit": [
        "unit", "units", "uom", "satuan", "measureunit", "unitofmeasure",
    ],
}

# Keyword -> unit inference for wide-format metric columns without a unit column.
_UNIT_HINTS = [
    (r"cpu|mem|memory|util|usage|percent|pct|disk|load|%", "%"),
    (r"bandwidth|throughput|bps|mbps|gbps|traffic|rate", "Mbps"),
    (r"temp|temperature|celsius", "°C"),
    (r"latency|rtt|delay|ms|response", "ms"),
    (r"byte|bytes|storage|capacity|gb|tb", "GB"),
    (r"count|sessions|connections|requests|hits", "count"),
]


def _norm(name: object) -> str:
    """Normalize a column name for matching: lower-case, keep alphanumerics only."""
    return re.sub(r"[^a-z0-9]", "", str(name).strip().lower())


def _infer_unit(metric_name: str) -> str:
    key = str(metric_name).lower()
    for pattern, unit in _UNIT_HINTS:
        if re.search(pattern, key):
            return unit
    return ""


def parse_timestamps(series: pd.Series) -> pd.Series:
    """Parse a column to datetime, tolerating compact numeric date codes.

    Handles plain datetimes as well as integer/string codes like ``YYYYMMDD``
    (e.g. 20250701) and ``YYYYMMDDHH`` / ``YYYYMMDDHHMM`` that pandas would not
    otherwise recognize without an explicit format.
    """
    # Compact numeric date codes (e.g. 20250701) must be checked FIRST, because
    # pd.to_datetime would otherwise read a bare integer as nanoseconds since the
    # epoch (giving a 1970 timestamp) rather than a YYYYMMDD date.
    text = series.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    digits = text.str.fullmatch(r"\d{8,14}")
    if digits.fillna(False).mean() >= 0.6:
        for fmt in ("%Y%m%d", "%Y%m%d%H", "%Y%m%d%H%M", "%Y%m%d%H%M%S"):
            cand = pd.to_datetime(text, format=fmt, errors="coerce")
            if cand.notna().mean() >= 0.6:
                return cand

    # Normal path for real datetimes / parseable strings.
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_excel(file: FileLike, sheet_name: object = 0) -> pd.DataFrame:
    """Read an Excel file (path, bytes or file-like) into a DataFrame.

    Raises ValueError with a human-readable message on failure.
    """
    try:
        # Raw bytes that are neither an .xlsx (zip, "PK") nor a legacy .xls
        # (OLE2) container are treated as a plain-text CSV upload.
        is_csv = isinstance(file, bytes) and not file.startswith(
            (b"PK", b"\xd0\xcf\x11\xe0"))
        if isinstance(file, bytes):
            file = io.BytesIO(file)
        if is_csv:
            df = pd.read_csv(file)
        else:
            df = pd.read_excel(file, engine="openpyxl", sheet_name=sheet_name)
    except Exception as exc:  # noqa: BLE001 - surface a friendly message
        raise ValueError(f"Could not read the Excel file: {exc}") from exc
    if isinstance(df, dict):  # multiple sheets requested -> take the first
        df = next(iter(df.values()))
    # Drop fully-empty columns/rows that spreadsheets often carry.
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all")
    if df.empty:
        raise ValueError("The uploaded Excel file contains no rows.")
    df.columns = [str(c).strip() for c in df.columns]
    return df


# --------------------------------------------------------------------------- #
# Flexible column detection
# --------------------------------------------------------------------------- #
def _match_columns(df: pd.DataFrame) -> dict:
    """Map each canonical column to an actual column name in `df` (or None)."""
    norm_to_actual = {_norm(c): c for c in df.columns}
    mapping: dict[str, Optional[str]] = {}
    for canonical, aliases in _ALIASES.items():
        found = None
        # exact normalized alias match first
        for alias in [canonical] + aliases:
            if _norm(alias) in norm_to_actual:
                found = norm_to_actual[_norm(alias)]
                break
        # then substring containment (e.g. "Device Hostname")
        if found is None:
            for norm_col, actual in norm_to_actual.items():
                if any(_norm(a) and _norm(a) in norm_col for a in aliases):
                    found = actual
                    break
        mapping[canonical] = found
    return mapping


def _detect_timestamp_column(df: pd.DataFrame, mapping: dict) -> Optional[str]:
    """Return the best timestamp column: mapped one, else the most date-like."""
    if mapping.get("Timestamp"):
        return mapping["Timestamp"]
    best, best_score = None, 0.0
    for col in df.columns:
        series = df[col]
        # Plain small-integer/float columns are metric values, not timestamps —
        # unless they look like compact date codes (YYYYMMDD...), which the
        # tolerant parser handles. Skip ordinary small numbers to avoid false
        # positives, but allow 8+ digit codes through.
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.notna().mean() >= 0.9:
            med = numeric.abs().median()
            looks_like_datecode = (
                not pd.isna(med) and 10_000_101 <= med <= 99_991_231_235_959
            )
            if (pd.isna(med) or med < 1_000_000_000) and not looks_like_datecode:
                continue
        parsed = parse_timestamps(series)
        score = parsed.notna().mean()
        if score > best_score:
            best, best_score = col, score
    return best if best_score >= 0.6 else None


def _numeric_columns(df: pd.DataFrame, exclude: set) -> list:
    cols = []
    for c in df.columns:
        if c in exclude:
            continue
        if pd.to_numeric(df[c], errors="coerce").notna().mean() >= 0.6:
            cols.append(c)
    return cols


@dataclass
class DetectionResult:
    """Outcome of analyzing an uploaded spreadsheet before cleaning."""
    layout: str                      # "long" or "wide"
    column_mapping: dict             # canonical -> actual column (or None)
    timestamp_column: Optional[str]
    device_column: Optional[str]
    interface_column: Optional[str] = None
    metric_columns: list = field(default_factory=list)   # wide: metric col names
    devices: list = field(default_factory=list)
    interfaces: list = field(default_factory=list)
    metrics: list = field(default_factory=list)          # final metric names
    warnings: list = field(default_factory=list)
    ok: bool = True
    error: Optional[str] = None


def detect_structure(df: pd.DataFrame) -> DetectionResult:
    """Analyze a raw dataframe and describe how it will be interpreted.

    Never raises for structural issues: returns ``ok=False`` with an ``error``
    instead, so the UI can report it gracefully.
    """
    mapping = _match_columns(df)
    ts_col = _detect_timestamp_column(df, mapping)
    warnings: list[str] = []

    if ts_col is None:
        return DetectionResult(
            layout="unknown", column_mapping=mapping, timestamp_column=None,
            device_column=mapping.get("Device_Name"),
            ok=False,
            error=("Could not find a date/time column. Make sure one column "
                   "contains timestamps."),
        )
    if mapping.get("Timestamp") is None:
        warnings.append(f"Auto-detected '{ts_col}' as the timestamp column.")

    device_col = mapping.get("Device_Name")
    if device_col is None:
        warnings.append(
            "No device column found; all rows will be grouped under device "
            "'All_Devices'."
        )

    interface_col = mapping.get("Interface")

    def _vals(col):
        return sorted(df[col].dropna().astype(str).unique()) if col else []

    devices = _vals(device_col) or ["All_Devices"]
    interfaces = _vals(interface_col) or [NO_INTERFACE]

    has_metric_col = mapping.get("Metric_Name") is not None
    has_value_col = mapping.get("Value") is not None

    if has_metric_col and has_value_col:
        # LONG layout.
        metrics = sorted(df[mapping["Metric_Name"]].dropna().astype(str).unique())
        if mapping.get("Unit") is None:
            warnings.append("No unit column found; units inferred from metric names.")
        if interface_col:
            warnings.append(f"Interface column detected: '{interface_col}'.")
        return DetectionResult(
            layout="long", column_mapping=mapping, timestamp_column=ts_col,
            device_column=device_col, interface_column=interface_col,
            metrics=metrics, devices=devices, interfaces=interfaces,
            warnings=warnings,
        )

    # WIDE layout: each numeric column (other than value/device/interface/ts) is a metric.
    exclude = {ts_col}
    for extra_col in (device_col, interface_col):
        if extra_col:
            exclude.add(extra_col)
    for extra in ("Metric_Name", "Unit"):
        if mapping.get(extra):
            exclude.add(mapping[extra])
    metric_cols = _numeric_columns(df, exclude)

    if not metric_cols:
        return DetectionResult(
            layout="unknown", column_mapping=mapping, timestamp_column=ts_col,
            device_column=device_col, interface_column=interface_col, ok=False,
            error=("Found a timestamp but no numeric metric columns to analyze. "
                   "Expected either a Value column or one or more numeric metric "
                   "columns."),
        )

    msg = (f"Wide format detected: treating {len(metric_cols)} numeric column(s) "
           f"as metrics ({', '.join(metric_cols)}).")
    if interface_col:
        msg += f" Interface column detected: '{interface_col}'."
    warnings.append(msg)
    return DetectionResult(
        layout="wide", column_mapping=mapping, timestamp_column=ts_col,
        device_column=device_col, interface_column=interface_col,
        metric_columns=metric_cols, metrics=sorted(metric_cols),
        devices=devices, interfaces=interfaces, warnings=warnings,
    )


def to_canonical(df: pd.DataFrame, detection: DetectionResult) -> pd.DataFrame:
    """Reshape any supported layout into the canonical long-format columns."""
    if not detection.ok:
        raise ValueError(detection.error or "Unrecognized spreadsheet structure.")

    ts_col = detection.timestamp_column
    device_col = detection.device_column
    iface_col = detection.interface_column

    if detection.layout == "long":
        m = detection.column_mapping
        out = pd.DataFrame({
            "Timestamp": df[ts_col],
            "Device_Name": df[device_col].astype(str) if device_col else "All_Devices",
            "Interface": df[iface_col].astype(str) if iface_col else NO_INTERFACE,
            "Metric_Name": df[m["Metric_Name"]].astype(str),
            "Value": df[m["Value"]],
        })
        if m.get("Unit"):
            out["Unit"] = df[m["Unit"]].astype(str)
        else:
            out["Unit"] = out["Metric_Name"].map(_infer_unit)
        return out[REQUIRED_COLUMNS]

    # wide -> melt
    id_vars = [ts_col] + [c for c in (device_col, iface_col) if c]
    melted = df.melt(
        id_vars=id_vars, value_vars=detection.metric_columns,
        var_name="Metric_Name", value_name="Value",
    )
    melted = melted.rename(columns={ts_col: "Timestamp"})
    if device_col:
        melted = melted.rename(columns={device_col: "Device_Name"})
    else:
        melted["Device_Name"] = "All_Devices"
    if iface_col:
        melted = melted.rename(columns={iface_col: "Interface"})
    else:
        melted["Interface"] = NO_INTERFACE
    melted["Device_Name"] = melted["Device_Name"].astype(str)
    melted["Interface"] = melted["Interface"].astype(str)
    melted["Metric_Name"] = melted["Metric_Name"].astype(str)
    melted["Unit"] = melted["Metric_Name"].map(_infer_unit)
    return melted[REQUIRED_COLUMNS]


# Resample options exposed to the UI, ordered fine -> coarse.
FREQ_OPTIONS = {
    "Minute": "min",
    "Hourly": "h",
    "Daily": "D",
    "Weekly": "W",
    "Monthly": "MS",
}

# Rank for comparing granularities (smaller = finer).
_FREQ_RANK = {"min": 0, "h": 1, "D": 2, "W": 3, "MS": 4}


def granularity_options(df: pd.DataFrame, detection: "DetectionResult") -> list:
    """Return granularity labels appropriate for the data's base interval.

    Only equal-or-coarser granularities than the detected sampling interval are
    offered, because you can aggregate up but not invent finer resolution.
    "Auto" is always offered first.
    """
    base = suggest_frequency(df, detection)
    base_rank = _FREQ_RANK.get(base, 2)
    labels = ["Auto"]
    for label, alias in FREQ_OPTIONS.items():
        if _FREQ_RANK[alias] >= base_rank:
            labels.append(label)
    return labels


def suggest_frequency(df: pd.DataFrame, detection: "DetectionResult") -> str:
    """Infer a sensible resample frequency from the median spacing of timestamps.

    Returns a pandas offset alias ("min", "h", "D", "W"). Falls back to "D".
    """
    ts_col = detection.timestamp_column
    if ts_col is None:
        return "D"
    ts = parse_timestamps(df[ts_col]).dropna().sort_values()
    # Collapse repeated timestamps (e.g. many interfaces share one date) so the
    # spacing reflects the sampling interval, not the row count per period.
    ts = ts.drop_duplicates()
    if len(ts) < 3:
        return "D"
    median_gap = ts.diff().dropna().median()
    if pd.isna(median_gap):
        return "D"
    secs = median_gap.total_seconds()
    span = (ts.max() - ts.min()).total_seconds() or 1.0

    # Choose a granularity giving enough points but not an explosion of them.
    if secs <= 90:                      # ~per-minute data
        chosen = "min"
    elif secs <= 90 * 60:               # ~per-hour data
        chosen = "h"
    elif secs <= 36 * 3600:             # ~per-day data
        chosen = "D"
    else:
        chosen = "W"

    # If the span is short, step finer so we still get >= a handful of points.
    order = ["W", "D", "h", "min"]
    approx_points = {"min": span / 60, "h": span / 3600,
                     "D": span / 86400, "W": span / 604800}
    while approx_points.get(chosen, 0) < 8 and chosen != "min":
        chosen = order[order.index(chosen) + 1]
    return chosen


def analyze_excel(file: FileLike) -> tuple[pd.DataFrame, DetectionResult]:
    """Load an Excel file and analyze its structure in one step.

    Returns the raw dataframe and a DetectionResult describing devices, metrics,
    layout and any warnings — intended to be shown to the user before cleaning.
    """
    raw = load_excel(file)
    return raw, detect_structure(raw)


# --------------------------------------------------------------------------- #
# Cleaning & aggregation
# --------------------------------------------------------------------------- #
def validate_schema(df: pd.DataFrame) -> None:
    """Ensure all required columns exist. Raise ValueError naming the first missing one."""
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(
                f"Missing required column '{col}'. "
                f"Expected columns: {', '.join(REQUIRED_COLUMNS)}."
            )


def clean_and_aggregate(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    """Clean and aggregate readings into a regular long-format time series.

    Accepts either the canonical schema or any layout recognizable by
    ``detect_structure`` (it will be reshaped automatically). Then:
      - parse Timestamp to datetime, drop unparseable rows
      - coerce Value to numeric, drop non-numeric
      - per (Device_Name, Metric_Name): resample to `freq`, mean-aggregate,
        time-interpolate gaps, and fill edges
      - preserve each metric's Unit (inferred when absent)
    """
    # If it is not already canonical, try to reshape it flexibly.
    if not all(c in df.columns for c in REQUIRED_COLUMNS):
        detection = detect_structure(df)
        df = to_canonical(df, detection)

    out = df.copy()

    out["Timestamp"] = parse_timestamps(out["Timestamp"])
    out = out.dropna(subset=["Timestamp"])

    out["Value"] = pd.to_numeric(out["Value"], errors="coerce")
    out = out.dropna(subset=["Value"])

    out["Device_Name"] = out["Device_Name"].astype(str)
    out["Interface"] = out["Interface"].fillna(NO_INTERFACE).astype(str)
    out["Metric_Name"] = out["Metric_Name"].astype(str)
    out["Unit"] = out["Unit"].fillna("").astype(str)

    if out.empty:
        raise ValueError("No valid rows remain after parsing Timestamp and Value.")

    frames: list[pd.DataFrame] = []
    keys = ["Device_Name", "Interface", "Metric_Name"]
    for (device, interface, metric), group in out.groupby(keys):
        unit = group["Unit"].iloc[0]
        series = (
            group.set_index("Timestamp")["Value"]
            .sort_index()
            .resample(freq)
            .mean()
        )
        # Time-interpolate interior gaps, fill the edges so the series is complete.
        series = series.interpolate(method="time").ffill().bfill()
        tidy = series.reset_index()
        tidy.columns = ["Timestamp", "Value"]
        tidy["Device_Name"] = device
        tidy["Interface"] = interface
        tidy["Metric_Name"] = metric
        tidy["Unit"] = unit
        frames.append(tidy)

    cleaned = pd.concat(frames, ignore_index=True)
    return cleaned[REQUIRED_COLUMNS]


def profile_dataframe(cleaned: pd.DataFrame, lang: str = "ID") -> pd.DataFrame:
    """Summarize a cleaned dataset: per device+interface+metric, points, stats.

    Column headers are localized via ``translations.t`` when available; falls
    back to English keys if the translation layer can't be imported.
    """
    try:
        from translations import t as _t
        def label(key, en):
            return _t(key, lang=lang)
    except Exception:  # noqa: BLE001 - keep the module importable standalone
        def label(key, en):
            return en

    cols = {
        "device": label("profile.device", "Device"),
        "interface": label("profile.interface", "Interface"),
        "metric": label("profile.metric", "Metric"),
        "unit": label("profile.unit", "Unit"),
        "points": label("profile.points", "Points"),
        "start": label("profile.start", "Start"),
        "end": label("profile.end", "End"),
        "min": label("profile.min", "Min"),
        "mean": label("profile.mean", "Mean"),
        "max": label("profile.max", "Max"),
    }
    rows = []
    keys = ["Device_Name", "Interface", "Metric_Name"]
    for (device, interface, metric), g in cleaned.groupby(keys):
        rows.append({
            cols["device"]: device,
            cols["interface"]: interface,
            cols["metric"]: metric,
            cols["unit"]: g["Unit"].iloc[0],
            cols["points"]: len(g),
            cols["start"]: g["Timestamp"].min(),
            cols["end"]: g["Timestamp"].max(),
            cols["min"]: round(float(g["Value"].min()), 4),
            cols["mean"]: round(float(g["Value"].mean()), 4),
            cols["max"]: round(float(g["Value"].max()), 4),
        })
    return pd.DataFrame(rows)


def get_series(df: pd.DataFrame, device: str, metric: str,
               interface: str = NO_INTERFACE) -> pd.Series:
    """Extract a time-indexed value Series for one device+interface+metric.

    The returned Series carries the metric unit in ``series.attrs['unit']`` and
    the device/interface in ``series.attrs``.
    """
    mask = (df["Device_Name"] == device) & (df["Metric_Name"] == metric)
    if "Interface" in df.columns and interface is not None:
        mask &= df["Interface"] == interface
    subset = df[mask]
    if subset.empty:
        raise ValueError(
            f"No data for device '{device}', interface '{interface}', "
            f"metric '{metric}'."
        )
    series = (
        subset.set_index("Timestamp")["Value"].sort_index().astype(float)
    )
    # Collapse any residual duplicate timestamps across the selection.
    series = series[~series.index.duplicated(keep="first")]
    series.name = metric
    series.attrs["unit"] = str(subset["Unit"].iloc[0])
    series.attrs["device"] = device
    series.attrs["interface"] = interface
    return series


def interfaces_for(df: pd.DataFrame, devices: list) -> list:
    """List interfaces present for the given device(s)."""
    sub = df[df["Device_Name"].isin(devices)] if devices else df
    return sorted(sub["Interface"].dropna().astype(str).unique())


def metrics_for(df: pd.DataFrame, devices: list, interfaces: list) -> list:
    """List metrics present for the given device(s) and interface(s)."""
    sub = df
    if devices:
        sub = sub[sub["Device_Name"].isin(devices)]
    if interfaces:
        sub = sub[sub["Interface"].isin(interfaces)]
    return sorted(sub["Metric_Name"].dropna().astype(str).unique())


def sample_dataframe(seed: int = 42) -> pd.DataFrame:
    """Generate a synthetic multi-device, multi-metric dataset for the demo."""
    rng = np.random.default_rng(seed)
    days = 90
    timestamps = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days, freq="D")

    specs = [
        ("Host-01", "eth0", "CPU_Usage", "%", 35, 0.25, 6),
        ("Host-01", "eth0", "Memory_Usage", "%", 55, 0.30, 5),
        ("Host-02", "eth1", "CPU_Usage", "%", 48, 0.18, 7),
        ("Host-02", "eth1", "Bandwidth", "Mbps", 300, 1.6, 40),
        ("Switch-A", "Gi0/1", "Bandwidth", "Mbps", 420, 2.4, 55),
    ]

    rows = []
    t = np.arange(days)
    for device, interface, metric, unit, base, slope, noise in specs:
        seasonal = 4 * np.sin(2 * np.pi * t / 7.0)  # weekly seasonality
        trend = base + slope * t
        values = trend + seasonal + rng.normal(0, noise, size=days)
        if unit == "%":
            values = np.clip(values, 0, 100)
        for ts, v in zip(timestamps, values):
            rows.append(
                {
                    "Timestamp": ts,
                    "Device_Name": device,
                    "Interface": interface,
                    "Metric_Name": metric,
                    "Value": round(float(v), 2),
                    "Unit": unit,
                }
            )
    return pd.DataFrame(rows)
