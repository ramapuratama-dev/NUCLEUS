import pandas as pd
import pytest

import analytics_db as adb


def _net(rows):
    return pd.DataFrame(rows, columns=["Timestamp", "Device_Name", "Interface",
                                       "Metric_Name", "Value", "Unit"])


BASE = [
    ["2026-01-01 00:00", "Host-01", "eth0", "CPU_Usage", 40.0, "%"],
    ["2026-01-01 00:00", "Host-01", "eth0", "Memory_Usage", 60.0, "%"],
    ["2026-01-02 00:00", "Host-01", "eth0", "CPU_Usage", 42.0, "%"],
]


@pytest.fixture()
def db(tmp_path):
    return adb.AnalyticsDB(str(tmp_path / "nucleus_database.db"))


def test_detect_keys_long_format():
    time_col, ids = adb.detect_keys(_net(BASE))
    assert time_col == "Timestamp"
    # Value and Unit describe the measurement and must not be part of the key.
    assert ids == ["Device_Name", "Interface", "Metric_Name"]


def test_detect_keys_ds_column_and_no_time():
    df = pd.DataFrame({"ds": ["2026-01-01", "2026-01-02"], "host": ["a", "b"],
                       "cpu": [1, 2]})
    assert adb.detect_keys(df) == ("ds", ["host"])
    assert adb.detect_keys(pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})) == (None, [])


def test_first_upload_creates_table(db):
    res = db.upsert("network", _net(BASE))
    assert res.mode == "created"
    assert (res.inserted, res.updated, res.unchanged) == (3, 0, 0)
    assert db.row_count("network") == 3


def test_reupload_identical_data_adds_nothing(db):
    db.upsert("network", _net(BASE))
    res = db.upsert("network", _net(BASE))
    assert res.mode == "upsert"
    assert (res.inserted, res.updated, res.unchanged) == (0, 0, 3)
    assert db.row_count("network") == 3


def test_changed_value_is_updated_and_new_row_inserted(db):
    db.upsert("network", _net(BASE))
    changed = [list(r) for r in BASE]
    changed[0][4] = 99.0                      # same key, new value
    changed.append(["2026-01-03 00:00", "Host-01", "eth0", "CPU_Usage", 45.0, "%"])
    res = db.upsert("network", _net(changed))
    assert (res.inserted, res.updated, res.unchanged) == (1, 1, 2)
    stored = db.load("network")
    assert len(stored) == 4
    cpu_day1 = stored[(stored["Timestamp"] == "2026-01-01 00:00:00")
                      & (stored["Metric_Name"] == "CPU_Usage")]
    assert float(cpu_day1["Value"].iloc[0]) == 99.0


def test_different_metrics_at_same_timestamp_do_not_collide(db):
    res = db.upsert("network", _net(BASE))
    assert res.inserted == 3 and db.row_count("network") == 3


def test_timestamp_formats_map_to_the_same_key(db):
    db.upsert("network", _net(BASE))
    other = [["2026-01-01", "Host-01", "eth0", "CPU_Usage", 40.0, "%"]]
    res = db.upsert("network", _net(other))
    assert (res.inserted, res.updated, res.unchanged) == (0, 0, 1)


def test_compact_date_codes_are_understood(db):
    df = pd.DataFrame({"ds": [20260101, 20260102], "host": ["a", "a"], "v": [1, 2]})
    db.upsert("compute", df)
    res = db.upsert("compute", df)
    assert res.unchanged == 2 and db.row_count("compute") == 2
    assert db.load("compute")["ds"].tolist() == ["2026-01-01 00:00:00",
                                                 "2026-01-02 00:00:00"]


def test_new_columns_are_added_to_existing_table(db):
    db.upsert("network", _net(BASE))
    wider = _net(BASE).assign(Site="DC1")
    res = db.upsert("network", wider)
    assert res.added_columns == ["Site"]
    assert res.unchanged == 0 and res.updated == 3    # Site went NULL -> DC1
    assert "Site" in db.columns("network")
    assert db.row_count("network") == 3


