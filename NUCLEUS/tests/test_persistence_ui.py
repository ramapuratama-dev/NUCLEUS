"""A fresh browser session must be filled from the SQLite database.

Each ``AppTest`` run is a brand-new session (like a refresh or a new tab), so
anything it shows has to come from the database file, not from session state.
"""
import json
import os

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import analytics_db
import settings_store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")
SAMPLE_DEVICES = {"Host-01", "Host-02", "Switch-A"}


def _network_rows():
    rows = []
    for day in pd.date_range("2026-01-01", periods=40, freq="D"):
        for device in ("SRV-A", "SRV-B"):
            for metric in ("CPU_Usage", "Memory_Usage"):
                rows.append([day.strftime("%Y-%m-%d"), device, "eth0", metric,
                             50.0 + day.day % 7, "%"])
    return pd.DataFrame(rows, columns=["Timestamp", "Device_Name", "Interface",
                                       "Metric_Name", "Value", "Unit"])


def _write_settings(path, data_source="sample"):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"forecasting": {"default_model": "Linear Regression"},
                   "data": {"source": data_source}}, fh)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """Isolated database + settings, with a fast default forecasting model."""
    db_path = str(tmp_path / "nucleus_database.db")
    monkeypatch.setenv("NUCLEUS_DB_PATH", db_path)
    settings_path = str(tmp_path / "settings.json")
    _write_settings(settings_path)
    monkeypatch.setattr(settings_store.SettingsStore.__init__, "__defaults__",
                        (settings_path,))
    # ``_settings()`` is a process-wide cache_resource; drop it so every test
    # builds its own store from its own settings file.
    st.cache_resource.clear()
    return analytics_db.AnalyticsDB(db_path)


def _open(role="administrator", stream=None, lang=None):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["authenticated"] = True
    at.session_state["username"] = "tester"
    at.session_state["user_role"] = role
    if stream:
        at.session_state["stream_select"] = stream
    if lang:
        at.session_state["lang_select"] = lang
    at.query_params["mode"] = "analytics"
    at.run()
    assert not at.exception, at.exception
    return at


@pytest.fixture()
def interactive(env, monkeypatch):
    """Let a test change widgets and rerun.

    AppTest cannot serialize ``st.segmented_control`` (it breaks every rerun
    after the first), so the stream selector is replaced by a stub that simply
    returns the Network stream. Everything else is the real app.
    """
    monkeypatch.setattr(st, "segmented_control",
                        lambda label, options, **kw: options[1])
    return env


def _pick(at, label, values):
    """Choose ``values`` in the sidebar multiselect called ``label``."""
    _widget(at.sidebar.multiselect, label).set_value(values).run()
    assert not at.exception, at.exception


def _widget(items, label):
    return next(w for w in items if w.label == label)


def _captions(at):
    return " | ".join(c.value for c in at.caption)


def _success(at):
    return " | ".join(s.value for s in at.success)


def _infos(at):
    return " | ".join(i.value for i in at.info)


def test_refresh_loads_saved_data_and_fills_the_filters(env):
    env.upsert("network", _network_rows())
    at = _open()
    assert set(_widget(at.sidebar.multiselect, "Device").options) == {"SRV-A", "SRV-B"}
    assert set(_widget(at.sidebar.multiselect, "Metric").options) == {
        "CPU_Usage", "Memory_Usage"}


def test_database_status_uses_corporate_wording_with_latest_date(env):
    env.upsert("network", _network_rows())
    caps = _captions(_open())
    assert ("Database synchronization complete. A total of 160 historical "
            "records up to 9 February 2026 are now stored in the network_data "
            "table and ready for automated forecasting.") in caps


def test_database_status_is_localized_in_indonesian(env):
    env.upsert("network", _network_rows())
    caps = _captions(_open(lang="ID"))
    assert "Sinkronisasi database selesai. Sebanyak 160 catatan historis " \
           "hingga 9 Februari 2026" in caps


def test_status_does_not_promise_forecasting_for_compute(env):
    env.upsert("compute", pd.DataFrame({"ds": ["2026-01-01", "2026-01-02"],
                                        "host": ["a", "b"], "cpu": [1, 2]}))
    caps = _captions(_open(stream="🖥️ Compute Stream"))
    assert ("A total of 2 historical records up to 2 January 2026 are now "
            "stored in the compute_data table.") in caps
    assert "automated forecasting" not in caps


def test_executive_telemetry_boxes(env):
    env.upsert("network", _network_rows())
    at = _open()
    assert ("NUCLEUS analysis finalized. Evaluated 2 devices across 2 core "
            "metrics.") in _success(at)
    assert ("Successfully detected 2 metrics: CPU_Usage and Memory_Usage."
            in _infos(at))


