import numpy as np
import pandas as pd
import pytest

import forecasting as fc
import insight_report as ir


def _series(values, unit="%", start="2026-01-01"):
    s = pd.Series(values, index=pd.date_range(start, periods=len(values), freq="D"))
    s.attrs["unit"] = unit
    return s


def _facts(device, metric, values, unit="%", method="Linear Regression",
           horizon=30):
    res = fc.forecast(_series(values, unit), horizon, method, freq="D")
    return ir.facts_from_forecast(device, "—", metric, unit, res)


def _ramp(start, end, n=90, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    return np.linspace(start, end, n) + rng.normal(0, noise, n)


# ----------------------------- MAPE in the engine --------------------------- #
def test_mape_is_percentage_error():
    assert fc.mape(np.array([100.0, 200.0]), np.array([110.0, 180.0])) == pytest.approx(10.0)


def test_mape_ignores_zero_actuals_and_handles_all_zero():
    assert fc.mape(np.array([0.0, 100.0]), np.array([5.0, 90.0])) == pytest.approx(10.0)
    assert np.isnan(fc.mape(np.array([0.0, 0.0]), np.array([1.0, 2.0])))


def test_auto_ranks_models_by_mape_and_exposes_it():
    res = fc.forecast(_series(_ramp(40, 60, noise=1.0)), 14, fc.AUTO_METHOD, freq="D")
    scores = res.meta["auto_scores"]
    best = res.meta["auto_choice"]
    assert res.meta["error_metric"] == "MAPE"
    assert scores[best] == min(scores.values())
    assert res.meta["backtest_mape"] == pytest.approx(scores[best])
    assert "RMSE" not in res.notes                    # no stale RMSE wording
    assert all(0 <= v < 100 for v in scores.values())  # percentages, not RMSE scale


def test_manual_method_also_reports_its_backtest_mape():
    res = fc.forecast(_series(_ramp(40, 60, noise=1.0)), 14, "Linear Regression", freq="D")
    assert res.meta["error_metric"] == "MAPE"
    assert res.meta["model_used"] == "Linear Regression"
    assert res.meta["backtest_mape"] is not None and res.meta["backtest_mape"] >= 0


# ------------------------------ formatting ---------------------------------- #
def test_number_and_date_formatting_per_language():
    assert ir.format_int(36073, "EN") == "36,073"
    assert ir.format_int(36073, "ID") == "36.073"
    assert ir.format_pct(3.4249, "EN") == "3.42%"
    assert ir.format_pct(3.4249, "ID") == "3,42%"
    assert ir.format_pct(8.04, "EN", 1, signed=True) == "+8.0%"
    assert ir.format_date("2026-02-09", "EN") == "9 February 2026"
    assert ir.format_date("2026-08-17", "ID") == "17 Agustus 2026"


def test_join_names():
    assert ir.join_names(["a"]) == "a"
    assert ir.join_names(["a", "b"]) == "a and b"
    assert ir.join_names(["a", "b", "c"]) == "a, b, and c"
    assert ir.join_names(["a", "b", "c"], "ID") == "a, b, dan c"
    assert ir.join_names(list("abcdefghij"), "EN", limit=3) == "a, b, c, and 7 more"


# ------------------------------ the narrative -------------------------------- #
def test_two_correlated_metrics_are_compared_in_depth():
    cpu = _facts("BR1-LN-AS-02", "avg_cpu_max", _ramp(40, 60, noise=1.0, seed=1))
    mem = _facts("BR1-LN-AS-02", "avg_memory_max", _ramp(50, 66, noise=1.0, seed=2))
    out = ir.build_executive_insight([cpu, mem], "EN", "30 Day")
    assert len(out.paragraphs) == 2
    text = out.markdown
    assert "Model & Trend Analysis" in text and "Projection & Recommendation" in text
    assert "2 series (1 device, 2 metrics)" in text
    assert "Linear Regression" in text and "MAPE" in text
    assert "steepest projected growth" in text
    assert "avg_cpu_max" in text and "avg_memory_max" in text
    assert "strong and positive" in text and "planned jointly" in text
    assert "Capacity assessment:" in text and "Recommended action:" in text


def test_critical_projection_names_the_threshold_date_and_mitigation():
    hot = _facts("SRV-1", "avg_cpu_max", _ramp(60, 80, noise=0.5, seed=3))
    out = ir.build_executive_insight([hot], "EN", "30 Day")
    assert out.severity == "critical"
    assert "CRITICAL" in out.markdown
    assert "85% critical utilization threshold on" in out.markdown
    assert "start proactive mitigation before" in out.markdown
    assert "rebalance workloads" in out.markdown        # CPU-specific action


def test_stable_projection_reports_headroom_and_no_action():
    calm = _facts("SRV-1", "avg_memory_max", _ramp(30, 34, noise=0.3, seed=4))
    out = ir.build_executive_insight([calm], "EN")
    assert out.severity == "stable"
    assert "STABLE" in out.markdown and "percentage points of headroom" in out.markdown
    assert "no intervention is required" in out.markdown


def test_non_percent_unit_uses_relative_growth_not_thresholds():
    grow = _facts("SW-1", "Bandwidth", _ramp(100, 400, noise=1.0, seed=5), unit="Mbps")
    assert grow.change_pct >= ir.GROWTH_NOTABLE_PCT
    out = ir.build_executive_insight([grow], "EN", "30 Day")
    assert out.severity == "elevated"
    assert "no absolute capacity threshold is defined for Bandwidth" in out.markdown
    assert "link utilization" in out.markdown            # network action
    assert "85%" not in out.markdown


def test_modest_growth_on_non_percent_unit_is_stable():
    flat = _facts("SW-1", "Bandwidth", _ramp(100, 110, noise=0.5, seed=6), unit="Mbps")
    out = ir.build_executive_insight([flat], "EN")
    assert out.severity == "stable"
    assert "within normal variation" in out.markdown


def test_missing_mape_is_stated_instead_of_invented():
    f = _facts("SRV-1", "avg_cpu_max", _ramp(40, 50, noise=0.5))
    f.mape = None
    text = ir.build_executive_insight([f], "EN").markdown
    assert "backtest accuracy could not be established" in text
    assert "predictive reliability" not in text


def test_indonesian_narrative():
    cpu = _facts("SRV-1", "avg_cpu_max", _ramp(40, 60, noise=1.0, seed=1))
    mem = _facts("SRV-1", "avg_memory_max", _ramp(50, 66, noise=1.0, seed=2))
    text = ir.build_executive_insight([cpu, mem], "ID", "30 Hari").markdown
    assert "Analisis Model & Tren" in text and "Proyeksi & Rekomendasi" in text
    assert "Ko-pergerakan historis" in text and "Rekomendasi:" in text
    assert "MAPE" in text and "Executive" not in text


def test_constant_series_do_not_break_the_correlation_step():
    a = _facts("SRV-1", "avg_cpu_max", [50.0] * 60)
    b = _facts("SRV-1", "avg_memory_max", _ramp(40, 50, noise=0.5))
    out = ir.build_executive_insight([a, b], "EN")
    assert "Historical co-movement" not in out.markdown   # skipped, no crash


def test_plain_text_for_speech_has_no_markdown():
    f = _facts("SRV-1", "avg_cpu_max", _ramp(40, 50, noise=0.5))
    assert "**" not in ir.build_executive_insight([f], "EN").plain


def test_empty_input_is_rejected():
    with pytest.raises(ValueError):
        ir.build_executive_insight([], "EN")
