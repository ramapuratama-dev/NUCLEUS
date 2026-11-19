"""Database module: admin library (database_admin) and the admin-only page."""
import io
import os
import sqlite3

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

import database_admin as dbm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")


def _make_db(path, tables=None):
    tables = tables or {"network_data": pd.DataFrame({
        "ds": ["2026-01-01", "2026-01-02", "2026-01-03"],
        "sys_name": ["h1", "h1", "h2"], "avg_cpu_max": [1.0, 2.0, 3.0]})}
    conn = sqlite3.connect(path)
    for name, frame in tables.items():
        frame.to_sql(name, conn, index=False)
    conn.commit()
    conn.close()
    return path


def _bytes(tmp_path, name, tables):
    path = _make_db(str(tmp_path / name), tables)
    with open(path, "rb") as fh:
        return fh.read()


@pytest.fixture()
def admin(tmp_path):
    return dbm.DatabaseAdmin(_make_db(str(tmp_path / "nucleus.db")))


# ------------------------------------------------------------- inspect -- #
def test_tables_report_rows_and_schema(admin):
    (info,) = admin.tables()
    assert info.name == "network_data" and info.rows == 3
    assert [(c.name, c.type) for c in info.columns] == [
        ("ds", "TEXT"), ("sys_name", "TEXT"), ("avg_cpu_max", "REAL")]
    assert admin.file_size() > 0


def test_missing_database_has_no_tables(tmp_path):
    assert dbm.DatabaseAdmin(str(tmp_path / "none.db")).tables() == []


def test_format_bytes():
    assert dbm.format_bytes(512) == "512 B"
    assert dbm.format_bytes(2_768_896) == "2.6 MB"
    assert dbm.format_bytes(None) == "-"


# --------------------------------------------------------------- query -- #
def test_select_returns_rows(admin):
    res = admin.run_query("SELECT sys_name, SUM(avg_cpu_max) AS s FROM network_data "
                          "GROUP BY sys_name ORDER BY sys_name")
    assert res.frame.to_dict("list") == {"sys_name": ["h1", "h2"], "s": [3.0, 3.0]}
    assert not res.truncated


def test_results_are_capped(admin):
    res = admin.run_query("WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 "
                          "FROM n WHERE x < 50) SELECT x FROM n", max_rows=10)
    assert len(res.frame) == 10 and res.truncated


@pytest.mark.parametrize("sql", [
    "DELETE FROM network_data",
    "DROP TABLE network_data",
    "INSERT INTO network_data VALUES ('x','y',1)",
])
def test_console_cannot_write(admin, sql):
    with pytest.raises(dbm.DatabaseError, match="readonly"):
        admin.run_query(sql)
    assert admin.tables()[0].rows == 3


@pytest.mark.parametrize("sql", ["SELEC nonsense", "SELECT * FROM nope", "",
                                 "SELECT 1; SELECT 2"])
def test_bad_sql_raises_a_clean_error(admin, sql):
    with pytest.raises(dbm.DatabaseError):
        admin.run_query(sql)


def test_long_query_times_out(admin):
    with pytest.raises(dbm.DatabaseError, match="timeout"):
        admin.run_query("WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 "
                        "FROM n) SELECT count(*) FROM n", timeout=0.2)


# -------------------------------------------------------------- mutate -- #
def test_clear_keeps_schema_and_makes_a_backup(admin):
    assert admin.clear_table("network_data") == 3
    (info,) = admin.tables()
    assert info.rows == 0 and len(info.columns) == 3
    assert len(admin.backups()) == 1


def test_drop_and_reset(admin, tmp_path):
    admin.import_update(_bytes(tmp_path, "extra.db",
                               {"compute_data": pd.DataFrame({"a": [1]})}))
    admin.drop_table("compute_data")
    assert admin.table_names() == ["network_data"]
    assert admin.reset() == 1
    assert admin.tables() == []


def test_unknown_table_is_rejected(admin):
    for action in (admin.clear_table, admin.drop_table, admin.export_csv,
                   admin.preview):
        with pytest.raises(dbm.DatabaseError, match="unknown_table"):
            action('network_data"; DROP TABLE network_data; --')
    assert admin.table_names() == ["network_data"]


def test_only_the_newest_backups_are_kept(admin):
    for _ in range(dbm.KEEP_BACKUPS + 3):
        admin.backup()
    assert len(admin.backups()) == dbm.KEEP_BACKUPS