def test_executive_telemetry_boxes_in_indonesian(env):
    env.upsert("network", _network_rows())
    at = _open(lang="ID")
    assert "Analisis NUCLEUS telah selesai. Mengevaluasi 2 perangkat pada " \
           "2 metrik utama." in _success(at)
    assert "Berhasil mendeteksi 2 metrik: CPU_Usage dan Memory_Usage." in _infos(at)


def test_old_wide_format_note_is_replaced(env):
    env.upsert("network", pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=30, freq="D").strftime("%Y-%m-%d"),
        "sys_name": ["h1"] * 30,
        "avg_cpu_max": [40.0 + i % 5 for i in range(30)],
        "avg_memory_max": [55.0 + i % 4 for i in range(30)],
    }))
    infos = _infos(_open())
    assert "Successfully detected 2 metrics: avg_cpu_max and avg_memory_max." in infos
    assert "Wide format detected" not in infos


def test_use_sample_toggle_and_engine_note_are_gone(env):
    env.upsert("network", _network_rows())
    at = _open()
    assert not [t for t in at.sidebar.toggle]
    assert "capacity-forecasting engine" not in _captions(at)


def _choose(at, device="SRV-A", interface="eth0", metric="CPU_Usage"):
    """Pick filters in dependency order (each choice changes the next options)."""
    if device:
        _pick(at, "Device", [device])
    if interface:
        _pick(at, "Interface", [interface])
    if metric:
        _pick(at, "Metric", [metric])


