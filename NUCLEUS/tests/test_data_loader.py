import pandas as pd
import pytest

import data_loader as dl


def _raw():
    return pd.DataFrame({
        "Timestamp": ["2026-01-01", "2026-01-01", "2026-01-03", "bad-date"],
        "Device_Name": ["H1", "H1", "H1", "H1"],
        "Metric_Name": ["CPU_Usage", "CPU_Usage", "CPU_Usage", "CPU_Usage"],
        "Value": [10, 20, 40, 99],
        "Unit": ["%", "%", "%", "%"],
    })


def test_validate_schema_missing_column():
    df = _raw().drop(columns=["Unit"])
    with pytest.raises(ValueError, match="Unit"):
        dl.validate_schema(df)


def test_clean_drops_unparseable_timestamp_and_aggregates_duplicates():
    cleaned = dl.clean_and_aggregate(_raw(), freq="D")
    series = dl.get_series(cleaned, "H1", "CPU_Usage")
    # 2026-01-01 duplicates (10, 20) collapse to mean 15.
    assert series.loc["2026-01-01"] == pytest.approx(15.0)
    # Bad date dropped; range is Jan 1..Jan 3 inclusive.
    assert series.index.min() == pd.Timestamp("2026-01-01")
    assert series.index.max() == pd.Timestamp("2026-01-03")


def test_interpolation_fills_gap():
    cleaned = dl.clean_and_aggregate(_raw(), freq="D")
    series = dl.get_series(cleaned, "H1", "CPU_Usage")
    # Jan 2 was missing; interpolated between 15 and 40 -> ~27.5.
    assert series.loc["2026-01-02"] == pytest.approx(27.5, abs=0.1)


def test_get_series_carries_unit():
    cleaned = dl.clean_and_aggregate(_raw(), freq="D")
    series = dl.get_series(cleaned, "H1", "CPU_Usage")
    assert series.attrs["unit"] == "%"


def test_sample_dataframe_shape():
    df = dl.sample_dataframe()
    assert set(dl.REQUIRED_COLUMNS).issubset(df.columns)
    assert df["Device_Name"].nunique() >= 2
    assert len(df) > 0


# --------------------------------------------------------------------------- #
# Flexible detection tests
# --------------------------------------------------------------------------- #
def test_detect_long_with_alias_columns():
    df = pd.DataFrame({
        "time": ["2026-01-01", "2026-01-02"],
        "host": ["H1", "H1"],
        "metric": ["CPU_Usage", "CPU_Usage"],
        "nilai": [10, 20],
    })
    det = dl.detect_structure(df)
    assert det.ok and det.layout == "long"
    assert det.timestamp_column == "time"
    assert det.device_column == "host"
    assert det.metrics == ["CPU_Usage"]
    cleaned = dl.clean_and_aggregate(df)
    assert set(cleaned["Metric_Name"]) == {"CPU_Usage"}
    # Unit inferred from metric name containing "cpu"/"usage".
    assert cleaned["Unit"].iloc[0] == "%"


def test_detect_wide_format_unpivots():
    df = pd.DataFrame({
        "Timestamp": pd.date_range("2026-01-01", periods=4, freq="D"),
        "Device": ["H1"] * 4,
        "CPU_Usage": [10, 20, 30, 40],
        "Bandwidth": [100, 110, 120, 130],
    })
    det = dl.detect_structure(df)
    assert det.ok and det.layout == "wide"
    assert set(det.metrics) == {"CPU_Usage", "Bandwidth"}
    cleaned = dl.clean_and_aggregate(df)
    assert set(cleaned["Metric_Name"]) == {"CPU_Usage", "Bandwidth"}


def test_detect_without_device_column_defaults():
    df = pd.DataFrame({
        "date": pd.date_range("2026-01-01", periods=3, freq="D"),
        "CPU_Usage": [10, 20, 30],
    })
    det = dl.detect_structure(df)
    assert det.ok and det.devices == ["All_Devices"]
    cleaned = dl.clean_and_aggregate(df)
    assert set(cleaned["Device_Name"]) == {"All_Devices"}


def test_detect_fails_without_timestamp():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    det = dl.detect_structure(df)
    assert not det.ok
    assert "date/time" in det.error.lower()


def test_profile_dataframe_summary():
    cleaned = dl.clean_and_aggregate(dl.sample_dataframe())
    prof = dl.profile_dataframe(cleaned, lang="EN")
    assert {"Device", "Metric", "Points", "Min", "Max"}.issubset(prof.columns)
    assert len(prof) >= 1


