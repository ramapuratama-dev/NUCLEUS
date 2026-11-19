"""excel_export.py — build the Analytics forecast workbook (.xlsx) in memory.

The workbook contains only what the dashboard is showing: the selected series
(history + forecast) and the settings that produced them. Nothing is written to
disk; ``pandas.ExcelWriter`` (openpyxl) writes into an ``io.BytesIO``.

Sheets:
* ``Summary & Metadata`` - the active filters, then one row per series with the
  selected algorithm and its backtest MAPE (%).
* ``Combined_Timeline``  - history and forecast rows in one table, one row per
  timestamp and series, tagged by ``Data_Type``.

The module never imports Streamlit, so it is unit-testable in isolation.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional, Sequence

import pandas as pd

SUMMARY_SHEET = "Summary & Metadata"
TIMELINE_SHEET = "Combined_Timeline"
HISTORICAL = "Historical"
FORECAST = "Forecast"
NO_INTERFACE = "-"

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
MIME = _XLSX_MIME


def file_name(stream: str, now: Optional[datetime] = None) -> str:
    """``nucleus_forecast_network_20260131_0930.xlsx``."""
    now = now or datetime.now()
    return f"nucleus_forecast_{stream.lower()}_{now:%Y%m%d_%H%M}.xlsx"


def model_info(result) -> tuple:
    """(algorithm, MAPE %, ranking text) for a ForecastResult.

    Auto (Best Fit) reports the winning model and its score; a manually chosen
    model reports its own backtest MAPE. MAPE is None when it was not scored.
    """
    meta = getattr(result, "meta", None) or {}
    scores = meta.get("auto_scores")
    if scores:
        best = meta.get("auto_choice") or min(scores, key=scores.get)
        ranking = ", ".join(f"{m}: {s:.2f}%"
                            for m, s in sorted(scores.items(), key=lambda kv: kv[1]))
        return best, float(scores[best]), ranking
    mape = meta.get("backtest_mape")
    algo = meta.get("model_used") or result.method
    return algo, (float(mape) if mape is not None else None), ""


def _naive(index) -> pd.DatetimeIndex:
    """Excel cannot store timezone-aware datetimes."""
    idx = pd.DatetimeIndex(index)
    return idx.tz_localize(None) if idx.tz is not None else idx


def timeline_frame(results: Sequence[dict], has_interfaces: bool) -> pd.DataFrame:
    """History and forecast of every shown series as one long table."""
    frames = []
    for r in results:
        res = r["result"]
        interface = r.get("interface") or NO_INTERFACE
        base = {"Device": r["device"]}
        if has_interfaces:
            base["Interface"] = interface
        base.update({"Metric": r["metric"], "Unit": r.get("unit") or ""})
        hist = pd.DataFrame({"Timestamp": _naive(res.history.index),
                             **base,
                             "Data_Type": HISTORICAL,
                             "Value": res.history.values,
                             "Lower_Bound": float("nan"), "Upper_Bound": float("nan")})
        fc = pd.DataFrame({"Timestamp": _naive(res.forecast.index),
                           **base,
                           "Data_Type": FORECAST,
                           "Value": res.forecast.values,
                           "Lower_Bound": res.lower.reindex(res.forecast.index).values,
                           "Upper_Bound": res.upper.reindex(res.forecast.index).values})
        frames.append(pd.concat([hist, fc], ignore_index=True))
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    for col in ("Value", "Lower_Bound", "Upper_Bound"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def summary_frames(results: Sequence[dict], settings: dict,
                   has_interfaces: bool, generated: datetime) -> tuple:
    """(filters table, per-series table) for the Summary sheet."""
    def join(values) -> str:
        return ", ".join(str(v) for v in values) if values else "-"

    rows = [
        ("Generated at", f"{generated:%Y-%m-%d %H:%M:%S}"),
        ("Stream", settings.get("stream", "")),
        ("Device", join(settings.get("devices"))),
    ]
    if has_interfaces:
        rows.append(("Interface", join(settings.get("interfaces"))))
    rows += [
        ("Metric", join(settings.get("metrics"))),
        ("Time granularity", settings.get("granularity", "")),
        ("Forecast horizon", settings.get("horizon", "")),
        ("Forecast steps", settings.get("steps", "")),
        ("Forecasting method (selected)", settings.get("method", "")),
        ("Series exported", len(results)),
    ]
    if settings.get("date_range"):
        rows.insert(-1, ("Date range", settings["date_range"]))
    filters = pd.DataFrame(rows, columns=["Setting", "Value"])

    series_rows = []
    for r in results:
        algo, mape, ranking = model_info(r["result"])
        row = {"Series": r["label"], "Device": r["device"]}
        if has_interfaces:
            row["Interface"] = r.get("interface") or NO_INTERFACE
        row.update({
            "Metric": r["metric"], "Unit": r.get("unit") or "",
            "Algorithm": algo,
            "MAPE (%)": round(mape, 4) if mape is not None else None,
            "Model ranking (MAPE %)": ranking,
            "Current": round(float(r["current"]), 4),
            "Forecast peak": round(float(r["peak"]), 4),
            "History points": len(r["result"].history),
            "Forecast points": len(r["result"].forecast),
        })
        series_rows.append(row)
    return filters, pd.DataFrame(series_rows)


def build_workbook(results: Sequence[dict], settings: dict, has_interfaces: bool,
                   generated: Optional[datetime] = None) -> bytes:
    """Render the workbook and return its bytes (nothing touches the disk)."""
    generated = generated or datetime.now()
    filters, per_series = summary_frames(results, settings, has_interfaces,
                                         generated)
    timeline = timeline_frame(results, has_interfaces)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl", datetime_format="yyyy-mm-dd hh:mm:ss") as xw:
        filters.to_excel(xw, sheet_name=SUMMARY_SHEET, index=False, startrow=0)
        per_series.to_excel(xw, sheet_name=SUMMARY_SHEET, index=False,
                            startrow=len(filters) + 3)
        timeline.to_excel(xw, sheet_name=TIMELINE_SHEET, index=False)
        _style(xw.book[SUMMARY_SHEET], header_rows=(1, len(filters) + 4),
               freeze=None)
        _style(xw.book[TIMELINE_SHEET], header_rows=(1,), freeze="A2",
               autofilter=True)
        ws = xw.book[SUMMARY_SHEET]
        ws.cell(row=len(filters) + 3, column=1,
                value="Selected algorithm per series").font = _bold()
    return buf.getvalue()


def _bold():
    from openpyxl.styles import Font
    return Font(bold=True)


def _style(ws, header_rows: tuple, freeze: Optional[str],
           autofilter: bool = False) -> None:
    """Bold headers, readable column widths, optional freeze pane and filter."""
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    fill = PatternFill("solid", fgColor="DDE7F5")
    for row in header_rows:
        for cell in ws[row]:
            if cell.value is not None:
                cell.font = Font(bold=True)
                cell.fill = fill
                cell.alignment = Alignment(vertical="center")
    widths: dict = {}
    for row in ws.iter_rows():
        for cell in row:
            if cell.value is None:
                continue
            length = len(str(cell.value))
            widths[cell.column] = max(widths.get(cell.column, 0), length)
    for col, length in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = min(max(length + 2, 10), 60)
    if freeze:
        ws.freeze_panes = freeze
    if autofilter and ws.max_row > 1:
        ws.auto_filter.ref = ws.dimensions
