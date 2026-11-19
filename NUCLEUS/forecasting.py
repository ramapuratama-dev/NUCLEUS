"""forecasting.py — forecasting engine for NUCLEUS.

Multiple methods behind one `forecast()` interface returning a uniform
`ForecastResult`. The engine is tuned to capture non-linear trends, seasonality
and short-term volatility rather than flat straight lines:

  * SMA / Exponential Smoothing — damped-trend baseline
  * Linear Regression            — simple trend extrapolation
  * Holt-Winters                 — additive/multiplicative trend + seasonality
  * SARIMAX / ARIMA              — autoregressive + seasonal differencing
  * Prophet                      — explicit daily/weekly/yearly seasonality
  * Gradient Boosting (lags)     — ML on lag/rolling features (XGBoost/LightGBM
                                   when available, else sklearn)
  * Auto (Best Fit)              — backtests the above and keeps the lowest error

Optional dependencies (prophet, xgboost, lightgbm, statsmodels) are imported
lazily and the engine degrades gracefully when they are missing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pandas as pd

MIN_HISTORY_POINTS = 5
_BAND_K = 1.96  # ~95% interval multiplier for residual-based bands

AUTO_METHOD = "Auto (Best Fit)"


@dataclass
class ForecastResult:
    history: pd.Series
    forecast: pd.Series
    lower: pd.Series
    upper: pd.Series
    method: str
    notes: str = ""
    meta: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Capability checks
# --------------------------------------------------------------------------- #
def _has(pkg: str) -> bool:
    try:
        __import__(pkg)
        return True
    except Exception:  # noqa: BLE001
        return False


def _prophet_available() -> bool:
    return _has("prophet")


def _statsmodels_available() -> bool:
    return _has("statsmodels")


def _boosting_backend() -> Optional[str]:
    """Return the best available gradient-boosting backend, or None."""
    if _has("xgboost"):
        return "xgboost"
    if _has("lightgbm"):
        return "lightgbm"
    if _has("sklearn"):
        return "sklearn"
    return None


def available_methods() -> list[str]:
    """Return selectable method names, best/most-capable first."""
    methods = [AUTO_METHOD, "SMA / Exponential Smoothing", "Linear Regression"]
    if _statsmodels_available():
        methods.append("Holt-Winters")
        methods.append("SARIMAX / ARIMA")
    if _boosting_backend() is not None:
        methods.append("Gradient Boosting (lags)")
    # Prophet is always offered; it falls back transparently if not installed.
    methods.append("Prophet")
    return methods


# --------------------------------------------------------------------------- #
# Shared helpers
# --------------------------------------------------------------------------- #
def _future_index(series: pd.Series, horizon: int, freq: str) -> pd.DatetimeIndex:
    last = series.index[-1]
    return pd.date_range(start=last, periods=horizon + 1, freq=freq)[1:]


def _seasonal_period(freq: str, n: int) -> Optional[int]:
    """A sensible seasonal period for the given frequency, if data supports it."""
    base = {"min": 60, "h": 24, "D": 7, "W": 52, "MS": 12}.get(freq, 7)
    # Need at least two full cycles to estimate seasonality.
    return base if n >= 2 * base else None


def _residual_band(forecast: pd.Series, resid_std: float,
                   history_len: int) -> tuple[pd.Series, pd.Series]:
    """Build a widening band from residual std when a model gives no interval."""
    steps = np.arange(1, len(forecast) + 1)
    widen = resid_std * np.sqrt(1.0 + steps / max(history_len, 1))
    lower = forecast - _BAND_K * widen
    upper = forecast + _BAND_K * widen
    lower.name, upper.name = "lower", "upper"
    return lower, upper


def _clip_nonneg(result: ForecastResult, series: pd.Series) -> ForecastResult:
    """Keep bands sane and floor at zero when the history is non-negative."""
    if (series >= 0).all():
        result.forecast = result.forecast.clip(lower=0)
        result.lower = result.lower.clip(lower=0)
    result.upper = pd.concat([result.lower, result.upper], axis=1).max(axis=1)
    return result


# --------------------------------------------------------------------------- #
# Method implementations
# --------------------------------------------------------------------------- #
def _forecast_sma(series, horizon, freq) -> ForecastResult:
    idx = _future_index(series, horizon, freq)
    window = max(2, min(7, len(series) // 3))

    # Exponential smoothing level + damped recent drift (avoids runaway lines).
    alpha, phi = 0.3, 0.9
    level = series.iloc[0]
    for v in series.iloc[1:]:
        level = alpha * v + (1 - alpha) * level
    recent = series.tail(window)
    drift = (recent.iloc[-1] - recent.iloc[0]) / max(len(recent) - 1, 1)

    steps = np.arange(1, horizon + 1)
    damp = np.cumsum(phi ** steps)
    values = level + drift * damp
    forecast = pd.Series(values, index=idx, name="forecast")

    fitted = series.rolling(window, min_periods=1).mean()
    resid_std = float((series - fitted).std(ddof=1) or series.std(ddof=1) or 1.0)
    lower, upper = _residual_band(forecast, resid_std, len(series))
    res = ForecastResult(series, forecast, lower, upper,
                         "SMA / Exponential Smoothing",
                         meta={"window": window, "alpha": alpha})
    return _clip_nonneg(res, series)


def _forecast_linreg(series, horizon, freq) -> ForecastResult:
    idx = _future_index(series, horizon, freq)
    x = np.arange(len(series), dtype=float)
    y = series.to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    fx = np.arange(len(series), len(series) + horizon, dtype=float)
    values = slope * fx + intercept
    forecast = pd.Series(values, index=idx, name="forecast")

    resid = y - (slope * x + intercept)
    resid_std = float(np.std(resid, ddof=1) or 1.0)
    lower, upper = _residual_band(forecast, resid_std, len(series))
    res = ForecastResult(series, forecast, lower, upper, "Linear Regression",
                         meta={"slope": slope, "intercept": intercept})
    return _clip_nonneg(res, series)


def _forecast_holt_winters(series, horizon, freq) -> ForecastResult:
    if not _statsmodels_available():
        res = _forecast_linreg(series, horizon, freq)
        res.method = "Holt-Winters"
        res.notes = "statsmodels not installed; fell back to Linear Regression."
        return res

    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    idx = _future_index(series, horizon, freq)
    sp = _seasonal_period(freq, len(series))
    y = series.astype(float)
    # Multiplicative seasonality needs strictly positive data.
    seasonal_mode = "mul" if (sp and (y > 0).all()) else ("add" if sp else None)
    try:
        model = ExponentialSmoothing(
            y, trend="add", damped_trend=True,
            seasonal=seasonal_mode, seasonal_periods=sp,
            initialization_method="estimated",
        ).fit()
        values = np.asarray(model.forecast(horizon))
        forecast = pd.Series(values, index=idx, name="forecast")
        resid_std = float(np.std(model.resid, ddof=1) or y.std(ddof=1) or 1.0)
        lower, upper = _residual_band(forecast, resid_std, len(series))
        res = ForecastResult(series, forecast, lower, upper, "Holt-Winters",
                             meta={"seasonal_periods": sp, "seasonal": seasonal_mode})
        return _clip_nonneg(res, series)
    except Exception as exc:  # noqa: BLE001
        res = _forecast_linreg(series, horizon, freq)
        res.method = "Holt-Winters"
        res.notes = f"Holt-Winters failed ({exc}); fell back to Linear Regression."
        return res


def _forecast_sarimax(series, horizon, freq) -> ForecastResult:
    if not _statsmodels_available():
        res = _forecast_linreg(series, horizon, freq)
        res.method = "SARIMAX / ARIMA"
        res.notes = "statsmodels not installed; fell back to Linear Regression."
        return res

    from statsmodels.tsa.statespace.sarimax import SARIMAX

    idx = _future_index(series, horizon, freq)
    y = series.astype(float)
    sp = _seasonal_period(freq, len(series))
    order = (1, 1, 1)
    seasonal_order = (1, 1, 1, sp) if sp else (0, 0, 0, 0)
    try:
        model = SARIMAX(
            y, order=order, seasonal_order=seasonal_order,
            enforce_stationarity=False, enforce_invertibility=False,
        ).fit(disp=False)
        pred = model.get_forecast(steps=horizon)
        forecast = pd.Series(np.asarray(pred.predicted_mean), index=idx, name="forecast")
        ci = pred.conf_int(alpha=0.05)
        lower = pd.Series(np.asarray(ci.iloc[:, 0]), index=idx, name="lower")
        upper = pd.Series(np.asarray(ci.iloc[:, 1]), index=idx, name="upper")
        res = ForecastResult(series, forecast, lower, upper, "SARIMAX / ARIMA",
                             meta={"order": order, "seasonal_order": seasonal_order})
        return _clip_nonneg(res, series)
    except Exception as exc:  # noqa: BLE001
        res = _forecast_linreg(series, horizon, freq)
        res.method = "SARIMAX / ARIMA"
        res.notes = f"SARIMAX failed ({exc}); fell back to Linear Regression."
        return res


def _build_lag_features(values: np.ndarray, lags: list[int],
                        roll: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """Construct a supervised matrix from lag and rolling statistics."""
    n = len(values)
    start = max(max(lags), max(roll))
    rows, targets = [], []
    for t in range(start, n):
        feat = [values[t - l] for l in lags]
        for w in roll:
            window = values[t - w:t]
            feat.append(window.mean())
            feat.append(window.std(ddof=0))
        rows.append(feat)
        targets.append(values[t])
    return np.array(rows, dtype=float), np.array(targets, dtype=float)


def _make_boosting_regressor():
    backend = _boosting_backend()
    if backend == "xgboost":
        from xgboost import XGBRegressor
        return XGBRegressor(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.9, colsample_bytree=0.9, random_state=0,
        ), backend
    if backend == "lightgbm":
        from lightgbm import LGBMRegressor
        return LGBMRegressor(
            n_estimators=400, max_depth=-1, num_leaves=31,
            learning_rate=0.05, subsample=0.9, random_state=0, verbose=-1,
        ), backend
    if backend == "sklearn":
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(
            n_estimators=300, max_depth=3, learning_rate=0.05, subsample=0.9,
            random_state=0,
        ), backend
    return None, None


def _forecast_boosting(series, horizon, freq) -> ForecastResult:
    model, backend = _make_boosting_regressor()
    if model is None:
        res = _forecast_linreg(series, horizon, freq)
        res.method = "Gradient Boosting (lags)"
        res.notes = "No boosting backend installed; fell back to Linear Regression."
        return res

    idx = _future_index(series, horizon, freq)
    y = series.to_numpy(dtype=float)
    sp = _seasonal_period(freq, len(series)) or 7
    lags = sorted({1, 2, 3, 7, sp})
    lags = [l for l in lags if l < len(y)]
    roll = sorted({w for w in (3, 7, sp) if w < len(y)}) or [min(3, len(y) - 1)]
    need = max(max(lags), max(roll)) + 2
    if len(y) < need:
        res = _forecast_holt_winters(series, horizon, freq)
        res.method = "Gradient Boosting (lags)"
        res.notes = (f"Not enough history for lag features (need ≥ {need}); "
                     "fell back to Holt-Winters.")
        return res

    X, target = _build_lag_features(y, lags, roll)
    try:
        model.fit(X, target)
    except Exception as exc:  # noqa: BLE001
        res = _forecast_holt_winters(series, horizon, freq)
        res.method = "Gradient Boosting (lags)"
        res.notes = f"Boosting failed ({exc}); fell back to Holt-Winters."
        return res

    # In-sample residual std for the band.
    resid_std = float(np.std(target - model.predict(X), ddof=1) or y.std(ddof=1) or 1.0)

    # Recursive multi-step forecasting.
    hist = list(y)
    preds = []
    for _ in range(horizon):
        feat = [hist[-l] for l in lags]
        for w in roll:
            window = np.array(hist[-w:])
            feat.append(window.mean())
            feat.append(window.std(ddof=0))
        yhat = float(model.predict(np.array([feat], dtype=float))[0])
        preds.append(yhat)
        hist.append(yhat)

    forecast = pd.Series(preds, index=idx, name="forecast")
    lower, upper = _residual_band(forecast, resid_std, len(series))
    res = ForecastResult(series, forecast, lower, upper,
                         "Gradient Boosting (lags)",
                         meta={"backend": backend, "lags": lags, "roll": roll})
    return _clip_nonneg(res, series)


def _forecast_prophet(series, horizon, freq) -> ForecastResult:
    if not _prophet_available():
        res = _forecast_holt_winters(series, horizon, freq)
        res.method = "Prophet"
        res.notes = ("Prophet not installed; fell back to Holt-Winters "
                     "(seasonal). Install `prophet` for full seasonality.")
        return res

    from prophet import Prophet

    idx = _future_index(series, horizon, freq)
    n = len(series)
    span_days = (series.index[-1] - series.index[0]).days or 1
    try:
        train = pd.DataFrame({"ds": series.index, "y": series.to_numpy(dtype=float)})
        model = Prophet(
            # Explicit seasonality; yearly only when data covers enough range.
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=(span_days >= 365 * 1.5),
            # More flexible trend so the fit is not a flat line.
            changepoint_prior_scale=0.3,
            seasonality_prior_scale=10.0,
            seasonality_mode="multiplicative" if (series > 0).all() else "additive",
        )
        model.fit(train)
        future = model.make_future_dataframe(periods=horizon, freq=freq)
        pred = model.predict(future).set_index("ds")
        tail = pred.iloc[-horizon:]
        forecast = pd.Series(tail["yhat"].to_numpy(), index=idx, name="forecast")
        lower = pd.Series(tail["yhat_lower"].to_numpy(), index=idx, name="lower")
        upper = pd.Series(tail["yhat_upper"].to_numpy(), index=idx, name="upper")
        res = ForecastResult(series, forecast, lower, upper, "Prophet",
                             meta={"changepoint_prior_scale": 0.3})
        return _clip_nonneg(res, series)
    except Exception as exc:  # noqa: BLE001
        res = _forecast_holt_winters(series, horizon, freq)
        res.method = "Prophet"
        res.notes = f"Prophet failed ({exc}); fell back to Holt-Winters."
        return res


# Base (non-auto) methods available for dispatch and auto-selection.
_DISPATCH: dict[str, Callable] = {
    "SMA / Exponential Smoothing": _forecast_sma,
    "Linear Regression": _forecast_linreg,
    "Holt-Winters": _forecast_holt_winters,
    "SARIMAX / ARIMA": _forecast_sarimax,
    "Gradient Boosting (lags)": _forecast_boosting,
    "Prophet": _forecast_prophet,
}


# --------------------------------------------------------------------------- #
# Error metrics & backtesting for Auto (Best Fit)
# --------------------------------------------------------------------------- #
def rmse(actual: np.ndarray, pred: np.ndarray) -> float:
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    return float(np.sqrt(np.mean((actual - pred) ** 2)))


def mape(actual: np.ndarray, pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error in percent.

    Points where the actual value is (almost) zero have no defined percentage
    error and are left out. ``nan`` is returned when every point is excluded.
    """
    actual, pred = np.asarray(actual, float), np.asarray(pred, float)
    denom = np.where(np.abs(actual) < 1e-9, np.nan, np.abs(actual))
    ratio = np.abs((actual - pred) / denom)
    if not np.isfinite(ratio).any():
        return float("nan")
    return float(np.nanmean(ratio) * 100.0)