def test_profile_dataframe_localized_id():
    cleaned = dl.clean_and_aggregate(dl.sample_dataframe())
    prof = dl.profile_dataframe(cleaned, lang="ID")
    # Indonesian headers (Perangkat=Device, Jumlah Titik=Points).
    assert "Perangkat" in prof.columns
    assert "Jumlah Titik" in prof.columns


# --------------------------------------------------------------------------- #
# Frequency suggestion tests
# --------------------------------------------------------------------------- #
def _ts_df(idx):
    return pd.DataFrame({
        "Timestamp": idx, "Device_Name": "H1",
        "Metric_Name": "CPU_Usage", "Value": range(len(idx)), "Unit": "%",
    })


def test_suggest_frequency_hourly():
    df = _ts_df(pd.date_range("2026-01-01", periods=48, freq="h"))
    det = dl.detect_structure(df)
    assert dl.suggest_frequency(df, det) == "h"


def test_suggest_frequency_minute():
    df = _ts_df(pd.date_range("2026-01-01", periods=180, freq="min"))
    det = dl.detect_structure(df)
    assert dl.suggest_frequency(df, det) == "min"


def test_suggest_frequency_daily():
    df = _ts_df(pd.date_range("2026-01-01", periods=90, freq="D"))
    det = dl.detect_structure(df)
    assert dl.suggest_frequency(df, det) == "D"


def test_short_hourly_data_yields_enough_points():
    """Previously daily resampling collapsed short sub-daily data below the
    forecast minimum; auto frequency must now keep enough points."""
    df = _ts_df(pd.date_range("2026-01-01", periods=48, freq="h"))
    det = dl.detect_structure(df)
    freq = dl.suggest_frequency(df, det)
    cleaned = dl.clean_and_aggregate(df, freq=freq)
    series = dl.get_series(cleaned, "H1", "CPU_Usage")
    assert len(series) >= 5


# --------------------------------------------------------------------------- #
# Interface dimension + YYYYMMDD date codes (real uploaded-file format)
# --------------------------------------------------------------------------- #
def _netflow_df():
    dates = pd.date_range("2025-07-01", periods=10, freq="D").strftime("%Y%m%d").astype(int)
    ifaces = ["Gi0/1/0", "Gi0/2/0"]
    rows = []
    for d in dates:
        for i, ifc in enumerate(ifaces):
            rows.append({
                "ds": d, "ip_address": "123.12.123.123", "sys_name": "AAA-AA-AA1",
                "interface_name": ifc, "avg_in_max": 0.05 + i * 0.01,
                "avg_out_max": 0.0001,
            })
    return pd.DataFrame(rows)


def test_parse_yyyymmdd_integer_dates():
    s = pd.Series([20250701, 20250702, 20250703])
    parsed = dl.parse_timestamps(s)
    assert parsed.notna().all()
    assert parsed.iloc[0] == pd.Timestamp("2025-07-01")
    assert parsed.iloc[2] == pd.Timestamp("2025-07-03")


def test_detect_interface_and_metrics_wide():
    det = dl.detect_structure(_netflow_df())
    assert det.ok and det.layout == "wide"
    assert det.timestamp_column == "ds"
    assert det.device_column == "sys_name"
    assert det.interface_column == "interface_name"
    assert det.interfaces == ["Gi0/1/0", "Gi0/2/0"]
    assert set(det.metrics) == {"avg_in_max", "avg_out_max"}


def test_clean_keeps_interface_dimension():
    cleaned = dl.clean_and_aggregate(_netflow_df(), freq="D")
    assert "Interface" in cleaned.columns
    # 2 interfaces x 2 metrics = 4 series.
    combos = cleaned[["Device_Name", "Interface", "Metric_Name"]].drop_duplicates()
    assert len(combos) == 4
    s = dl.get_series(cleaned, "AAA-AA-AA1", "avg_in_max", "Gi0/2/0")
    assert len(s) == 10
    assert s.attrs["interface"] == "Gi0/2/0"


def test_suggest_frequency_daily_for_yyyymmdd():
    df = _netflow_df()
    det = dl.detect_structure(df)
    assert dl.suggest_frequency(df, det) == "D"


def test_granularity_options_not_finer_than_daily():
    df = _netflow_df()
    det = dl.detect_structure(df)
    opts = dl.granularity_options(df, det)
    assert "Minute" not in opts and "Hourly" not in opts
    assert "Daily" in opts and "Auto" in opts


def test_interfaces_and_metrics_helpers():
    cleaned = dl.clean_and_aggregate(_netflow_df(), freq="D")
    assert dl.interfaces_for(cleaned, ["AAA-AA-AA1"]) == ["Gi0/1/0", "Gi0/2/0"]
    mets = dl.metrics_for(cleaned, ["AAA-AA-AA1"], ["Gi0/1/0"])
    assert set(mets) == {"avg_in_max", "avg_out_max"}
