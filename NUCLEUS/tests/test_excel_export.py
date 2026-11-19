"""Excel export: workbook content and the button in the Analytics module."""
import io
from datetime import datetime

import numpy as np
import pandas as pd
import pytest
from openpyxl import load_workbook

import excel_export
import forecasting


def _result(n=60, steps=10, method="Linear Regression", auto=False):
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    series = pd.Series(50 + np.arange(n) % 7, index=idx, dtype=float)
    series.attrs["unit"] = "%"
    res = forecasting.forecast(series, steps, "Auto (Best Fit)" if auto else method,
                               freq="D")
    return series, res


def _item(device="SRV-A", interface="eth0", metric="CPU_Usage", **kw):
    series, res = _result(**kw)
    return {"device": device, "interface": interface, "metric": metric,
            "label": f"{device} · {metric}", "unit": "%", "series": series,
            "result": res, "current": float(series.iloc[-1]),
            "peak": float(res.forecast.max())}


SETTINGS = {"stream": "Network", "devices": ["SRV-A"], "interfaces": ["eth0"],
            "metrics": ["CPU_Usage"], "granularity": "Auto (Daily)",
            "horizon": "10 Day", "steps": 10, "method": "Linear Regression",
            "date_range": ""}


def _load(results, has_interfaces=True, settings=SETTINGS):
    data = excel_export.build_workbook(results, settings, has_interfaces,
                                       generated=datetime(2026, 3, 1, 9, 30))
    return load_workbook(io.BytesIO(data))


def _rows(ws):
    return [[c.value for c in row] for row in ws.iter_rows()]


def test_workbook_has_the_two_sheets():
    wb = _load([_item()])
    assert wb.sheetnames == ["Summary & Metadata", "Combined_Timeline"]


def test_summary_lists_filters_and_per_series_model_with_mape():
    item = _item()
    rows = _rows(_load([item])["Summary & Metadata"])
    flat = {r[0]: r[1] for r in rows if r[0]}
    assert flat["Stream"] == "Network"
    assert flat["Device"] == "SRV-A" and flat["Interface"] == "eth0"
    assert flat["Metric"] == "CPU_Usage"
    assert flat["Forecast horizon"] == "10 Day"
    assert flat["Forecasting method (selected)"] == "Linear Regression"
    header = next(r for r in rows if r[0] == "Series")
    row = rows[rows.index(header) + 1]
    rec = dict(zip(header, row))
    algo, mape, _ = excel_export.model_info(item["result"])
    assert rec["Algorithm"] == algo
    assert rec["MAPE (%)"] == pytest.approx(mape, abs=1e-3)


def test_auto_method_reports_winner_and_ranking():
    item = _item(auto=True, n=120)
    algo, mape, ranking = excel_export.model_info(item["result"])
    assert algo and mape is not None and ranking.count("%") >= 1
    assert algo == item["result"].meta["auto_choice"]


def test_timeline_has_history_then_forecast_for_each_series():
    a, b = _item(metric="CPU_Usage"), _item(device="SRV-B", metric="Memory_Usage")
    ws = _load([a, b])["Combined_Timeline"]
    rows = _rows(ws)
    assert rows[0] == ["Timestamp", "Device", "Interface", "Metric", "Unit",
                       "Data_Type", "Value", "Lower_Bound", "Upper_Bound"]
    body = pd.DataFrame(rows[1:], columns=rows[0])
    for item in (a, b):
        sub = body[body["Device"] == item["device"]]
        assert (sub["Data_Type"] == "Historical").sum() == len(item["result"].history)
        assert (sub["Data_Type"] == "Forecast").sum() == len(item["result"].forecast)
    hist = body[body["Data_Type"] == "Historical"]
    assert hist["Lower_Bound"].isna().all()
    fc = body[body["Data_Type"] == "Forecast"]
    assert fc["Lower_Bound"].notna().all() and fc["Upper_Bound"].notna().all()
    assert body["Timestamp"].map(lambda v: isinstance(v, datetime)).all()


def test_only_the_given_series_are_exported():
    body = pd.DataFrame(_rows(_load([_item()])["Combined_Timeline"])[1:])
    assert set(body[1]) == {"SRV-A"} and set(body[3]) == {"CPU_Usage"}


def test_interface_column_is_dropped_when_data_has_none():
    item = _item(interface="")
    wb = _load([item], has_interfaces=False)
    assert "Interface" not in _rows(wb["Combined_Timeline"])[0]
    flat = {r[0] for r in _rows(wb["Summary & Metadata"])}
    assert "Interface" not in flat


def test_timezone_aware_index_is_exported():
    item = _item()
    res = item["result"]
    res.history.index = res.history.index.tz_localize("UTC")
    res.forecast.index = res.forecast.index.tz_localize("UTC")
    res.lower.index = res.lower.index.tz_localize("UTC")
    res.upper.index = res.upper.index.tz_localize("UTC")
    assert _load([item])["Combined_Timeline"].max_row > 1


def test_file_name():
    assert excel_export.file_name("Network", datetime(2026, 1, 31, 9, 5)) == \
        "nucleus_forecast_network_20260131_0905.xlsx"