# -------------------------------------------------------- import/export -- #
def test_export_round_trip(admin, tmp_path):
    data = admin.export_bytes()
    assert data.startswith(dbm.SQLITE_HEADER)
    assert dbm.validate_sqlite_bytes(data) == ["network_data"]
    csv = pd.read_csv(io.BytesIO(admin.export_csv("network_data")))
    assert list(csv.columns) == ["ds", "sys_name", "avg_cpu_max"] and len(csv) == 3


def test_invalid_upload_is_rejected_before_any_change(admin):
    for junk in (b"", b"hello world", dbm.SQLITE_HEADER + b"\x00" * 50):
        with pytest.raises(dbm.DatabaseError):
            admin.import_replace(junk)
    assert admin.tables()[0].rows == 3 and admin.backups() == []


def test_import_replace_swaps_the_whole_file(admin, tmp_path):
    new = _bytes(tmp_path, "new.db", {"facility_data": pd.DataFrame({"t": [1, 2]})})
    assert admin.import_replace(new) == ["facility_data"]
    assert admin.table_names() == ["facility_data"]
    assert len(admin.backups()) == 1


def test_import_update_replaces_same_name_and_keeps_others(admin, tmp_path):
    new = _bytes(tmp_path, "upd.db", {
        "network_data": pd.DataFrame({"ds": ["2027-01-01"], "v": [9.0]}),
        "compute_data": pd.DataFrame({"a": [1, 2]})})
    admin.import_update(_bytes(tmp_path, "keep.db",
                               {"facility_data": pd.DataFrame({"t": [1]})}))
    assert sorted(admin.import_update(new)) == ["compute_data", "network_data"]
    rows = {x.name: x.rows for x in admin.tables()}
    assert rows == {"compute_data": 2, "facility_data": 1, "network_data": 1}


# ---------------------------------------------------------------- page -- #
@pytest.fixture()
def page_env(tmp_path, monkeypatch):
    path = _make_db(str(tmp_path / "nucleus_database.db"))
    monkeypatch.setenv("NUCLEUS_DB_PATH", path)
    return path


def _open(role="administrator"):
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["authenticated"] = True
    at.session_state["username"] = "tester"
    at.session_state["user_role"] = role
    at.query_params["mode"] = "database"
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.mark.parametrize("role", ["engineer", "viewer"])
def test_non_admins_are_denied(page_env, role):
    at = _open(role)
    assert any("do not have permission" in e.value for e in at.error)
    assert not at.tabs


def test_admin_sees_kpis_and_four_tabs(page_env):
    at = _open()
    assert [tab.label for tab in at.tabs] == [
        "Table Browser", "Query Console", "Data Management", "Import & Export"]
    kpis = {m.label: m.value for m in at.metric}
    assert kpis["Tables"] == "1" and kpis["Total rows"] == "3"


def test_console_runs_a_query_and_shows_errors(page_env):
    at = _open()
    at.text_area(key="db_sql").set_value("SELECT COUNT(*) AS n FROM network_data")
    at.button(key="db_run").click().run()
    assert not at.exception
    frames = [d.value for d in at.dataframe]
    assert any(list(f.columns) == ["n"] and f.iloc[0, 0] == 3 for f in frames)
    at.text_area(key="db_sql").set_value("DELETE FROM network_data")
    at.button(key="db_run").click().run()
    assert any("readonly" in e.value for e in at.error)


def test_delete_needs_both_confirmations(page_env):
    at = _open()
    assert at.button(key="db_manage_go").disabled
    at.checkbox(key="db_manage_ack").check().run()
    assert at.button(key="db_manage_go").disabled          # name not typed yet
    at.text_input(key="db_manage_typed").input("wrong").run()
    assert at.button(key="db_manage_go").disabled
    at.text_input(key="db_manage_typed").input("network_data").run()
    assert not at.button(key="db_manage_go").disabled
    at.button(key="db_manage_go").click().run()
    assert not at.exception, at.exception
    assert any("Deleted 3 rows" in s.value for s in at.success)
    assert dbm.DatabaseAdmin(page_env).tables()[0].rows == 0


def test_reset_needs_the_word_reset(page_env):
    at = _open()
    at.checkbox(key="db_reset_ack").check().run()
    at.text_input(key="db_reset_typed").input("reset").run()
    assert at.button(key="db_reset_go").disabled           # case-sensitive
    at.text_input(key="db_reset_typed").input("RESET").run()
    at.button(key="db_reset_go").click().run()
    assert dbm.DatabaseAdmin(page_env).tables() == []