def _backtest_error(method: str, series: pd.Series, freq: str,
                    test_frac: float = 0.2) -> Optional[float]:
    """Hold out the tail of the series and score a one-shot forecast by MAPE (%)."""
    n = len(series)
    test_n = max(1, min(int(round(n * test_frac)), n - MIN_HISTORY_POINTS))
    if n - test_n < MIN_HISTORY_POINTS:
        return None
    train = series.iloc[:-test_n]
    actual = series.iloc[-test_n:]
    try:
        res = _DISPATCH[method](train, test_n, freq)
        pred = res.forecast.to_numpy()[:test_n]
        if len(pred) != len(actual) or not np.isfinite(pred).all():
            return None
        err = mape(actual.to_numpy(), pred)
        return err if np.isfinite(err) else None
    except Exception:  # noqa: BLE001
        return None


def _auto_select(series: pd.Series, horizon: int, freq: str) -> ForecastResult:
    """Backtest candidate models and forecast with the lowest-error one."""
    candidates = [m for m in _DISPATCH if m != "Linear Regression"]
    # Linear Regression stays as a guaranteed fallback candidate too.
    candidates.append("Linear Regression")

    scores: dict[str, float] = {}
    for method in candidates:
        err = _backtest_error(method, series, freq)
        if err is not None and np.isfinite(err):
            scores[method] = err

    if not scores:
        res = _forecast_holt_winters(series, horizon, freq)
        res.method = f"{AUTO_METHOD} → Holt-Winters"
        res.notes = "Backtesting inconclusive; defaulted to Holt-Winters."
        return res

    best = min(scores, key=scores.get)
    res = _DISPATCH[best](series, horizon, freq)
    # The ranking is kept as data (MAPE in percent, per candidate model) so the
    # UI can word it in the active language. ``res.notes`` only carries the
    # model's own fallback warnings, if any.
    res.meta["model_used"] = res.method
    res.method = f"{AUTO_METHOD} → {res.method}"
    res.meta["auto_scores"] = scores
    res.meta["auto_choice"] = best
    res.meta["error_metric"] = "MAPE"
    res.meta["backtest_mape"] = scores[best]
    return res


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def forecast(series: pd.Series, horizon_days: int, method: str,
             freq: str = "D") -> ForecastResult:
    """Run the selected forecasting method over `horizon_days` steps."""
    if len(series) < MIN_HISTORY_POINTS:
        raise ValueError(
            f"Need at least {MIN_HISTORY_POINTS} historical points to forecast; "
            f"got {len(series)}."
        )
    series = series.sort_index().astype(float)
    series = series[~series.index.duplicated(keep="first")]

    if method == AUTO_METHOD:
        result = _auto_select(series, int(horizon_days), freq)
    elif method in _DISPATCH:
        result = _DISPATCH[method](series, int(horizon_days), freq)
        # One extra backtest so a manually chosen model also reports its error.
        result.meta["model_used"] = result.method
        result.meta["error_metric"] = "MAPE"
        result.meta["backtest_mape"] = _backtest_error(method, series, freq)
    else:
        raise ValueError(f"Unknown forecasting method: {method!r}")

    result.meta.setdefault("unit", series.attrs.get("unit", ""))
    result.meta.setdefault("device", series.attrs.get("device", ""))
    return result


def days_until_breach(result: ForecastResult, threshold: float) -> Optional[int]:
    """Days from the last history date until the forecast first crosses threshold.

    Retained for callers that still track thresholds. Returns None if no breach
    occurs within the forecast horizon.
    """
    future = result.forecast
    breaching = future[future >= threshold]
    if breaching.empty:
        return None
    first = breaching.index[0]
    last_history = result.history.index[-1]
    return max(0, (first - last_history).days)
