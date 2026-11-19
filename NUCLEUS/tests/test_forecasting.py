import numpy as np
import pandas as pd
import pytest

import forecasting as fc


def _series(n=60, slope=1.0, start=10.0, seasonal=0.0, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-01-01", periods=n, freq="D")
    t = np.arange(n)
    vals = (start + slope * t
            + seasonal * np.sin(2 * np.pi * t / 7.0)
            + rng.normal(0, noise, n))
    s = pd.Series(vals, index=idx, name="CPU_Usage")
    s.attrs["unit"] = "%"
    s.attrs["device"] = "H1"
    return s


ALL_METHODS = [
    "SMA / Exponential Smoothing",
    "Linear Regression",
    "Holt-Winters",
    "SARIMAX / ARIMA",
    "Gradient Boosting (lags)",
    "Prophet",
    fc.AUTO_METHOD,
]


@pytest.mark.parametrize("method", ALL_METHODS)
def test_forecast_shape_and_band(method):
    s = _series(seasonal=4.0, noise=1.0)
    res = fc.forecast(s, horizon_days=14, method=method, freq="D")
    assert len(res.forecast) == 14
    assert len(res.lower) == 14 and len(res.upper) == 14
    assert res.forecast.index[0] > s.index[-1]
    assert res.forecast.index.is_monotonic_increasing
    # Band ordering holds for every method.
    assert (res.lower.values <= res.forecast.values + 1e-6).all()
    assert (res.forecast.values <= res.upper.values + 1e-6).all()
    assert np.isfinite(res.forecast.values).all()


def test_available_methods_includes_auto_first():
    methods = fc.available_methods()
    assert methods[0] == fc.AUTO_METHOD
    assert "Linear Regression" in methods


def test_too_little_history_raises():
    s = _series(n=3)
    with pytest.raises(ValueError, match="historical points"):
        fc.forecast(s, 7, "Linear Regression")


def test_unknown_method_raises():
    with pytest.raises(ValueError, match="Unknown"):
        fc.forecast(_series(), 7, "Magic")


def test_linreg_extrapolates_trend():
    s = _series(slope=2.0, start=5.0)
    res = fc.forecast(s, 10, "Linear Regression")
    assert res.forecast.iloc[-1] > res.forecast.iloc[0]


def test_auto_selection_records_choice():
    s = _series(seasonal=6.0, noise=1.0)
    res = fc.forecast(s, 14, fc.AUTO_METHOD, freq="D")
    assert res.method.startswith(fc.AUTO_METHOD)
    assert "auto_choice" in res.meta
    assert "auto_scores" in res.meta and res.meta["auto_scores"]


def test_boosting_captures_nonlinearity():
    # A seasonal series: boosting forecast should not be a flat constant line.
    s = _series(slope=0.2, seasonal=8.0, noise=0.5)
    res = fc.forecast(s, 21, "Gradient Boosting (lags)", freq="D")
    assert res.forecast.std() > 1e-6


def test_error_metrics():
    a = np.array([1.0, 2.0, 3.0, 4.0])
    p = np.array([1.0, 2.0, 3.0, 4.0])
    assert fc.rmse(a, p) == pytest.approx(0.0)
    assert fc.mape(a, p) == pytest.approx(0.0)
    assert fc.rmse(a, p + 1) == pytest.approx(1.0)


def test_days_until_breach_helper_still_works():
    s = _series(slope=1.0, start=50.0)
    res = fc.forecast(s, 14, "Linear Regression")
    assert fc.days_until_breach(res, threshold=50) is not None
    assert fc.days_until_breach(res, threshold=10_000) is None