def test_filters_start_empty_and_nothing_is_forecast(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    for label in ("Device", "Interface", "Metric"):
        assert _widget(at.sidebar.multiselect, label).value == [], label
    assert "Select at least one device and one metric to run a forecast" in _infos(at)
    # No forecast output yet, and no model work was done.
    assert not at.metric
    assert not at.get("plotly_chart")
    assert "Model Evaluation Complete" not in _infos(at)
    assert not [e for e in at.success if "Model & Trend Analysis" in e.value]
    # The rest of the sidebar is still usable.
    assert _widget(at.sidebar.selectbox, "Forecasting method")
    assert _widget(at.sidebar.number_input, "Amount").value == 30


def test_filters_also_start_empty_on_demonstration_data(interactive):
    at = _open()                       # empty database -> demonstration data
    assert set(_widget(at.sidebar.multiselect, "Device").options) == SAMPLE_DEVICES
    for label in ("Device", "Interface", "Metric"):
        assert _widget(at.sidebar.multiselect, label).value == [], label
    assert "Select at least one device and one metric" in _infos(at)


def test_a_device_alone_is_not_enough(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _pick(at, "Device", ["SRV-A"])
    assert "Select at least one device and one metric" in _infos(at)
    assert not at.metric


def test_a_metric_alone_is_not_enough(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _pick(at, "Metric", ["CPU_Usage"])
    assert "Select at least one device and one metric" in _infos(at)
    assert not at.metric


def test_interface_is_requested_when_the_data_has_interfaces(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _pick(at, "Device", ["SRV-A"])
    _pick(at, "Metric", ["CPU_Usage"])
    assert "interface-level data" in _infos(at)
    assert not at.metric                      # nothing forecast for every interface
    _pick(at, "Interface", ["eth0"])
    assert at.metric                          # now it runs


def test_data_without_interfaces_only_needs_device_and_metric(interactive):
    interactive.upsert("network", pd.DataFrame({
        "ds": pd.date_range("2026-01-01", periods=40, freq="D").strftime("%Y-%m-%d"),
        "sys_name": ["h1"] * 40,
        "avg_cpu_max": [40.0 + i % 5 for i in range(40)],
    }))
    at = _open()
    for label in ("Device", "Interface", "Metric"):
        assert _widget(at.sidebar.multiselect, label).value == [], label
    _pick(at, "Device", ["h1"])
    _pick(at, "Metric", ["avg_cpu_max"])
    assert "interface-level data" not in _infos(at)
    assert at.metric                          # forecast ran


def test_selecting_filters_runs_the_forecast(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    assert at.metric and at.get("plotly_chart")
    assert "Select at least one device" not in _infos(at)


def test_clearing_a_filter_returns_to_the_prompt(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    assert at.metric
    _pick(at, "Metric", [])
    assert "Select at least one device and one metric" in _infos(at)
    assert not at.metric


def test_manual_model_reports_its_own_mape(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    infos = _infos(at)
    assert "Model Evaluation Complete: Linear Regression applied as configured" in infos
    assert "backtest MAPE:" in infos and "RMSE" not in infos


def test_intelligent_insight_is_an_executive_summary(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    body = " ".join(
        e.value for e in list(at.success) + list(at.warning) + list(at.error)
        if "Model & Trend Analysis" in e.value)
    assert "Projection & Recommendation" in body
    assert "MAPE" in body and "Linear Regression" in body
    assert len(body.split()) > 80           # two paragraphs, not a one-liner


def test_empty_database_shows_a_hint_and_falls_back_to_demo_data(env):
    at = _open()
    caps = _captions(at)
    assert "holds no historical records" in caps
    assert "Demonstration data is displayed" in caps
    assert set(_widget(at.sidebar.multiselect, "Device").options) == SAMPLE_DEVICES


def test_empty_database_can_require_an_upload_instead(env, tmp_path):
    _write_settings(str(tmp_path / "settings.json"), data_source="upload")
    at = _open()
    assert "holds no historical records" in _captions(at)
    assert "There is no data to analyze" in _infos(at)
    assert not at.sidebar.multiselect            # no filters without data


def test_data_source_priority():
    import app
    pick = app._pick_data_source
    # (has_upload, sync_ok, has_db, allow_sample)
    assert pick(False, False, True, True) == "db"          # saved data wins
    assert pick(True, True, True, True) == "db"            # incl. the new upload
    assert pick(True, False, True, True) == "file"         # upload not saved
    assert pick(True, False, False, False) == "file"
    assert pick(False, False, False, True) == "sample"     # empty repository
    assert pick(False, False, False, False) == "none"      # demo disabled


def test_viewers_see_the_saved_data_without_an_upload_widget(env):
    env.upsert("network", _network_rows())
    at = _open(role="viewer")
    assert set(_widget(at.sidebar.multiselect, "Device").options) == {"SRV-A", "SRV-B"}
    assert "historical records up to 9 February 2026" in _captions(at)
    assert not at.get("file_uploader")


def test_compute_stream_is_also_loaded_from_the_database(env):
    env.upsert("compute", pd.DataFrame({"ds": ["2026-01-01", "2026-01-02"],
                                        "host": ["a", "b"], "cpu": [1, 2]}))
    at = _open(stream="🖥️ Compute Stream")
    assert "A total of 2 historical records" in _captions(at)


# --------------------- language switch keeps the filters --------------------- #
def _switch_language(at, code):
    at.selectbox(key="lang_select").select(code).run()
    assert not at.exception, at.exception


def _sidebar_ids(at):
    """Widget ids of the Network sidebar, keyed by name."""
    ids = {name: at.sidebar.multiselect(key=f"net_{name}").proto.id
           for name in ("device", "interface", "metric")}
    ids["amount"] = at.sidebar.number_input(key="net_horizon_amount").proto.id
    ids["method"] = at.sidebar.selectbox(key="net_method").proto.id
    ids["upload"] = at.get("file_uploader")[0].proto.id
    return ids


def test_filters_and_settings_survive_a_language_switch(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    at.sidebar.number_input(key="net_horizon_amount").set_value(2).run()
    at.sidebar.selectbox(key="net_horizon_unit").select("Month").run()
    gran = at.sidebar.selectbox(key="net_granularity")
    wanted = gran.options[1]
    gran.select(wanted).run()
    assert not at.exception, at.exception
    before_gran_index = at.sidebar.selectbox(key="net_granularity").index

    _switch_language(at, "ID")

    ms = lambda name: at.sidebar.multiselect(key=f"net_{name}")      # noqa: E731
    assert ms("device").label == "Perangkat"                          # really Indonesian
    assert ms("device").value == ["SRV-A"]
    assert ms("interface").value == ["eth0"]
    assert ms("metric").value == ["CPU_Usage"]
    assert at.sidebar.number_input(key="net_horizon_amount").value == 2
    unit = at.sidebar.selectbox(key="net_horizon_unit")
    assert unit.options == ["Hari", "Bulan", "Tahun"] and unit.value == "Bulan"
    assert at.sidebar.selectbox(key="net_granularity").index == before_gran_index
    assert at.metric                          # the forecast is still on screen

    _switch_language(at, "EN")                # and back again
    assert ms("device").value == ["SRV-A"] and ms("metric").value == ["CPU_Usage"]
    assert at.sidebar.selectbox(key="net_horizon_unit").value == "Month"


def test_widget_identities_do_not_depend_on_the_language(interactive):
    interactive.upsert("network", _network_rows())
    english = _sidebar_ids(_open(lang="EN"))
    indonesian = _sidebar_ids(_open(lang="ID"))
    assert english == indonesian


def test_filters_stay_empty_after_a_language_switch_too(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _switch_language(at, "ID")
    for name in ("device", "interface", "metric"):
        assert at.sidebar.multiselect(key=f"net_{name}").value == []
    assert "Pilih minimal satu perangkat dan satu metrik" in _infos(at)


def test_valid_choices_are_kept_when_dependent_options_change(interactive):
    rows = _network_rows()
    extra = rows[(rows["Device_Name"] == "SRV-B")
                 & (rows["Metric_Name"] == "CPU_Usage")].copy()
    extra["Interface"] = "eth1"
    interactive.upsert("network", pd.concat([rows, extra], ignore_index=True))
    at = _open()
    _choose(at)                                              # SRV-A / eth0 / CPU
    _pick(at, "Device", ["SRV-A", "SRV-B"])                  # Interface options grow
    ifaces = at.sidebar.multiselect(key="net_interface")
    assert set(ifaces.options) == {"eth0", "eth1"}
    assert ifaces.value == ["eth0"]                          # not wiped
    assert at.sidebar.multiselect(key="net_metric").value == ["CPU_Usage"]
    assert at.metric                                         # still forecasting
    _pick(at, "Interface", ["eth0", "eth1"])
    _pick(at, "Device", ["SRV-A"])                           # eth1 is no longer valid
    ifaces = at.sidebar.multiselect(key="net_interface")
    assert ifaces.options == ["eth0"] and ifaces.value == ["eth0"]


def test_going_home_starts_the_next_visit_with_empty_filters(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    assert at.sidebar.multiselect(key="net_device").value == ["SRV-A"]
    at.button(key="home_brand_btn").click().run()
    assert not [k for k in at.session_state.filtered_state if str(k).startswith("_flt_")]
    at.query_params["mode"] = "analytics"
    at.run()
    assert at.sidebar.multiselect(key="net_device").value == []


# ----------------------------- collapsed expander ---------------------------- #
def _structure_expander(at):
    return next(e for e in at.expander if "Detected structure" in e.label)


def test_detected_structure_is_collapsed_by_default(env):
    env.upsert("network", _network_rows())
    assert _structure_expander(_open()).proto.expanded is False


def test_detected_structure_is_collapsed_on_demo_data_and_in_indonesian(env):
    at = _open()                                          # demonstration data
    assert _structure_expander(at).proto.expanded is False
    env.upsert("network", _network_rows())
    id_expander = next(e for e in _open(lang="ID").expander
                       if "Struktur" in e.label)
    assert id_expander.proto.expanded is False
# ------------------------------- Excel export ------------------------------- #
def test_export_button_appears_only_once_a_forecast_runs(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    assert not at.get("download_button")
    _choose(at)
    buttons = at.get("download_button")
    # One (hidden) download button, driven from the chart's toolbar.
    assert len(buttons) == 1 and buttons[0].proto.label == "Export to Excel (.xlsx)"


def test_export_lives_in_the_chart_toolbar_not_on_the_page(interactive):
    import app
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    # The chart is scoped so the toolbar script can find its modebar.
    chart_css = " ".join(m.value for m in at.markdown)
    assert ".st-key-export_excel_host{position:absolute" in chart_css
    assert "opacity:0" in chart_css
    # Bridge script: adds "Export to Excel" first in this chart's modebar,
    # with a sheet icon, and clicks the hidden download button.
    js = app._EXPORT_BRIDGE_JS
    assert "'.st-key-forecast_chart'" in js
    assert "var TITLE = 'Export to Excel'" in js
    assert app._EXCEL_ICON_PATH in js
    assert "bar.insertBefore(group, bar.firstElementChild)" in js
    assert ".st-key-export_excel button" in js
    assert "__" not in js.replace("__nucleusExport", "")   # placeholders filled


def test_export_follows_the_active_filters(interactive):
    interactive.upsert("network", _network_rows())
    at = _open()
    _choose(at)
    _widget(at.sidebar.number_input, "Amount").set_value(15).run()
    sheet = _read_export(at)
    body = pd.DataFrame(list(sheet["Combined_Timeline"].values)[1:],
                        columns=[c.value for c in sheet["Combined_Timeline"][1]])
    assert set(body["Device"]) == {"SRV-A"}
    assert set(body["Metric"]) == {"CPU_Usage"}
    assert (body["Data_Type"] == "Forecast").sum() == 15
    summary = {r[0].value: r[1].value for r in sheet["Summary & Metadata"].iter_rows()
               if r[0].value}
    assert summary["Forecast horizon"] == "15 Day"
    assert summary["Device"] == "SRV-A" and summary["Interface"] == "eth0"


def _read_export(at):
    """The workbook the download button serves (kept in the session)."""
    import io
    from openpyxl import load_workbook
    return load_workbook(io.BytesIO(at.session_state["_flt_xlsx_cache"][1]))