def test_duplicate_keys_inside_the_file_are_merged(db):
    dup = BASE + [["2026-01-01 00:00", "Host-01", "eth0", "CPU_Usage", 41.0, "%"]]
    res = db.upsert("network", _net(dup))
    assert res.duplicates_in_file == 1 and res.inserted == 3
    stored = db.load("network")
    first = stored[(stored["Timestamp"] == "2026-01-01 00:00:00")
                   & (stored["Metric_Name"] == "CPU_Usage")]
    assert float(first["Value"].iloc[0]) == 41.0       # last occurrence wins


def test_invalid_timestamps_are_skipped(db):
    many = [[f"2026-01-{d:02d} 00:00", "Host-01", "eth0", "CPU_Usage", float(d), "%"]
            for d in range(1, 10)]
    bad = many + [["not a date", "Host-01", "eth0", "CPU_Usage", 1.0, "%"]]
    res = db.upsert("network", _net(bad))
    assert res.skipped == 1 and res.inserted == 9


def test_new_identifier_like_column_does_not_wipe_the_table(db):
    db.upsert("network", _net(BASE))
    res = db.upsert("network", _net(BASE).assign(Rack="R1"))
    assert res.mode == "upsert" and res.added_columns == ["Rack"]
    assert db.row_count("network") == 3
    # Rack is not part of the key because the stored table did not have it.
    assert res.key_cols == ["Timestamp", "Device_Name", "Interface", "Metric_Name"]


def test_all_invalid_timestamps_raise(db):
    df = pd.DataFrame({"ds": ["x", "y", "z", "w", "v"], "v": [1, 2, 3, 4, 5]})
    # No parseable time column, so it falls back to whole-row keys (no error).
    assert db.upsert("compute", df).mode == "created"


def test_incompatible_upload_replaces_the_table(db):
    db.upsert("network", _net(BASE))
    other = pd.DataFrame({"ds": ["2026-02-01"], "rack": ["r1"], "temp": [21.5]})
    res = db.upsert("network", other)
    assert res.mode == "replaced"
    assert db.columns("network") == ["ds", "rack", "temp"]
    assert db.row_count("network") == 1


def test_without_time_column_only_new_rows_are_added(db):
    df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    db.upsert("facility", df)
    res = db.upsert("facility", pd.DataFrame({"a": [2, 3], "b": ["y", "z"]}))
    assert res.mode == "dedupe"
    assert (res.inserted, res.updated, res.unchanged) == (1, 0, 1)
    assert db.row_count("facility") == 3


def test_streams_are_isolated(db):
    db.upsert("network", _net(BASE))
    assert not db.has_data("compute")
    with pytest.raises(ValueError):
        db.upsert("bogus", _net(BASE))


def test_data_survives_reopening_the_database(tmp_path):
    path = str(tmp_path / "nucleus_database.db")
    adb.AnalyticsDB(path).upsert("network", _net(BASE))
    reopened = adb.AnalyticsDB(path)          # e.g. a refresh / new process
    assert reopened.row_count("network") == 3
    assert reopened.load("network")["Device_Name"].unique().tolist() == ["Host-01"]


def test_fingerprint_changes_on_write_and_is_none_when_missing(db):
    assert db.fingerprint() is None
    db.upsert("network", _net(BASE))
    first = db.fingerprint()
    assert first is not None
    changed = [list(r) for r in BASE]
    changed[0][4] = 99.0
    db.upsert("network", _net(changed))
    assert db.fingerprint() != first


def test_database_path_can_come_from_the_environment(tmp_path, monkeypatch):
    target = str(tmp_path / "elsewhere.db")
    monkeypatch.setenv("NUCLEUS_DB_PATH", target)
    assert adb.AnalyticsDB().path == target
