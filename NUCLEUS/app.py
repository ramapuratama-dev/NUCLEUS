"""app.py — NUCLEUS: IT Infrastructure Monitoring & Analytics Platform.

NUCLEUS = Network, Unified Compute, and Layered Environment Under Surveillance.

Streamlit UI that wires together data_loader, forecasting and nucleus_ai.
Run with:  streamlit run app.py
"""
from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

import analytics_db
import auth
import insight_report
import nucleus_ai
import data_loader
import database_admin
import excel_export
import forecasting
import session_guard
import settings_store
from translations import t, get_lang, set_lang


def _logo_svg() -> str:
    """A modern NUCLEUS mark: a glowing core nucleus with orbiting network nodes.

    Represents a unified compute core (the nucleus) surrounded by a layered,
    networked environment under surveillance — the meaning behind the name.
    """
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" '
        'viewBox="0 0 48 48" role="img" aria-label="NUCLEUS logo">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#6366f1"/>'
        '<stop offset="1" stop-color="#0ea5e9"/></linearGradient>'
        '<radialGradient id="core" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0" stop-color="#ffffff"/>'
        '<stop offset="1" stop-color="#bae6fd"/></radialGradient></defs>'
        '<rect x="1" y="1" width="46" height="46" rx="12" fill="url(#g)"/>'
        # layered orbital rings (the "layered environment / network")
        '<circle cx="24" cy="24" r="15" fill="none" stroke="#ffffff" '
        'stroke-width="1.6" opacity="0.45"/>'
        '<ellipse cx="24" cy="24" rx="15" ry="6" fill="none" stroke="#ffffff" '
        'stroke-width="1.6" opacity="0.65"/>'
        '<ellipse cx="24" cy="24" rx="6" ry="15" fill="none" stroke="#ffffff" '
        'stroke-width="1.6" opacity="0.65"/>'
        # orbiting network nodes (the "network / unified compute" endpoints)
        '<circle cx="24" cy="9" r="2.4" fill="#ffffff"/>'
        '<circle cx="39" cy="24" r="2.4" fill="#ffffff"/>'
        '<circle cx="24" cy="39" r="2.4" fill="#ffffff"/>'
        '<circle cx="9" cy="24" r="2.4" fill="#ffffff"/>'
        # the nucleus / core
        '<circle cx="24" cy="24" r="6.5" fill="url(#core)"/>'
        '<circle cx="24" cy="24" r="3" fill="#0ea5e9"/>'
        '</svg>'
    )


def _logo_data_uri() -> str:
    import base64

    b64 = base64.b64encode(_logo_svg().encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _login_bg_svg() -> str:
    """A self-contained, futuristic data-center / IT-operations backdrop.

    Deep dark gradient (#07090E → #111827) layered with a fine monitoring grid,
    a glowing cyan/emerald network mesh, and a soft ambient light in the center
    so the login card appears to float. Fully inline (works offline).
    """
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="900" '
        'viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">'
        '<defs>'
        # deep vertical base gradient
        '<linearGradient id="bg" x1="0" y1="0" x2="0.4" y2="1">'
        '<stop offset="0" stop-color="#07090E"/>'
        '<stop offset="0.6" stop-color="#0c1322"/>'
        '<stop offset="1" stop-color="#111827"/></linearGradient>'
        # ambient center glow behind the login card (floating-card effect)
        '<radialGradient id="ambient" cx="0.5" cy="0.46" r="0.42">'
        '<stop offset="0" stop-color="#22d3ee" stop-opacity="0.22"/>'
        '<stop offset="0.5" stop-color="#2563eb" stop-opacity="0.10"/>'
        '<stop offset="1" stop-color="#07090E" stop-opacity="0"/></radialGradient>'
        # corner accents
        '<radialGradient id="glow" cx="0.18" cy="0.2" r="0.6">'
        '<stop offset="0" stop-color="#1e40af" stop-opacity="0.45"/>'
        '<stop offset="1" stop-color="#07090E" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="glow2" cx="0.85" cy="0.85" r="0.6">'
        '<stop offset="0" stop-color="#0d9488" stop-opacity="0.40"/>'
        '<stop offset="1" stop-color="#07090E" stop-opacity="0"/></radialGradient>'
        # fine + coarse monitoring grid
        '<pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">'
        '<path d="M40 0H0V40" fill="none" stroke="#2dd4bf" '
        'stroke-opacity="0.05" stroke-width="1"/></pattern>'
        '<pattern id="grid2" width="200" height="200" patternUnits="userSpaceOnUse">'
        '<path d="M200 0H0V200" fill="none" stroke="#38bdf8" '
        'stroke-opacity="0.07" stroke-width="1"/></pattern>'
        # soft glow filter for the network mesh
        '<filter id="soft" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="3.2" result="b"/>'
        '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/>'
        '</feMerge></filter>'
        '</defs>'
        # base + grids + glows
        '<rect width="1600" height="900" fill="url(#bg)"/>'
        '<rect width="1600" height="900" fill="url(#grid)"/>'
        '<rect width="1600" height="900" fill="url(#grid2)"/>'
        '<rect width="1600" height="900" fill="url(#glow)"/>'
        '<rect width="1600" height="900" fill="url(#glow2)"/>'
        '<rect width="1600" height="900" fill="url(#ambient)"/>'
        # glowing network mesh (links)
        '<g filter="url(#soft)" stroke-linecap="round">'
        '<g stroke="#22d3ee" stroke-opacity="0.45" stroke-width="1.6">'
        '<line x1="150" y1="160" x2="440" y2="300"/>'
        '<line x1="440" y1="300" x2="280" y2="560"/>'
        '<line x1="440" y1="300" x2="740" y2="210"/>'
        '<line x1="740" y1="210" x2="1040" y2="350"/>'
        '</g>'
        '<g stroke="#34d399" stroke-opacity="0.42" stroke-width="1.6">'
        '<line x1="1040" y1="350" x2="1330" y2="240"/>'
        '<line x1="1040" y1="350" x2="1190" y2="660"/>'
        '<line x1="280" y1="560" x2="620" y2="710"/>'
        '<line x1="620" y1="710" x2="1190" y2="660"/>'
        '<line x1="740" y1="210" x2="620" y2="710"/>'
        '</g>'
        # glowing nodes
        '<g fill="#67e8f9">'
        '<circle cx="150" cy="160" r="5"/>'
        '<circle cx="440" cy="300" r="7.5"/>'
        '<circle cx="280" cy="560" r="5"/>'
        '<circle cx="740" cy="210" r="6"/>'
        '</g>'
        '<g fill="#6ee7b7">'
        '<circle cx="1040" cy="350" r="8"/>'
        '<circle cx="1330" cy="240" r="5"/>'
        '<circle cx="1190" cy="660" r="6.5"/>'
        '<circle cx="620" cy="710" r="7"/>'
        '</g>'
        '</g>'
        # faint node halos
        '<g fill="none" stroke="#67e8f9" stroke-opacity="0.16">'
        '<circle cx="440" cy="300" r="17"/>'
        '<circle cx="1040" cy="350" r="19"/>'
        '<circle cx="620" cy="710" r="16"/>'
        '</g>'
        '</svg>'
    )


def _login_bg_data_uri() -> str:
    import base64

    b64 = base64.b64encode(_login_bg_svg().encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


st.set_page_config(
    page_title="NUCLEUS — Infrastructure Monitoring & Analytics",
    page_icon=_logo_data_uri(),
    layout="wide",
    # Keep the settings sidebar open by default (and on refresh) for the
    # Analytics / Monitoring / User Management modules.
    initial_sidebar_state="expanded",
)


def _hide_chrome_css() -> str:
    """Hide Streamlit's Deploy button / main menu / footer, but KEEP the
    sidebar show/hide toggle visible and prominent.

    We deliberately do NOT use ``visibility:hidden`` on the whole header,
    because that cascades to the sidebar collapse/expand control. Instead we
    make the header transparent and non-blocking, remove only the toolbar and
    menu, then force the sidebar toggle to be visible on top.
    """
    return """
          /* Transparent, non-blocking header (keeps its children usable). */
          header[data-testid="stHeader"] {
              background: transparent !important;
              box-shadow: none !important;
              pointer-events: none;  /* let clicks pass through empty areas */
          }
          /* Remove only the Deploy button, the hamburger menu and the footer. */
          [data-testid="stToolbar"] { display: none !important; }
          [data-testid="stDecoration"] { display: none !important; }
          #MainMenu { display: none !important; }
          footer { display: none !important; }

          /* Permanent, fixed navigation panel: hide ALL sidebar collapse /
             expand controls (<< and >>) so it can never be closed. */
          [data-testid="stSidebarCollapseButton"],
          [data-testid="stSidebarCollapsedControl"],
          [data-testid="stSidebarExpandButton"],
          [data-testid="collapsedControl"],
          button[aria-label="Toggle sidebar"],
          button[aria-label="Open sidebar"],
          button[aria-label="Close sidebar"] {
              display: none !important;
          }

          /* Keep the sidebar permanently open, but allow a flexible width
             (user-resizable via Streamlit's drag handle) within sane bounds. */
          [data-testid="stSidebar"] {
              display: block !important;
              visibility: visible !important;
              transform: none !important;
              min-width: 240px !important;
              max-width: 420px !important;
          }
          /* Keep the sidebar resize grip usable even with the header hidden. */
          [data-testid="stSidebarResizeHandle"] {
              display: block !important;
              pointer-events: auto !important;
          }
    """


def _glass_css() -> str:
    """Apple 'Liquid Glass' styling for the module pages (Analytics/Monitoring/
    User Management): metric cards, alert boxes, chart area, expanders, tables
    and the sidebar all become frosted-glass surfaces with hairline borders.

    Theme-aware: colors come from CSS variables set by ``_theme_vars`` so the
    whole UI adapts smoothly between Dark and Light mode."""
    return f"""
          {_theme_vars()}

          /* Theme-aware canvas + base text, with a smooth transition. */
          [data-testid="stAppViewContainer"] {{
              background:
                linear-gradient(180deg, var(--nuc-bg-1), var(--nuc-bg-2)) !important;
              color: var(--nuc-text) !important;
              transition: background 0.35s ease, color 0.35s ease;
          }}
          [data-testid="stAppViewContainer"] *,
          [data-testid="stSidebar"] * {{
              transition: background-color 0.3s ease, color 0.3s ease,
                          border-color 0.3s ease;
          }}
          /* Base text color follows the theme. */
          [data-testid="stAppViewContainer"],
          [data-testid="stSidebar"],
          .main p, .main span, .main label, .main li,
          [data-testid="stSidebar"] p, [data-testid="stSidebar"] span,
          [data-testid="stSidebar"] label,
          h1, h2, h3, h4, h5, h6, [data-testid="stMetricValue"],
          [data-testid="stMetricLabel"] {{
              color: var(--nuc-text) !important;
          }}

          /* Clean, elegant sans-serif typography everywhere. */
          html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"] {{
              font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                           "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          }}

          /* Shared liquid-glass surface: metric cards, alerts, charts,
             expanders, dataframes and the dataset summary. */
          [data-testid="stMetric"],
          [data-testid="stAlert"],
          [data-testid="stNotification"],
          [data-testid="stExpander"] > details,
          [data-testid="stPlotlyChart"],
          [data-testid="stDataFrame"],
          [data-testid="stTable"] {{
              background: var(--nuc-glass) !important;
              backdrop-filter: blur(16px) !important;
              -webkit-backdrop-filter: blur(16px) !important;
              border: 1px solid var(--nuc-border) !important;
              border-radius: 16px !important;
              box-shadow: 0 8px 30px var(--nuc-shadow) !important;
          }}
          [data-testid="stMetric"] {{
              padding: 1rem 1.1rem !important;
          }}
          [data-testid="stPlotlyChart"] {{
              padding: 0.4rem !important;
              overflow: hidden;
          }}
          /* Keep alert text readable while the surface stays glassy. */
          [data-testid="stExpander"] > details {{
              overflow: hidden;
          }}
          [data-testid="stExpander"] summary {{
              border-radius: 16px !important;
              color: var(--nuc-text) !important;
          }}

          /* Sidebar as a frosted glass panel with a hairline edge. */
          [data-testid="stSidebar"] {{
              background: var(--nuc-glass) !important;
              backdrop-filter: blur(18px) !important;
              -webkit-backdrop-filter: blur(18px) !important;
              border-right: 1px solid var(--nuc-border) !important;
          }}

          /* Rounded, glassy inputs/buttons inside the sidebar + main area. */
          [data-testid="stSidebar"] .stButton button,
          .main .stButton button {{
              border-radius: 12px;
              border: 1px solid var(--nuc-border);
          }}
    """


def _lang_pill_css() -> str:
    """Capsule (pill) language switcher in the top-right, matching the selector.

    Content is centered vertically & horizontally and the box is sized to its
    text rather than stretching full width."""
    return """
          /* Position the header's language column as a compact top-right pill. */
          .st-key-lang_header {
              position: fixed;
              top: 14px;
              right: 20px;
              width: 108px;
              z-index: 1000;
          }
          .st-key-lang_header [data-testid="stWidgetLabel"] { display: none; }
          .st-key-lang_header [data-baseweb="select"] > div {
              display: flex !important;
              align-items: center !important;
              min-height: 36px;
              height: 36px;
              padding: 0 8px 0 14px !important;
              background: var(--nuc-glass-strong);
              border: 1px solid var(--nuc-border-strong);
              border-radius: 999px;
              font-size: 0.8rem;
          }
          .st-key-lang_header [data-baseweb="select"] > div > div:first-child {
              display: flex !important;
              align-items: center !important;
              justify-content: space-between !important;
              width: 100% !important;
              line-height: 1 !important;
              padding: 0 !important;
          }
          .st-key-lang_header [data-baseweb="select"] svg {
              display: block; margin: 0;
          }
    """


def _inject_css() -> None:
    """Base chrome + Liquid Glass theme for the authenticated module pages."""
    st.markdown(
        f"""
        <style>
          {_hide_chrome_css()}
          {_glass_css()}
          {_lang_pill_css()}
          {_page_transition_css()}

          /* Pull the main content up toward the top of the page. */
          .main .block-container,
          [data-testid="stMainBlockContainer"] {{
              padding-top: 1.5rem;
          }}
          /* Trim the sidebar's matching top gap so both columns align. */
          [data-testid="stSidebarUserContent"] {{
              padding-top: 1.5rem;
          }}
          /* Reserve space so a bottom-fixed footer never hides content. */
          .main .block-container,
          [data-testid="stMainBlockContainer"] {{
              padding-bottom: 5rem;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Data loading (cached on file bytes / sample flag)
# --------------------------------------------------------------------------- #
@st.cache_data(show_spinner=False)
def _analyze(file_bytes, use_sample: bool):
    """Load + analyze the raw spreadsheet. Returns (raw_df, DetectionResult)."""
    if use_sample or file_bytes is None:
        raw = data_loader.sample_dataframe()
        return raw, data_loader.detect_structure(raw)
    return data_loader.analyze_excel(file_bytes)


@st.cache_data(show_spinner=False)
def _clean(file_bytes, use_sample: bool, freq: str) -> pd.DataFrame:
    raw, _ = _analyze(file_bytes, use_sample)
    return data_loader.clean_and_aggregate(raw, freq=freq)


@st.cache_data(show_spinner=False)
def _analyze_frame(raw: pd.DataFrame):
    """Analyze a DataFrame loaded from the local database."""
    return raw, data_loader.detect_structure(raw)


@st.cache_data(show_spinner=False)
def _clean_frame(raw: pd.DataFrame, freq: str) -> pd.DataFrame:
    return data_loader.clean_and_aggregate(raw, freq=freq)


def _stored_state(stream: str) -> tuple:
    """The stream's saved table and its latest timestamp, cached in the session.

    Loaded from SQLite the first time it is needed in a session (so a refresh
    or a freshly opened tab is filled from the database straight away) and
    reloaded only when the database file changes, e.g. after an upload.
    Returns ``(DataFrame, latest_timestamp_or_None)``; the frame is empty when
    nothing has been saved yet.
    """
    adb = _adb()
    fingerprint = adb.fingerprint()
    key = f"_stored_frame_{stream}"
    cached = st.session_state.get(key)
    if cached is None or cached[0] != fingerprint:
        try:
            frame = adb.load(stream)
        except sqlite3.Error:
            frame = pd.DataFrame()
        latest = analytics_db.latest_timestamp(frame) if not frame.empty else None
        cached = (fingerprint, frame, latest)
        st.session_state[key] = cached
    return cached[1], cached[2]


def _stored_frame(stream: str) -> pd.DataFrame:
    """The stream's saved table (empty DataFrame when nothing is saved)."""
    return _stored_state(stream)[0]


def _freq_label(freq: str) -> str:
    """Localized prose label for a resample frequency alias."""
    return t(f"freq.{freq}")


# Horizon unit canonical keys -> approximate number of days.
_HORIZON_UNIT_DAYS = {"Day": 1, "Month": 30, "Year": 365}
# Canonical horizon unit -> translation key.
_HORIZON_UNIT_TKEY = {"Day": "unit.day", "Month": "unit.month", "Year": "unit.year"}


def _header() -> None:
    """Module-page header: clickable NUCLEUS brand (Home) + language switcher.

    The NUCLEUS logo/wordmark acts as the single Home control back to the
    module selector. It does not touch the login session, so navigating never
    logs the user out.
    """
    _inject_css()
    _header_css()

    # Compact capsule language switcher, fixed to the top-right corner
    # (styled by _lang_pill_css to match the module selector).
    with st.container(key="lang_header"):
        options = ["EN", "ID"]
        current = get_lang()
        choice = st.selectbox(
            t("lang.label"), options, index=options.index(current),
            key="lang_select", label_visibility="collapsed",
        )
        set_lang(choice)

    # Clickable NUCLEUS brand (Home). The logo image sits behind a transparent,
    # full-size button so the whole brand acts as a Home control.
    with st.container(key="brand_home"):
        st.markdown(
            f"""
            <div class="brand-row">
              <img src="{_logo_data_uri()}" width="44" height="44"
                   alt="NUCLEUS logo"/>
              <span class="brand-word">NUCLEUS</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("NUCLEUS", key="home_brand_btn",
                     help=t("nav.home"), use_container_width=True):
            _go_home()

    st.caption(t("app.tagline"))


def _header_css() -> None:
    """Style the clickable brand: overlay the Home button on the logo/wordmark."""
    st.markdown(
        """
        <style>
          /* Constrain the clickable brand to its own width (not full page). */
          .st-key-brand_home { width: fit-content; max-width: 320px; }
          /* Brand visual row. */
          .st-key-brand_home .brand-row {
              display: flex; align-items: center; gap: 12px;
              pointer-events: none; margin: 0 0 -46px 0; position: relative;
              z-index: 1;
          }
          .st-key-brand_home .brand-word {
              font-size: 2.1rem; font-weight: 800; line-height: 1;
              letter-spacing: -0.5px;
          }
          /* The Home button sits on top but is made invisible — only its hit
             area remains, turning the whole brand into a Home link. */
          .st-key-brand_home .stButton button {
              opacity: 0; height: 48px; position: relative; z-index: 2;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Steps-per-day for each resample frequency, used to turn a horizon in days
# into the number of forecast steps at the data's granularity.
_STEPS_PER_DAY = {"min": 1440, "h": 24, "D": 1, "W": 1 / 7, "MS": 1 / 30}

# A small qualitative palette for multi-series charts.
_PALETTE = ["#2563eb", "#ea580c", "#16a34a", "#9333ea", "#dc2626",
            "#0891b2", "#ca8a04", "#db2777", "#4f46e5", "#059669"]


def _days_to_steps(horizon_days: int, freq: str) -> int:
    """Convert a horizon expressed in days to forecast steps at `freq`."""
    steps = int(round(horizon_days * _STEPS_PER_DAY.get(freq, 1)))
    return max(steps, 1)


def _raw_timestamps(raw, detection):
    """Parsed, sorted timestamps from the raw dataframe (handles YYYYMMDD)."""
    ts = data_loader.parse_timestamps(raw[detection.timestamp_column]).dropna()
    return ts.sort_values()


def raw_ts_min(raw, detection):
    return _raw_timestamps(raw, detection).min().date()


def raw_ts_max(raw, detection):
    return _raw_timestamps(raw, detection).max().date()


def _combo_label(device: str, interface: str, metric: str,
                 has_interfaces: bool) -> str:
    metric_label = metric.replace("_", " ")
    if has_interfaces and interface and interface != data_loader.NO_INTERFACE:
        return f"{device} · {interface} · {metric_label}"
    return f"{device} · {metric_label}"


def _selected_combos(df, devices, interfaces, metrics) -> list:
    """Keep only device/interface/metric combinations that actually exist."""
    sub = df[df["Device_Name"].isin(devices) & df["Metric_Name"].isin(metrics)]
    if interfaces:
        sub = sub[sub["Interface"].isin(interfaces)]
    combos = (
        sub[["Device_Name", "Interface", "Metric_Name"]]
        .drop_duplicates()
        .itertuples(index=False, name=None)
    )
    return sorted(combos)


def _primary_result(results: list) -> dict:
    """Pick the headline series: the one with the highest predicted peak."""
    return max(results, key=lambda r: r["peak"])


def _kpi_cards_multi(results: list) -> None:
    c1, c2, c3 = st.columns(3)
    primary = _primary_result(results)
    u = primary["unit"] or ""
    # Current usage of the primary series.
    c1.metric(t("kpi.current", name=primary["label"].split(" · ")[0]),
              f"{primary['current']:.4g}{u}")
    # Highest predicted peak across the whole selection.
    peak_r = max(results, key=lambda r: r["peak"])
    c2.metric(t("kpi.peak"), f"{peak_r['peak']:.4g}{peak_r['unit'] or ''}")
    # Projected change of the primary series over the horizon.
    delta = primary["peak"] - primary["current"]
    pct = (delta / primary["current"] * 100.0) if primary["current"] else 0.0
    c3.metric(t("kpi.change"), f"{delta:+.4g}{u}", delta=f"{pct:+.1f}%")


def _chart_multi(results: list, horizon_label: str) -> go.Figure:
    fig = go.Figure()
    single = len(results) == 1
    for i, r in enumerate(results):
        color = _PALETTE[i % len(_PALETTE)]
        res = r["result"]
        hist_lbl, fc_lbl = t("chart.history"), t("chart.forecast")
        # Historical (solid).
        fig.add_trace(go.Scatter(
            x=res.history.index, y=res.history.values, mode="lines",
            name=f"{r['label']} — {hist_lbl}",
            legendgroup=r["label"], line=dict(color=color),
        ))
        # Forecast (dashed).
        fig.add_trace(go.Scatter(
            x=res.forecast.index, y=res.forecast.values, mode="lines",
            name=f"{r['label']} — {fc_lbl}",
            legendgroup=r["label"], line=dict(color=color, dash="dash"),
        ))
        # Projection band only when a single series is shown (keeps it readable).
        if single:
            fig.add_trace(go.Scatter(
                x=list(res.upper.index) + list(res.lower.index[::-1]),
                y=list(res.upper.values) + list(res.lower.values[::-1]),
                fill="toself", fillcolor="rgba(234,88,12,0.15)",
                line=dict(color="rgba(0,0,0,0)"), name=t("chart.band"),
                hoverinfo="skip",
            ))
    title = (results[0]["label"] if single
             else t("chart.multi_title", n=len(results)))
    # Legend below the plot so it never overlaps the title; generous top margin
    # keeps the title on its own line. More series => a bit more bottom room.
    bottom = 70 + min(len(results), 6) * 10
    fig.update_layout(
        title=dict(
            text=f"{title}  ·  {t('chart.title_suffix', horizon=horizon_label)}",
            x=0.0, xanchor="left", y=0.97, yanchor="top",
            font=dict(size=16),
        ),
        xaxis_title=t("chart.x"), yaxis_title=t("chart.y"),
        height=520, hovermode="x unified",
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center",
                    yanchor="top"),
        margin=dict(t=60, b=bottom, l=50, r=30),
    )
    return fig


# A sheet/grid icon (1000x1000 box): frame, filled header row, 2 column and
# 2 row dividers. Uses even-odd filling so the frame is hollow.
_EXCEL_ICON_PATH = (
    "M100,100H900V900H100Z M170,170V830H830V170Z "      # frame (outer minus hole)
    "M170,170H830V300H170Z "                            # header row
    "M385,300H445V830H385Z M555,300H615V830H555Z "      # column dividers
    "M170,470H830V530H170Z M170,650H830V710H170Z"       # row dividers
)
_EXPORT_TITLE = "Export to Excel"
# Plotly custom modebar buttons need a JavaScript ``click`` function, and
# Plotly throws ("must provide button 'click' function") if it is missing.
# Streamlit passes the chart config as JSON, so a Python
# ``modeBarButtonsToAdd`` entry cannot carry that function and would break the
# chart. Instead this script, run in a zero-height same-origin iframe, adds the
# button to the chart's own modebar with Plotly's markup (``modebar-btn`` +
# ``data-title``), so it gets the same dim-grey icon, hover highlight and
# tooltip. It sits first, left of the camera, and clicks the hidden download
# button. A MutationObserver re-adds it when Plotly rebuilds the modebar.
_EXPORT_BRIDGE_JS = """
<script>
(function () {
  var P = window.parent, D = P.document;
  var SCOPE = '.st-key-forecast_chart';
  var TITLE = '__TITLE__';
  var ICON = '__ICON__';
  if (P.__nucleusExport) P.__nucleusExport.disconnect();
  function exportNow(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    var dl = D.querySelector('.st-key-export_excel button, .st-key-export_excel a');
    if (dl) dl.click();
  }
  function colors(bar) {
    // Plotly 2.x colours its icons from JS using layout.modebar.color and
    // .activecolor (no CSS rule), so read the same values from the chart.
    var gd = bar.closest('.js-plotly-plot');
    var mb = (gd && gd._fullLayout && gd._fullLayout.modebar) || {};
    return {rest: mb.color || 'rgba(68, 68, 68, 0.3)',
            active: mb.activecolor || 'rgba(68, 68, 68, 0.7)'};
  }
  function makeButton(bar) {
    var group = D.createElement('div');
    group.className = 'modebar-group nucleus-export-group';
    var btn = D.createElement('button');
    btn.type = 'button';
    btn.setAttribute('rel', 'tooltip');
    btn.className = 'modebar-btn';
    btn.setAttribute('data-title', TITLE);
    btn.setAttribute('aria-label', TITLE);
    btn.setAttribute('data-gravity', 'n');
    btn.innerHTML = '<svg viewBox="0 0 1000 1000" class="icon" height="1em" width="1em">'
      + '<path fill-rule="evenodd" d="' + ICON + '"></path></svg>';
    var path = btn.querySelector('path');
    function paint(active) { path.style.fill = colors(bar)[active ? 'active' : 'rest']; }
    btn.addEventListener('mouseenter', function () { paint(true); });
    btn.addEventListener('mouseleave', function () { paint(false); });
    btn.addEventListener('click', exportNow);
    paint(false);
    group.appendChild(btn);
    return group;
  }
  function place() {
    D.querySelectorAll(SCOPE + ' .modebar').forEach(function (bar) {
      var group = bar.querySelector('.nucleus-export-group');
      if (!group) group = makeButton(bar);
      if (bar.firstElementChild !== group) bar.insertBefore(group, bar.firstElementChild);
    });
  }
  var observer = new MutationObserver(place);
  observer.observe(D.body, {childList: true, subtree: true});
  P.__nucleusExport = observer;
  place();
})();
</script>
""".replace("__TITLE__", _EXPORT_TITLE).replace("__ICON__", _EXCEL_ICON_PATH)


def _export_excel_button(results: list, settings: dict,
                         has_interfaces: bool) -> None:
    """Download button for the active forecast (history + forecast, .xlsx).

    The workbook is rebuilt only when the series or settings change; between
    reruns the bytes are reused from the session so a rerun stays cheap.
    """
    signature = (
        tuple(sorted((k, str(v)) for k, v in settings.items())),
        tuple((r["label"], len(r["series"]), str(r["series"].index[-1]),
               float(r["series"].iloc[-1]), r["result"].method,
               len(r["result"].forecast), float(r["peak"])) for r in results),
    )
    cached = st.session_state.get("_flt_xlsx_cache")
    if not cached or cached[0] != signature:
        cached = (signature,
                  excel_export.build_workbook(results, settings, has_interfaces))
        st.session_state["_flt_xlsx_cache"] = cached
    # The Plotly toolbar button clicks this download button. It is kept in the
    # DOM (so Streamlit can serve the file) but is not visible.
    with st.container(key="export_excel_host"):
        st.download_button(
            t("export.excel"), data=cached[1],
            file_name=excel_export.file_name(settings["stream"]),
            mime=excel_export.MIME, key="export_excel",
        )
        st.markdown(
            "<style>.st-key-export_excel_host{position:absolute !important;"
            "width:0 !important;height:0 !important;overflow:hidden !important;"
            "opacity:0 !important;pointer-events:none !important;"
            "margin:0 !important;}</style>",
            unsafe_allow_html=True)
        components.html(_EXPORT_BRIDGE_JS, height=0)


def _results_table(results: list) -> pd.DataFrame:
    rows = []
    for r in results:
        rows.append({
            t("table.device"): r["device"],
            t("table.interface"): r["interface"],
            t("table.metric"): r["metric"],
            t("table.unit"): r["unit"],
            t("table.current"): round(r["current"], 4),
            t("table.peak"): round(r["peak"], 4),
            t("table.method"): r["result"].method,
        })
    return pd.DataFrame(rows)


def _analytics_css() -> None:
    """Apple Liquid Glass sliding tab bar for the Analytics stream selector."""
    st.markdown(
        "<style>" + _glass_tabs_css("stream_selector", 3, "700px") + "</style>",
        unsafe_allow_html=True,
    )


def _analytics_dashboard() -> None:
    """Analytics module: a 3-stream workspace (Compute / Network / Facility).

    A segmented stream selector sits at the top. The Network stream runs the
    full NUCLEUS capacity-forecasting engine (the reference module); Compute and
    Facility ingest uploads into their own dynamic SQLite tables and preview
    them. All uploads map file columns straight into per-stream tables.
    """
    _header()

    _analytics_css()

    # Stream selector styled as an Apple Liquid Glass segmented slider,
    # centered neatly under the header.
    stream_labels = {
        t("stream.compute"): "compute",
        t("stream.network"): "network",
        t("stream.facility"): "facility",
    }
    labels = list(stream_labels.keys())
    # Land directly in the main Analytics portal (Network stream) — no
    # intermediate "pick a stream" gate. The selector still lets the user
    # switch between streams at any time.
    network_label = next(k for k, v in stream_labels.items() if v == "network")
    with st.container(key="stream_selector"):
        picked = st.segmented_control(
            t("stream.label"), labels, default=network_label,
            key="stream_select", label_visibility="collapsed",
        )

    # Default to the Network stream if the control is momentarily cleared.
    stream = stream_labels.get(picked, "network")

    if stream == "network":
        _network_stream()
    else:
        _generic_stream(stream)


def _render_sync_result(outcome) -> None:
    """Show what an upload did to the database (new / updated / identical)."""
    if not isinstance(outcome, analytics_db.UpsertResult):
        st.error(t("stream.ingest.error", err=str(outcome)))
        return
    r = outcome
    if r.mode == "created":
        st.success(t("stream.sync.created", table=r.table,
                     inserted=r.inserted, cols=len(r.columns)))
    elif r.mode == "replaced":
        st.success(t("stream.sync.replaced", table=r.table, rows=r.inserted))
    else:
        st.success(t("stream.sync.ok", table=r.table, inserted=r.inserted,
                     updated=r.updated, unchanged=r.unchanged))
    if r.mode in ("upsert", "created") and r.time_col:
        st.caption(t("stream.sync.keys", keys=" + ".join(r.key_cols)))
    elif r.mode in ("dedupe", "created", "replaced") and not r.time_col:
        st.caption(t("stream.sync.keys.none"))
    if r.added_columns:
        st.caption(t("stream.sync.newcols", cols=", ".join(r.added_columns)))
    if r.duplicates_in_file:
        st.caption(t("stream.sync.dups", n=r.duplicates_in_file))
    if r.skipped:
        st.warning(t("stream.sync.skipped", n=r.skipped))


def _sync_upload_to_db(stream: str, upload) -> None:
    """Upsert an uploaded file into the stream's SQLite table and report it.

    Rows are keyed on the time column plus identifier columns: new keys are
    inserted, changed values are updated, identical rows are left alone. The
    sync runs once per distinct file (name + content hash). Streamlit reruns the
    script on every interaction, and re-syncing the same file each time would
    replace the first, informative result with "0 new, N unchanged".
    """
    sig_key, res_key = f"_sync_sig_{stream}", f"_sync_res_{stream}"
    if upload is None:
        st.session_state.pop(sig_key, None)
        st.session_state.pop(res_key, None)
        return
    payload = upload.getvalue()
    sig = (upload.name, hashlib.sha1(payload).hexdigest())
    if st.session_state.get(sig_key) != sig:
        try:
            df = analytics_db.read_upload(payload, upload.name)
            outcome = _adb().upsert(stream, df)
        except ValueError as exc:
            outcome = str(exc)
        except sqlite3.Error as exc:
            outcome = f"database: {exc}"
        st.session_state[sig_key] = sig
        st.session_state[res_key] = outcome
    _render_sync_result(st.session_state[res_key])


def _pick_data_source(has_upload: bool, sync_ok: bool, has_db: bool,
                      allow_sample: bool) -> str:
    """Decide which data feeds the Network analysis.

    1. ``file``   - an upload that could not be saved, so the file itself is used;
    2. ``db``     - everything saved so far, including the latest upload;
    3. ``sample`` - demonstration data while the repository is still empty, only
                    when the Settings data-source preference allows it;
    4. ``none``   - nothing to analyze yet (the UI shows an empty state).
    """
    if has_upload and not sync_ok:
        return "file"
    if has_db:
        return "db"
    if has_upload:
        return "file"
    return "sample" if allow_sample else "none"


def _model_optimization_message(result, label: str, lang: str):
    """Corporate wording for the model selection (MAPE), or None if unscored.

    Auto (Best Fit) reports the winner and the full MAPE ranking; a manually
    chosen model reports its own backtest MAPE.
    """
    meta = result.meta or {}
    prefix = f"**{label}** — " if label else ""
    scores = meta.get("auto_scores")
    if scores:
        ranking = ", ".join(
            t("forecast.opt.item", model=model,
              mape=insight_report.format_pct(score, lang))
            for model, score in sorted(scores.items(), key=lambda kv: kv[1]))
        best = meta.get("auto_choice") or min(scores, key=scores.get)
        return t("forecast.opt", prefix=prefix, model=best,
                 mape=insight_report.format_pct(scores[best], lang),
                 ranking=ranking)
    mape = meta.get("backtest_mape")
    if mape is not None:
        return t("forecast.opt.manual", prefix=prefix,
                 model=meta.get("model_used") or result.method,
                 mape=insight_report.format_pct(mape, lang))
    return None


# Fixed (untranslated) accessible label shared by the sidebar file uploaders.
_UPLOADER_LABEL = "Upload file"

# Session keys that remember sidebar choices across a language switch or a
# change of dependent options. They are cleared on navigation and logout, so a
# fresh visit to Analytics always starts with empty filters.
_FILTER_STATE = "_flt_"


def _reset_filter_state() -> None:
    for key in [k for k in st.session_state if str(k).startswith(_FILTER_STATE)]:
        del st.session_state[key]


def _keep_multiselect(label: str, options: list, name: str, help=None) -> list:
    """A multiselect whose still-valid choices survive a rebuild.

    With a ``key`` Streamlit identifies the widget by its key and options (not
    its translated label), so switching language keeps the choice. When the
    options themselves change, e.g. adding a device changes the Interface list,
    Streamlit rebuilds the widget; the previous choices that are still valid
    are passed as its default so they are not lost.
    """
    state_key = f"{_FILTER_STATE}{name}"
    previous = [v for v in st.session_state.get(state_key, []) if v in options]
    picked = st.multiselect(label, options, default=previous,
                            key=f"net_{name}", help=help)
    st.session_state[state_key] = list(picked)
    return picked


def _keep_selectbox(label: str, keys: list, fmt, name: str, help=None,
                    container=None):
    """A selectbox over canonical ``keys`` shown through ``fmt`` (translation).

    The option texts are translated, and Streamlit includes them in the
    widget's identity, so the widget is rebuilt whenever the language changes.
    The canonical choice is therefore remembered separately and used as the
    initial index. Returns the canonical key.
    """
    state_key = f"{_FILTER_STATE}{name}"
    saved = st.session_state.get(state_key)
    shown = [fmt(k) for k in keys]
    picked = (container or st).selectbox(
        label, shown, index=keys.index(saved) if saved in keys else 0,
        key=f"net_{name}", help=help)
    chosen = keys[shown.index(picked)]
    st.session_state[state_key] = chosen
    return chosen


def _count_label(kind: str, n: int) -> str:
    """'1 device' / '56 devices' / '2 core metrics' in the active language."""
    return t(f"count.{kind}.{'one' if n == 1 else 'many'}",
             n=insight_report.format_int(n, get_lang()))


def _persistence_note(stream: str, stored: pd.DataFrame, latest=None,
                      data_source: str = "") -> None:
    """Status line: how much history the local database holds for this stream."""
    lang = get_lang()
    if stored.empty:
        note = t("stream.persist.empty")
        if data_source == "sample":
            note += " " + t("stream.persist.demo")
        st.caption(note)
        return
    # Only the Network stream has a forecasting engine behind it.
    base = "stream.persist.loaded" if stream == "network" else "stream.persist.stored"
    rows = insight_report.format_int(len(stored), lang)
    table = analytics_db.table_name(stream)
    if latest is not None:
        st.caption(t(base, rows=rows, table=table,
                     date=insight_report.format_date(latest, lang)))
    else:
        st.caption(t(base + ".nodate", rows=rows, table=table))


def _stream_uploader_sidebar(stream: str) -> None:
    """Stream upload for Compute / Facility, rendered in the left sidebar.

    The file is upserted into the stream's dynamic SQLite table right away
    (see ``_sync_upload_to_db``) and the result is summarized below the widget.
    """
    if not _can(auth.PERM_UPLOAD_FILE):
        return
    # The title and tooltip are translated, so they live outside the widget:
    # a file_uploader's identity includes its label and help, and a translated
    # label would drop the uploaded file when the language changes.
    st.markdown(f"**{t('stream.upload')}**", help=t("stream.upload.help"))
    up = st.file_uploader(
        _UPLOADER_LABEL, type=["csv", "xlsx", "xls"],
        key=f"stream_upload_{stream}", label_visibility="collapsed",
    )
    _sync_upload_to_db(stream, up)
    st.divider()


def _generic_stream(stream: str) -> None:
    """Compute / Facility streams: show stored SQLite data (preview module)."""
    with st.sidebar:
        st.header(t(f"stream.{stream}"))
        _stream_uploader_sidebar(stream)

    st.subheader(t(f"stream.{stream}"))
    st.info(t("stream.placeholder"))

    stored, latest = _stored_state(stream)
    _persistence_note(stream, stored, latest)
    if stored.empty:
        st.markdown(t("stream.empty"))
        return
    st.dataframe(stored, use_container_width=True, hide_index=True)


def _network_stream() -> None:
    """The NUCLEUS capacity-forecasting dashboard (the Network stream)."""
    # Role capabilities for this module.
    can_upload = _can(auth.PERM_UPLOAD_FILE)
    read_only = not _can(auth.PERM_RUN_FORECAST)

    # Read-only roles (e.g. Viewer) get a banner; they analyze the saved data.
    if read_only:
        st.info(t("access.readonly"))

    # ----------------------------- Sidebar ------------------------------- #
    with st.sidebar:
        st.header(t("sidebar.settings"))
        # Single uploader: it BOTH feeds the forecasting analysis AND saves the
        # uploaded data straight into this stream's SQLite table.
        uploaded = None
        if can_upload:
            # The file is upserted into the stream's SQLite table (feedback is
            # shown right under the widget).
            # Translated title/tooltip sit outside the widget (see
            # _stream_uploader_sidebar) so the uploaded file survives a
            # language switch.
            st.markdown(f"**{t('sidebar.upload')}**",
                        help=t("stream.upload.help"))
            uploaded = st.file_uploader(
                _UPLOADER_LABEL, type=["csv", "xlsx", "xls"],
                key="net_upload", label_visibility="collapsed",
            )
            _sync_upload_to_db("network", uploaded)
        # Read after the sync above so a fresh upload is already included.
        stored, latest = _stored_state("network")

    file_bytes = uploaded.getvalue() if uploaded is not None else None
    has_db = not stored.empty

    # Which data feeds the analysis, in priority order:
    #   1. file     - an upload that could not be saved to the database
    #   2. database - everything saved so far, including the latest upload
    #   3. sample   - demonstration data while the repository is empty, only if
    #                 Settings > Data allows it
    sync_ok = isinstance(st.session_state.get("_sync_res_network"),
                         analytics_db.UpsertResult)
    data_source = _pick_data_source(uploaded is not None, sync_ok, has_db,
                                    _default_use_sample())

    _persistence_note("network", stored, latest, data_source)

    if data_source == "none":
        st.info(t("stream.empty"))
        st.stop()

    # ---------------------- Step 1: analyze the data -------------------- #
    try:
        if data_source == "db":
            raw, detection = _analyze_frame(stored)
        else:
            raw, detection = _analyze(file_bytes, data_source == "sample")
    except ValueError as exc:
        st.error(f"❌ {exc}")
        st.stop()
    except Exception as exc:  # noqa: BLE001
        st.error(t("error.read", err=exc))
        st.stop()

    if not detection.ok:
        st.error(f"❌ {detection.error}")
        st.markdown(t("detect.unreadable"))
        st.write(list(raw.columns))
        st.dataframe(raw.head(10), use_container_width=True)
        st.stop()

    # Executive telemetry summary: what NUCLEUS evaluated and which metrics it
    # detected, before the forecast runs.
    lang = get_lang()
    st.success(t("detect.summary",
                 devices=_count_label("device", len(detection.devices)),
                 metrics=_count_label("metric", len(detection.metrics))))
    n_metrics = len(detection.metrics)
    st.info(t("detect.metrics.found.one" if n_metrics == 1
              else "detect.metrics.found", n=n_metrics,
              names=insight_report.join_names(detection.metrics, lang)))
    for w in detection.warnings:
        # The wide-format note is replaced by the metrics summary above.
        if not w.startswith("Wide format detected"):
            st.info(f"ℹ️ {w}")

    # Collapsed by default (also after a refresh) to keep the page uncluttered.
    with st.expander(t("detect.expander"), expanded=False):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**{t('detect.devices')}**")
        c1.write(detection.devices)
        c2.markdown(f"**{t('detect.interfaces')}**")
        c2.write(detection.interfaces)
        c3.markdown(f"**{t('detect.metrics')}**")
        c3.write(detection.metrics)
        st.markdown(f"**{t('detect.mapping')}**")
        st.json({k: v for k, v in detection.column_mapping.items()})

    # ---------------------- Granularity (dynamic + auto + custom) ------- #
    suggested = data_loader.suggest_frequency(raw, detection)
    gran_keys = data_loader.granularity_options(raw, detection) + ["Custom Range"]
    with st.sidebar:
        gran_label = _keep_selectbox(
            t("sidebar.granularity"), gran_keys,
            lambda k: t(f"gran.{k}"), "granularity",
            help=t("sidebar.granularity.help", suggested=_freq_label(suggested)),
        )

    custom_range = None
    if gran_label == "Custom Range":
        # Custom range still resamples at the auto-detected granularity.
        freq = suggested
        with st.sidebar:
            data_min = raw_ts_min(raw, detection)
            data_max = raw_ts_max(raw, detection)
            picked = st.date_input(
                t("sidebar.date_range"),
                value=(data_min, data_max),
                min_value=data_min, max_value=data_max,
                help=t("sidebar.date_range.help"),
                key="net_date_range",
            )
        # st.date_input returns a tuple once both ends are chosen.
        if isinstance(picked, (tuple, list)) and len(picked) == 2:
            custom_range = (pd.Timestamp(picked[0]),
                            pd.Timestamp(picked[1]) + pd.Timedelta(days=1)
                            - pd.Timedelta(seconds=1))
        else:
            st.info(t("gran.custom.need_both"))
            st.stop()
        st.caption(t("gran.custom.caption", freq=_freq_label(freq),
                     start=picked[0], end=picked[1]))
    else:
        freq = (data_loader.FREQ_OPTIONS.get(gran_label) if gran_label != "Auto"
                else None) or suggested
        if gran_label == "Auto":
            st.caption(t("gran.auto.caption", freq=_freq_label(freq)))

    # ---------------------- Step 2: clean + aggregate ------------------- #
    try:
        if data_source == "db":
            df = _clean_frame(stored, freq)
        else:
            df = _clean(file_bytes, data_source == "sample", freq)
    except ValueError as exc:
        st.error(f"❌ {exc}")
        st.stop()

    # Apply the custom date filter to the cleaned history, if any.
    if custom_range is not None:
        start, end = custom_range
        df = df[(df["Timestamp"] >= start) & (df["Timestamp"] <= end)]
        if df.empty:
            st.error(t("error.no_range_data"))
            st.stop()

    with st.expander(t("dataset.summary")):
        st.dataframe(data_loader.profile_dataframe(df, lang=get_lang()),
                     use_container_width=True)

    all_devices = sorted(df["Device_Name"].unique())
    with st.sidebar:
        # The filters start empty on first load and after a refresh: nothing is
        # pre-selected, and the forecast only runs once the user has actively
        # chosen what to analyze (see the guidance messages below).
        # All widgets below have a stable ``key`` (see _keep_multiselect /
        # _keep_selectbox), so switching language does not reset them.
        sel_devices = _keep_multiselect(
            t("sidebar.device"), all_devices, "device",
            help=t("sidebar.device.help"))
        iface_choices = data_loader.interfaces_for(df, sel_devices)
        has_interfaces = iface_choices != [data_loader.NO_INTERFACE]
        sel_interfaces = _keep_multiselect(
            t("sidebar.interface"), iface_choices, "interface",
            help=t("sidebar.interface.help"))
        metric_choices = data_loader.metrics_for(df, sel_devices, sel_interfaces)
        sel_metrics = _keep_multiselect(
            t("sidebar.metric"), metric_choices, "metric",
            help=t("sidebar.metric.help"))

        st.markdown(f"**{t('sidebar.horizon')}**")
        hc1, hc2 = st.columns([2, 2])
        horizon_n = hc1.number_input(t("sidebar.horizon.amount"),
                                     min_value=1, value=30, step=1,
                                     key="net_horizon_amount")
        horizon_unit = _keep_selectbox(
            t("sidebar.horizon.unit"), list(_HORIZON_UNIT_TKEY),
            lambda k: t(_HORIZON_UNIT_TKEY[k]), "horizon_unit", container=hc2)
        unit_pick = t(_HORIZON_UNIT_TKEY[horizon_unit])

        # Method list and default are governed by the Settings > Forecasting
        # configuration (enabled models + default model).
        _methods = _enabled_methods()
        method = st.selectbox(
            t("sidebar.method"), _methods,
            index=_methods.index(_default_method())
            if _default_method() in _methods else 0,
            key="net_method",
        )

    lang = get_lang()

    if not sel_devices or not sel_metrics:
        st.info(t("forecast.pick_prompt"))
        st.stop()
    # An empty Interface filter would mean "every interface of the device",
    # which can start dozens of forecasts at once. When the data has an
    # interface dimension, ask for an explicit choice instead.
    if has_interfaces and not sel_interfaces:
        st.info(t("forecast.pick_interface_prompt"))
        st.stop()

    # Convert the custom horizon to days, then to steps at the chosen frequency.
    horizon_days = int(horizon_n) * _HORIZON_UNIT_DAYS[horizon_unit]
    steps = _days_to_steps(horizon_days, freq)
    horizon_label = f"{int(horizon_n)} {unit_pick}"

    # Build the list of (device, interface, metric) combinations to forecast.
    combos = _selected_combos(df, sel_devices, sel_interfaces, sel_metrics)

    # ---------------------------- Forecast ------------------------------- #
    results = []   # list of dicts: label, series, result, current, peak
    skipped = []
    for device, interface, metric in combos:
        try:
            series = data_loader.get_series(df, device, metric, interface)
        except ValueError:
            continue
        if len(series) < forecasting.MIN_HISTORY_POINTS:
            skipped.append((device, interface, metric, len(series)))
            continue
        try:
            res = forecasting.forecast(series, steps, method, freq=freq)
        except ValueError:
            skipped.append((device, interface, metric, len(series)))
            continue
        current = float(series.iloc[-1])
        peak = float(res.forecast.max())
        results.append({
            "device": device, "interface": interface, "metric": metric,
            "label": _combo_label(device, interface, metric, has_interfaces),
            "unit": series.attrs.get("unit", ""), "series": series,
            "result": res, "current": current, "peak": peak,
        })

    if skipped:
        st.warning(t("forecast.skipped", n=len(skipped), freq=_freq_label(freq),
                     min=forecasting.MIN_HISTORY_POINTS))

    if not results:
        st.error(t("forecast.none"))
        st.stop()

    # Model optimization summary: selected algorithm and MAPE ranking, one box
    # per series (labeled when several series are analyzed).
    for r in results:
        message = _model_optimization_message(
            r["result"], r["label"] if len(results) > 1 else "", lang)
        if message:
            st.info(message)

    # Warnings raised by a model itself (e.g. a missing optional library).
    notes = {r["result"].notes for r in results if r["result"].notes}
    for note in notes:
        st.info(f"ℹ️ {note}")

    st.caption(t("forecast.caption", n=len(results), horizon=horizon_label,
                 steps=steps, freq=_freq_label(freq), method=method))

    # KPI cards: aggregate across the selection.
    _kpi_cards_multi(results)

    # Multi-series chart.
    with st.container(key="forecast_chart"):
        st.plotly_chart(
            _chart_multi(results, horizon_label),
            use_container_width=True,
        )

    # Excel export of exactly the series shown above (triggered from the
    # chart toolbar button; see _export_excel_button).
    _export_excel_button(results, {
        "stream": "Network",
        "devices": sel_devices, "interfaces": sel_interfaces,
        "metrics": sel_metrics,
        "granularity": f"{gran_label} ({t(f'freq.{freq}', 'EN')})",
        "horizon": f"{int(horizon_n)} {horizon_unit}",
        "steps": steps, "method": method,
        "date_range": (f"{custom_range[0]:%Y-%m-%d} to {custom_range[1]:%Y-%m-%d}"
                       if custom_range is not None else ""),
    }, has_interfaces)
    # ------------------------- NUCLEUS panel ----------------------------- #
    st.subheader(t("insight.header"))
    # Executive summary across every analyzed series: model and MAPE, metric
    # comparison, projection, capacity assessment and recommendation.
    facts = [
        insight_report.facts_from_forecast(
            r["device"], r["interface"], r["metric"], r["unit"], r["result"])
        for r in results
    ]
    report = insight_report.build_executive_insight(
        facts, lang=lang, horizon_label=horizon_label)
    # The box color follows the assessed risk (green / amber / red).
    {"stable": st.success, "elevated": st.warning,
     "critical": st.error}[report.severity](report.markdown)

    # Audio playback only appears when a TTS backend is available — otherwise the
    # feature is hidden silently (no warning shown).
    if nucleus_ai.tts_backend() is not None and st.button(t("insight.speak")):
        audio = nucleus_ai.synthesize_speech(report.plain, lang=lang.lower())
        if audio:
            st.audio(audio)

    # Per-series breakdown.
    with st.expander(t("insight.per_series"), expanded=len(results) > 1):
        st.dataframe(_results_table(results), use_container_width=True)


# --------------------------------------------------------------------------- #
# Governance flow: authentication, RBAC, mode selection and navigation
# --------------------------------------------------------------------------- #
# Session-state keys that drive the top-level navigation flow.
_AUTH_KEY = "authenticated"
_USER_KEY = "username"
_ROLE_KEY = "user_role"
_MODE_KEY = "mode"            # None -> selector; analytics/monitoring/settings
_LAST_ACTIVE_KEY = "last_active_time"   # datetime of the last interaction
_EXPIRED_KEY = "session_expired"        # True after an idle auto-logout


@st.cache_resource(show_spinner=False)
def _store() -> auth.UserStore:
    """Process-wide, JSON-backed user store (created/seeded on first use)."""
    return auth.UserStore()


@st.cache_resource(show_spinner=False)
def _token_registry(idle_ttl: int, version: int) -> auth.SessionTokens:
    # ``idle_ttl`` and ``version`` are cache keys: changing the timeout or the
    # class layout builds a fresh registry instead of serving a stale one.
    return auth.SessionTokens(idle_ttl=idle_ttl)
def _tokens() -> auth.SessionTokens:
    """Process-wide session-token registry shared across tabs/sessions."""
    return _token_registry(session_guard.timeout_seconds(),
                           auth.SessionTokens.VERSION)


@st.cache_resource(show_spinner=False)
def _settings() -> settings_store.SettingsStore:
    """Process-wide, JSON-backed application settings (created on first use)."""
    return settings_store.SettingsStore()


def _adb() -> analytics_db.AnalyticsDB:
    """Dynamic-schema SQLite store for the analytics streams.

    Deliberately not cached: the object only holds a file path, and a
    ``st.cache_resource`` copy would keep serving a stale instance of an old
    class definition to a running server after ``analytics_db`` changes.
    """
    return analytics_db.AnalyticsDB()


# Valid module modes that may appear in the URL (?mode=...).
_VALID_MODES = ("analytics", "monitoring", "database", "settings")


def _init_state() -> None:
    """Ensure the navigation keys exist, and restore ``mode`` from the URL.

    Auth keys live purely in ``st.session_state`` so they survive reruns.
    The active module is mirrored to the ``mode`` query param so the browser
    Back/Forward buttons and a page refresh resolve to the right module
    instead of bouncing the user back to the login screen.
    """
    st.session_state.setdefault(_AUTH_KEY, False)
    st.session_state.setdefault(_USER_KEY, "")
    st.session_state.setdefault(_ROLE_KEY, "")
    st.session_state.setdefault(_MODE_KEY, None)

    # Seed the active language from the saved system preference once per
    # session (before any widget sets it), so the configured default applies.
    if "lang_select" not in st.session_state and "_lang_seeded" not in \
            st.session_state:
        set_lang(_settings().language())
        st.session_state["_lang_seeded"] = True

    # Resume an existing session in a freshly opened tab: if this tab isn't
    # authenticated but the URL carries a valid session token, restore the
    # user from the shared token registry so no re-login is needed.
    if not st.session_state[_AUTH_KEY]:
        token = st.query_params.get("token")
        username = _tokens().username_for(token) if token else None
        resumed = False
        if username:
            user = _store().get(username)
            if user is not None and user.active:
                st.session_state[_AUTH_KEY] = True
                st.session_state[_USER_KEY] = user.username
                st.session_state[_ROLE_KEY] = user.role
                st.session_state[_LAST_ACTIVE_KEY] = datetime.now()
                _tokens().touch(token)
                resumed = True
        if token and not resumed:
            # Expired, revoked or unknown token: show the notice if it timed
            # out, and drop it from the URL so it is not retried.
            if _tokens().was_expired(token):
                st.session_state[_EXPIRED_KEY] = True
            try:
                del st.query_params["token"]
            except KeyError:
                pass

    # Reconcile session mode with the URL query param (URL is the source of
    # truth on a fresh load / Back / Forward navigation).
    url_mode = st.query_params.get("mode")
    if url_mode in _VALID_MODES:
        st.session_state[_MODE_KEY] = url_mode
    elif url_mode in (None, "", "home"):
        st.session_state[_MODE_KEY] = None


def _current_mode():
    return st.session_state.get(_MODE_KEY)


def _go(mode) -> None:
    """Navigate to ``mode`` (a module id or None for the selector) + update URL."""
    st.session_state[_MODE_KEY] = mode
    _reset_filter_state()    # a new visit to a module starts with empty filters
    if mode in _VALID_MODES:
        st.query_params["mode"] = mode
    else:
        # Clear the param for the Home / selector view.
        try:
            del st.query_params["mode"]
        except KeyError:
            pass
    st.rerun()


def _go_home() -> None:
    """Return to the Module Selector without touching the login session."""
    _go(None)


def _current_role() -> str:
    return st.session_state.get(_ROLE_KEY, "")


def _can(permission: str) -> bool:
    """True if the logged-in user's role grants ``permission``."""
    return auth.has_permission(_current_role(), permission)


def _role_label(role: str) -> str:
    """Localized display label for a role id."""
    return t(f"role.{role}") if role else ""


def _portal_backdrop_css() -> str:
    """Shared CSS: the data-center SVG backdrop + Apple-style font stack.

    Used by both the login portal and the module selector so the two screens
    share an identical background and typography.
    """
    bg = _login_bg_data_uri()
    # Dark veil over the data-center SVG mesh (permanent dark theme).
    overlay = ("linear-gradient(180deg, rgba(7,9,14,0.55), "
               "rgba(17,24,39,0.75))")
    return f"""
          {_theme_vars()}

          /* Data-center SVG mesh under a dark overlay. */
          [data-testid="stAppViewContainer"] {{
              background: {overlay}, url("{bg}");
              background-size: cover;
              background-position: center;
              background-attachment: fixed;
              color: var(--nuc-text) !important;
              transition: background 0.35s ease, color 0.35s ease;
          }}
          /* Base text follows the theme on the hero screens too. */
          [data-testid="stAppViewContainer"] p,
          [data-testid="stAppViewContainer"] span,
          [data-testid="stAppViewContainer"] label,
          [data-testid="stAppViewContainer"] h1,
          [data-testid="stAppViewContainer"] h2,
          [data-testid="stAppViewContainer"] h3,
          [data-testid="stAppViewContainer"] .wordmark,
          [data-testid="stAppViewContainer"] .brand-word {{
              color: var(--nuc-text) !important;
          }}
          {_hide_chrome_css()}

          /* Clean system sans-serif stack, Apple-like. */
          html, body, [data-testid="stAppViewContainer"] {{
              font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                           "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          }}
    """


def _corner_lang_css() -> str:
    """Shared CSS: a minimal, snug language select pinned to the top-right.

    Targets the keyed container ``.st-key-lang_corner`` (Streamlit emits a
    ``st-key-<key>`` class), which is far more reliable than sibling tricks.
    """
    return """
          /* Minimal language switcher pinned to the top-right corner. */
          .st-key-lang_corner {
              position: fixed;
              top: 16px;
              right: 24px;
              width: 100px;
              z-index: 999;
          }
          .st-key-lang_corner [data-testid="stWidgetLabel"] { display: none; }

          /* Capsule shell: fixed height, content vertically centered. */
          .st-key-lang_corner [data-baseweb="select"] > div {
              display: flex !important;
              align-items: center !important;
              min-height: 36px;
              height: 36px;
              padding: 0 6px 0 12px !important;
              background: var(--nuc-glass-strong);
              border: 1px solid var(--nuc-border-strong);
              border-radius: 999px;
              font-size: 0.8rem;
          }
          /* The value row: text on the left, arrow on the right, both centered
             vertically. space-between keeps the gap balanced. */
          .st-key-lang_corner [data-baseweb="select"] > div > div:first-child {
              display: flex !important;
              align-items: center !important;
              justify-content: space-between !important;
              width: 100% !important;
              line-height: 1 !important;
              padding: 0 !important;
          }
          /* Selected value text: remove any top offset that pushes it up. */
          .st-key-lang_corner [data-baseweb="select"] [class*="SingleValue"],
          .st-key-lang_corner [data-baseweb="select"] div[aria-selected] {
              display: flex !important;
              align-items: center !important;
              line-height: 1 !important;
              padding-top: 0 !important;
              padding-bottom: 0 !important;
          }
          /* Dropdown arrow: vertically centered, no extra spacing. */
          .st-key-lang_corner [data-baseweb="select"] svg {
              display: block;
              margin: 0;
          }
    """


def _corner_language_switcher() -> None:
    """Render the compact, top-right language switcher (shared helper)."""
    with st.container(key="lang_corner"):
        options = ["EN", "ID"]
        current = get_lang()
        choice = st.selectbox(
            t("lang.label"), options, index=options.index(current),
            key="lang_select", label_visibility="collapsed",
        )
        set_lang(choice)


def _login_css() -> None:
    """Apple-style glassmorphism styling scoped to the login portal.

    A futuristic IT-monitoring SVG backdrop fills the viewport behind a dark
    overlay, and the Streamlit login form is restyled as a frosted-glass card
    with a soft floating shadow, hairline border and a capsule submit button.
    """
    st.markdown(
        f"""
        <style>
          {_portal_backdrop_css()}

          .login-shell, .login-shell * {{
              font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display",
                           "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
          }}

          /* Ambient glow behind the card so it appears to float. A capped
             max-width keeps the login form a proper, compact size regardless
             of the column width. */
          [data-testid="stForm"] {{
              position: relative;
              max-width: 420px;
              margin: 3vh auto 0 auto;
              background: var(--nuc-glass-strong);
              backdrop-filter: blur(22px);
              -webkit-backdrop-filter: blur(22px);
              border: 1px solid var(--nuc-border);
              border-radius: 24px;
              box-shadow:
                0 24px 70px var(--nuc-shadow),
                0 0 90px rgba(34, 211, 238, 0.14);
              padding: 2rem 2rem 1.5rem 2rem;
          }}
          /* Form text/labels follow the theme for contrast. */
          [data-testid="stForm"] label,
          [data-testid="stForm"] .login-brand .wordmark,
          [data-testid="stForm"] .login-brand .tagline {{
              color: var(--nuc-text) !important;
          }}

          /* Rounded, subtle input fields. */
          [data-testid="stForm"] input {{
              border-radius: 12px !important;
          }}

          /* Password field: reserve safe area on the right so typed text never
             collides with the show/hide (eye) toggle. */
          [data-testid="stForm"] [data-testid="stTextInput"] input[type="password"],
          [data-testid="stForm"] [data-testid="stTextInput"] input[type="text"] {{
              padding-right: 3rem !important;
          }}

          /* Hide the "Press Enter to submit form" hint inside the login card:
             it overlaps the eye toggle and is redundant beside the Sign In
             button. */
          [data-testid="stForm"] [data-testid="InputInstructions"],
          [data-testid="stForm"] [data-testid="stTextInputInstructions"] {{
              display: none !important;
          }}

          /* Capsule, confident submit button. */
          [data-testid="stForm"] [data-testid="stFormSubmitButton"] button {{
              border-radius: 999px;
              padding: 0.55rem 1.5rem;
              font-weight: 600;
              border: 1px solid rgba(255,255,255,0.18);
              background: linear-gradient(90deg, #0ea5e9, #6366f1);
              color: #ffffff;
          }}
          [data-testid="stForm"] [data-testid="stFormSubmitButton"] button:hover {{
              filter: brightness(1.08);
              border-color: rgba(255,255,255,0.35);
          }}

          /* Brand header inside the card. */
          .login-brand {{
              display: flex; flex-direction: column; align-items: center;
              text-align: center; gap: 8px; margin-bottom: 1.25rem;
          }}
          .login-brand .wordmark {{
              font-size: 2.1rem; font-weight: 800; line-height: 1;
              letter-spacing: -0.5px;
          }}
          .login-brand .tagline {{
              opacity: 0.72; white-space: nowrap;
              /* Scale down so the full tagline stays on one line inside the
                 capped (420px) card. */
              font-size: clamp(0.56rem, 1.9vw, 0.72rem);
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _login_page() -> None:
    """Status 1 — Apple-style glassmorphism login portal over an IT backdrop.

    No language switcher here: the portal stays clean and minimal. Language can
    be changed from the mode selector after signing in.
    """
    _login_css()

    # Center the card; its width is capped via CSS (max-width on the form).
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if st.session_state.get(_EXPIRED_KEY):
            with st.container(key="session_expired_notice"):
                st.markdown(
                    "<style>.st-key-session_expired_notice [data-testid=\"stAlert\"] "
                    "[data-testid=\"stMarkdownContainer\"]{text-align:center;"
                    "width:100%;}</style>",
                    unsafe_allow_html=True)
                st.warning(t(
                    "session.expired",
                    duration=session_guard.format_duration(
                        session_guard.timeout_seconds(), get_lang()),
                ))
        st.markdown('<div class="login-shell">', unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            # Logo + wordmark + tagline, centered at the top of the card.
            st.markdown(
                f"""
                <div class="login-brand">
                  <img src="{_logo_data_uri()}" width="64" height="64"
                       alt="NUCLEUS logo"/>
                  <div class="wordmark">NUCLEUS</div>
                  <div class="tagline">{t('login.footer')}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            username = st.text_input(t("login.username"))
            password = st.text_input(t("login.password"), type="password")
            submitted = st.form_submit_button(t("login.submit"),
                                              use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        store = _store()
        user = store.authenticate(username, password)
        if user is not None:
            st.session_state[_AUTH_KEY] = True
            st.session_state[_USER_KEY] = user.username
            st.session_state[_ROLE_KEY] = user.role
            st.session_state.pop(_EXPIRED_KEY, None)
            st.session_state[_LAST_ACTIVE_KEY] = datetime.now()
            # Issue a session token and store it in the URL so other tabs can
            # resume this session without logging in again.
            st.query_params["token"] = _tokens().issue(user.username)
            _go(None)  # land on the module selector
        else:
            with mid:
                # Distinguish a disabled account from bad credentials.
                existing = store.get(username)
                if existing is not None and not existing.active:
                    st.error(t("login.disabled"))
                else:
                    st.error(t("login.error"))


def _logout() -> None:
    # Revoke the shared session token so other tabs can't resume it.
    token = st.query_params.get("token")
    if token:
        _tokens().revoke(token)
    st.session_state[_AUTH_KEY] = False
    st.session_state[_USER_KEY] = ""
    st.session_state[_ROLE_KEY] = ""
    st.session_state[_MODE_KEY] = None
    _reset_filter_state()
    # Clear module + token from the URL so a logged-out refresh shows login.
    for param in ("mode", "token"):
        try:
            del st.query_params[param]
        except KeyError:
            pass


def _clear_session_data() -> None:
    """Drop every session key except the language seed, then restore the language."""
    lang = get_lang()
    for key in list(st.session_state.keys()):
        if key != "_lang_seeded":
            try:
                del st.session_state[key]
            except KeyError:
                pass
    set_lang(lang)


def _expire_session() -> None:
    """Log out an idle session, wipe its data and flag the expiry notice."""
    lang = get_lang()
    _logout()                      # revokes the token, clears auth + URL
    _clear_session_data()
    set_lang(lang)
    st.session_state[_EXPIRED_KEY] = True


def _enforce_idle_timeout() -> None:
    """Run first on every script execution.

    An authenticated session idle for more than the timeout is logged out.
    Otherwise the run counts as activity and refreshes ``last_active_time``
    (and the shared token's idle clock).
    """
    if not st.session_state.get(_AUTH_KEY):
        return
    now = datetime.now()
    last = st.session_state.get(_LAST_ACTIVE_KEY)
    if session_guard.is_expired(last, now):
        _expire_session()
        return
    st.session_state[_LAST_ACTIVE_KEY] = now
    token = st.query_params.get("token")
    if token:
        _tokens().touch(token)


@st.fragment(run_every=session_guard.tick_seconds())
def _idle_watchdog() -> None:
    """Invisible poller so an idle tab shows the expiry without interaction.

    It never refreshes ``last_active_time``; it only triggers a full rerun
    when the session has expired, and the guard in ``main`` does the logout.
    """
    st.markdown("<style>.st-key-idle_watchdog{display:none !important}</style>",
                unsafe_allow_html=True)
    if session_guard.is_expired(st.session_state.get(_LAST_ACTIVE_KEY),
                                datetime.now()):
        st.rerun()


def _selector_css(n_tabs: int = 2) -> None:
    """Glassmorphism styling for the module portal, matching the login card."""
    st.markdown(
        f"""
        <style>
          {_portal_backdrop_css()}
          {_corner_lang_css()}
          {_page_transition_css()}
          {_glass_tabs_css("portal_nav", max(n_tabs, 1), "800px", size="large",
                           centered=True)}

          /* Centered brand header, matching the login card proportions. */
          .sel-brand {{
              display:flex; flex-direction:column; align-items:center;
              text-align:center; gap:8px; margin:2vh 0 0.5rem 0;
          }}
          .sel-brand .wordmark {{
              font-size:2.4rem; font-weight:800; line-height:1;
              letter-spacing:-0.5px;
          }}
          .sel-brand .tagline {{
              opacity:0.72; white-space:nowrap;
              font-size:clamp(0.6rem, 1.6vw, 0.8rem);
          }}
          .sel-title {{
              text-align:center; font-weight:600;
              color: var(--nuc-text); opacity:0.9;
              margin:0.25rem 0 1.5rem 0;
          }}

          /* Capsule buttons of the bottom status bar. */
          .stButton button {{
              border-radius: 999px;
              font-weight: 600;
              border: 1px solid var(--nuc-border-strong);
          }}

          {_footer_css()}

          /* Reserve space so the bottom-fixed footer never hides content. */
          .main .block-container,
          [data-testid="stMainBlockContainer"] {{
              padding-top: 1.5rem;
              padding-bottom: 5.5rem;
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


_GLASS_TABS_TEMPLATE = """
          /* ---- Apple Liquid Glass sliding tab bar (__ROOT__) ----------------
             Built on st.segmented_control. Streamlit 1.50 renders it as a
             stButtonGroup holding a radiogroup of <button>s; the active one has
             kind="segmented_controlActive". The options have equal widths, so a
             single glass "pill" (::before) can glide from one to the next. */
          __ROOT__ { display: flex; flex-direction: column; align-items: center; }
          __ROOT__ [data-testid="stElementContainer"] {
              width: min(__WIDTH__, 94vw) !important; margin: 0 auto !important;
          }
          __ROOT__ [data-testid="stButtonGroup"] { width: 100%; }
          __ROOT__ [data-testid="stWidgetLabel"] { display: none; }

          /* The glass track. */
          __GROUP__ {
              position: relative; display: flex; flex-wrap: nowrap;
              width: 100%; gap: 0;
              padding: __PAD__; border-radius: 999px; isolation: isolate;
              background: var(--nuc-glass-strong);
              border: 1px solid var(--nuc-border-strong);
              backdrop-filter: blur(22px);
              -webkit-backdrop-filter: blur(22px);
              box-shadow: 0 14px 44px var(--nuc-shadow),
                          inset 0 1px 0 rgba(255, 255, 255, 0.08);
          }

          /* The sliding indicator: hidden until an option is active, then it
             glides (with a slight spring) to that option's slot. */
          __GROUP__::before {
              content: ""; position: absolute; z-index: 0; pointer-events: none;
              top: __PAD__; bottom: __PAD__; left: __PAD__;
              width: calc((100% - __PAD2__) / __N__);
              border-radius: 999px;
              background: linear-gradient(135deg, rgba(103, 232, 249, 0.22),
                                          rgba(99, 102, 241, 0.28));
              border: 1px solid rgba(103, 232, 249, 0.45);
              box-shadow: 0 6px 22px rgba(34, 211, 238, 0.20),
                          inset 0 1px 0 rgba(255, 255, 255, 0.20);
              opacity: 0; transform: translateX(0);
              transition: transform 0.42s cubic-bezier(0.34, 1.3, 0.5, 1),
                          opacity 0.25s ease;
          }

          /* The options sit above the indicator. */
          __GROUP__ > button {
              position: relative; z-index: 1; min-width: 0;
              /* Equal slots. A zero flex-basis does not grow inside BaseWeb's
                 button group (verified in the browser), a 1/N basis does. */
              flex: 1 1 calc(100% / __N__); margin: 0 !important;
              display: flex; align-items: center; justify-content: center;
              gap: __GAP__; white-space: nowrap; min-height: __MINH__;
              background: transparent !important; border: none !important;
              box-shadow: none !important; border-radius: 999px !important;
              color: var(--nuc-text-dim) !important; font-weight: 600;
              font-size: __FONT__;
              padding: __BTN_PAD__ !important;
              transition: color 0.25s ease, background-color 0.25s ease;
          }
          __GROUP__ > button:hover {
              color: var(--nuc-text) !important;
              background: rgba(255, 255, 255, 0.05) !important;
          }
          __GROUP__ > button[kind="segmented_controlActive"] {
              color: var(--nuc-text) !important;
              background: transparent !important;
          }
          __GROUP__ > button:focus-visible {
              outline: 2px solid rgba(103, 232, 249, 0.6);
              outline-offset: -2px;
          }
          __GROUP__ > button [data-testid="stIconEmoji"] {
              font-size: __ICON__; line-height: 1;
          }
          /* Streamlit sets its own size on the label paragraph; inherit ours. */
          __GROUP__ > button p,
          __GROUP__ > button [data-testid="stMarkdownContainer"] {
              margin: 0; font-size: inherit; line-height: 1.2;
          }

          @media (prefers-reduced-motion: reduce) {
              __GROUP__::before, __GROUP__ > button { transition: none; }
          }
"""


# Size presets for the glass tab bar. "regular" suits an in-page control (the
# Analytics stream selector); "large" is the portal's main navigation.
_TAB_SIZES = {
    "regular": {
        "PAD": "5px", "PAD2": "10px", "MINH": "2.75rem", "GAP": "0.5rem",
        "FONT": "clamp(0.85rem, 2.6vw, 1.02rem)",
        "BTN_PAD": "clamp(0.55rem, 1.8vw, 0.85rem) clamp(0.6rem, 2.4vw, 1.25rem)",
        "ICON": "1em",
    },
    "large": {
        "PAD": "8px", "PAD2": "16px", "MINH": "clamp(3.75rem, 11vw, 5.5rem)",
        "GAP": "clamp(0.5rem, 1.6vw, 0.9rem)",
        "FONT": "clamp(1.05rem, 4.2vw, 1.65rem)",
        "BTN_PAD": "clamp(0.8rem, 3vw, 1.4rem) clamp(0.8rem, 3vw, 2rem)",
        # The emoji sits in its own span (16px base), so size it from the label.
        "ICON": "calc(clamp(1.05rem, 4.2vw, 1.65rem) * 1.25)",
    },
}

# Below this viewport height a centered bar would collide with the brand
# header, so it falls back to the normal page flow.
_CENTER_MIN_HEIGHT_PX = 641


def _glass_tabs_css(scope: str, n: int, width: str = "460px",
                    size: str = "regular", centered: bool = False) -> str:
    """CSS for an Apple Liquid Glass sliding tab bar.

    ``scope`` is the key of the container wrapping the ``st.segmented_control``
    and ``n`` the number of options. One slide rule is generated per option:
    the indicator moves to ``translateX(i * 100%)`` of its own width. ``size``
    picks a preset from ``_TAB_SIZES``. With ``centered`` the bar is placed at
    the exact centre of the viewport (fixed + auto margins, no transform) on
    screens tall enough for it not to overlap the header above.
    """
    root = f".st-key-{scope}"
    group = f'{root} [data-baseweb="button-group"]'
    css = (_GLASS_TABS_TEMPLATE.replace("__ROOT__", root)
           .replace("__GROUP__", group).replace("__WIDTH__", width)
           .replace("__N__", str(n)))
    for name, value in _TAB_SIZES[size].items():
        css = css.replace(f"__{name}__", value)
    slides = "\n".join(
        f'{group}:has(> button:nth-child({i})[kind="segmented_controlActive"])'
        f"::before {{ opacity: 1; transform: translateX({(i - 1) * 100}%); }}"
        for i in range(1, n + 1))
    css += "\n" + slides
    if centered:
        css += f"""
          @media (min-height: {_CENTER_MIN_HEIGHT_PX}px) {{
              {root} {{
                  position: fixed; top: 0; right: 0; bottom: 0; left: 0;
                  margin: auto; width: min({width}, 94vw);
                  height: fit-content; z-index: 5;
              }}
              {root} [data-testid="stElementContainer"] {{
                  width: 100% !important;
              }}
          }}"""
    return css


def _page_transition_css() -> str:
    """Fade a page in when the user moves to it (portal <-> module pages).

    Every page is wrapped in a container whose key includes the page id, so
    React mounts a fresh element on navigation and the animation replays; on
    ordinary reruns the container is reused and nothing re-animates. Opacity
    only: a transform would turn the container into the containing block of the
    ``position: fixed`` footer and language pill.
    """
    return """
          [class*="st-key-page_"] { animation: nucPageIn 0.45s ease both; }
          @keyframes nucPageIn { from { opacity: 0; } to { opacity: 1; } }
          @media (prefers-reduced-motion: reduce) {
              [class*="st-key-page_"] { animation: none; }
          }
    """


# Modules offered on the portal: (tab title key, mode id, permission needed).
_PORTAL_MODULES = (
    ("selector.analytics.title", "analytics", auth.PERM_VIEW_ANALYTICS),
    ("selector.monitoring.title", "monitoring", auth.PERM_VIEW_MONITORING),
    ("selector.database.title", "database", auth.PERM_MANAGE_DATABASE),
)


def _mode_selector() -> None:
    """Status 2 — glassmorphism landing portal with a sliding tab bar."""
    _selector_css(sum(1 for _, _, perm in _PORTAL_MODULES if _can(perm)))
    _corner_language_switcher()

    # Brand header mirroring the login card (logo, wordmark, one-line tagline).
    st.markdown(
        f"""
        <div class="sel-brand">
          <img src="{_logo_data_uri()}" width="64" height="64" alt="NUCLEUS logo"/>
          <div class="wordmark">NUCLEUS</div>
          <div class="tagline">{t('login.footer')}</div>
        </div>
        <div class="sel-title">{t('selector.title')}</div>
        """,
        unsafe_allow_html=True,
    )

    # One sliding tab bar for the modules this role may open. Picking a tab
    # goes straight to the module (no intermediate "Open ..." step).
    modules = [(t(title_key), mode) for title_key, mode, perm in _PORTAL_MODULES
               if _can(perm)]
    if modules:
        by_label = dict(modules)
        with st.container(key="portal_nav"):
            picked = st.segmented_control(
                t("selector.title"), list(by_label), default=None,
                key="portal_nav_ctl", label_visibility="collapsed")
        if picked in by_label:
            _go(by_label[picked])

    _selector_footer()


def _footer_css() -> str:
    """CSS that locks the keyed footer container to the bottom of the window."""
    return """
          /* Single status bar locked to the very bottom of the viewport.
             Targets the keyed container (st-key-<key>) for reliability. */
          .st-key-selector_footer {
              position: fixed;
              left: 0;
              right: 0;
              bottom: 0;
              width: 100%;
              padding: 0.4rem 1.5rem 0.55rem 1.5rem;
              background: var(--nuc-glass-strong);
              backdrop-filter: blur(12px);
              -webkit-backdrop-filter: blur(12px);
              border-top: 1px solid var(--nuc-border);
              z-index: 998;
          }
          .st-key-selector_footer, .st-key-selector_footer * {
              color: var(--nuc-text) !important;
          }
          /* Vertically center the status text against the buttons. */
          .st-key-selector_footer [data-testid="stHorizontalBlock"] {
              align-items: center;
          }
          .st-key-selector_footer .stButton button {
              border-radius: 999px;
              font-weight: 600;
              border: 1px solid var(--nuc-border-strong);
          }
    """


def _selector_footer() -> None:
    """One bottom status bar: identity on the left, actions on the right.

    Placed inside a keyed container so CSS can fix it flush to the bottom.
    """
    with st.container(key="selector_footer"):
        is_admin = _can(auth.PERM_USER_MANAGEMENT)
        # Left: identity. Right: User Management (admin only) + Log Out.
        if is_admin:
            info_col, users_col, logout_col = st.columns([6, 1.6, 1.1])
        else:
            info_col, logout_col = st.columns([7, 1.1])
            users_col = None

        info_col.markdown(
            t("nav.signed_in_as", user=st.session_state.get(_USER_KEY, ""))
            + " · " + t("access.role_badge", role=_role_label(_current_role()))
        )
        if users_col is not None:
            if users_col.button(t("selector.users.short"),
                                use_container_width=True, key="go_settings"):
                _go("settings")
        if logout_col.button(t("nav.logout"), use_container_width=True,
                             key="logout_sel"):
            _logout()
            st.rerun()


@st.cache_data(show_spinner=False)
def _monitoring_sample() -> pd.DataFrame:
    """Static sample device-status table for the monitoring placeholder."""
    return pd.DataFrame([
        {"device": "Host-01", "status": "online", "uptime": "42d 6h",
         "cpu": 38, "mem": 61},
        {"device": "Host-02", "status": "online", "uptime": "17d 2h",
         "cpu": 54, "mem": 72},
        {"device": "Switch-A", "status": "warning", "uptime": "8d 19h",
         "cpu": 81, "mem": 66},
        {"device": "Router-Edge", "status": "online", "uptime": "123d 1h",
         "cpu": 22, "mem": 44},
        {"device": "Storage-01", "status": "offline", "uptime": "—",
         "cpu": 0, "mem": 0},
    ])


def _monitoring_dashboard() -> None:
    """Placeholder 'Monitoring' module: live device status preview."""
    _header()
    with st.sidebar:
        st.header(t("monitoring.header"))

    st.subheader(t("monitoring.header"))
    st.caption(t("monitoring.subtitle"))
    st.info(t("monitoring.coming_soon"))

    raw = _monitoring_sample()
    status_label = {
        "online": t("monitoring.status.online"),
        "warning": t("monitoring.status.warning"),
        "offline": t("monitoring.status.offline"),
    }

    # KPI cards summarizing the fleet.
    online = int((raw["status"] == "online").sum())
    alerts = int((raw["status"] != "online").sum())
    avg_cpu = raw.loc[raw["status"] != "offline", "cpu"].mean()
    k1, k2, k3 = st.columns(3)
    k1.metric(t("monitoring.kpi.online"), f"{online}/{len(raw)}")
    k2.metric(t("monitoring.kpi.alerts"), f"{alerts}")
    k3.metric(t("monitoring.kpi.avg_cpu"), f"{avg_cpu:.0f}%")

    # Localized status table.
    table = pd.DataFrame({
        t("monitoring.col.device"): raw["device"],
        t("monitoring.col.status"): raw["status"].map(status_label),
        t("monitoring.col.uptime"): raw["uptime"],
        t("monitoring.col.cpu"): raw["cpu"].map(lambda v: f"{v}%"),
        t("monitoring.col.mem"): raw["mem"].map(lambda v: f"{v}%"),
    })
    st.dataframe(table, use_container_width=True, hide_index=True)


def _role_options() -> dict:
    """Localized role label -> canonical role id, for selectboxes."""
    return {_role_label(r): r for r in auth.ROLES}


def _users_table(store: auth.UserStore) -> pd.DataFrame:
    """Localized dataframe of all users for display."""
    rows = []
    for u in store.list_users():
        rows.append({
            t("users.col.username"): u.username,
            t("users.col.full_name"): u.full_name,
            t("users.col.email"): u.email,
            t("users.col.role"): _role_label(u.role),
            t("users.col.status"): (t("users.status.active") if u.active
                                    else t("users.status.inactive")),
        })
    return pd.DataFrame(rows)


def _settings_css() -> None:
    """Apple Liquid Glass styling for the Settings page (theme-aware).

    The theme-aware canvas/typography come from ``_glass_css`` (via _header);
    here we only style the settings cards using the shared theme variables so
    they adapt to Dark/Light mode too."""
    st.markdown(
        """
        <style>
          /* Frosted-glass cards wrapping the settings content. */
          .st-key-um_table, .st-key-um_actions,
          .st-key-settings_panel_forecasting,
          .st-key-settings_panel_data,
          .st-key-settings_panel_system {
              background: var(--nuc-glass);
              backdrop-filter: blur(16px);
              -webkit-backdrop-filter: blur(16px);
              border: 1px solid var(--nuc-border);
              border-radius: 18px;
              box-shadow: 0 16px 44px var(--nuc-shadow);
              padding: 1.25rem 1.4rem;
              margin-bottom: 1.1rem;
          }
          /* Apple-style clean, rounded action buttons. */
          .st-key-um_table .stButton button,
          .st-key-um_actions .stButton button,
          .st-key-settings_panel_forecasting .stButton button,
          .st-key-settings_panel_data .stButton button,
          .st-key-settings_panel_system .stButton button,
          [data-testid="stFormSubmitButton"] button {
              border-radius: 12px;
              font-weight: 600;
              border: 1px solid var(--nuc-border-strong);
          }
          [data-testid="stFormSubmitButton"] button:hover,
          .st-key-settings_panel_forecasting .stButton button:hover,
          .st-key-settings_panel_data .stButton button:hover,
          .st-key-settings_panel_system .stButton button:hover {
              filter: brightness(1.08);
              border-color: var(--nuc-border-strong);
          }
          .st-key-um_table [data-testid="stDataFrame"] {
              background: transparent;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _settings_users_tab() -> None:
    """Tab 1 — RBAC: list, add, edit, and delete/disable users."""
    store = _store()
    role_opts = _role_options()
    role_labels = list(role_opts.keys())

    # ---- current users table (glass card) ---- #
    with st.container(key="um_table"):
        st.markdown(f"#### {t('users.table.title')}")
        st.dataframe(_users_table(store), use_container_width=True,
                     hide_index=True)

    # ---- actions (glass card with tabs) ---- #
    with st.container(key="um_actions"):
        add_tab, edit_tab, del_tab = st.tabs([
            t("users.add.title"), t("users.edit.title"),
            t("users.delete.title"),
        ])

        with add_tab:
            with st.form("add_user_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                new_username = c1.text_input(t("users.col.username"))
                new_full = c2.text_input(t("users.col.full_name"))
                c3, c4 = st.columns(2)
                new_email = c3.text_input(t("users.col.email"))
                new_role_label = c4.selectbox(t("users.col.role"), role_labels)
                c5, c6 = st.columns(2)
                new_pw = c5.text_input(t("users.field.password"),
                                       type="password")
                new_active = c6.checkbox(t("users.field.active"), value=True)
                if st.form_submit_button(t("users.btn.add"), type="primary"):
                    try:
                        store.add_user(new_username, new_full, new_email,
                                       role_opts[new_role_label], new_pw,
                                       active=new_active)
                        st.success(t("users.msg.added", user=new_username))
                        st.rerun()
                    except ValueError as exc:
                        st.error(t(f"users.err.{exc}"))

        with edit_tab:
            usernames = [u.username for u in store.list_users()]
            target = st.selectbox(t("users.select.user"), usernames,
                                  key="edit_select")
            u = store.get(target) if target else None
            if u is not None:
                with st.form("edit_user_form"):
                    c1, c2 = st.columns(2)
                    ed_full = c1.text_input(t("users.col.full_name"),
                                            value=u.full_name)
                    ed_email = c2.text_input(t("users.col.email"),
                                             value=u.email)
                    c3, c4 = st.columns(2)
                    cur_idx = list(role_opts.values()).index(u.role) \
                        if u.role in role_opts.values() else 0
                    ed_role_label = c3.selectbox(t("users.col.role"),
                                                 role_labels, index=cur_idx)
                    ed_active = c4.checkbox(t("users.field.active"),
                                            value=u.active)
                    ed_pw = st.text_input(t("users.field.password.keep"),
                                          type="password")
                    if st.form_submit_button(t("users.btn.save"),
                                             type="primary"):
                        try:
                            store.update_user(
                                target, full_name=ed_full, email=ed_email,
                                role=role_opts[ed_role_label], active=ed_active,
                                password=ed_pw or None,
                            )
                            st.success(t("users.msg.updated", user=target))
                            st.rerun()
                        except ValueError as exc:
                            st.error(t(f"users.err.{exc}"))

        with del_tab:
            usernames = [u.username for u in store.list_users()]
            target_d = st.selectbox(t("users.select.user"), usernames,
                                    key="del_select")
            u = store.get(target_d) if target_d else None
            if u is not None:
                b1, b2 = st.columns(2)
                if b1.button(t("users.btn.toggle"), use_container_width=True):
                    try:
                        store.set_active(target_d, not u.active)
                        st.success(t("users.msg.toggled", user=target_d))
                        st.rerun()
                    except ValueError as exc:
                        st.error(t(f"users.err.{exc}"))
                if b2.button(t("users.btn.delete"), use_container_width=True,
                             type="primary"):
                    try:
                        store.delete_user(target_d)
                        st.success(t("users.msg.deleted", user=target_d))
                        st.rerun()
                    except ValueError as exc:
                        st.error(t(f"users.err.{exc}"))


def _enabled_methods() -> list:
    """The forecasting methods enabled in Settings, intersected with what the
    engine actually supports right now. Falls back to all available methods."""
    available = forecasting.available_methods()
    enabled = _settings().enabled_models()
    if not enabled:
        return available
    allowed = [m for m in available if m in enabled]
    return allowed or available


def _default_method() -> str:
    """The configured default forecasting method (if still available)."""
    methods = _enabled_methods()
    default = _settings().default_model()
    return default if default in methods else methods[0]


def _default_use_sample() -> bool:
    """True when Settings prefers built-in sample data by default."""
    return _settings().data_source() == "sample"


def _theme_vars() -> str:
    """CSS custom properties for the permanent dark Apple Liquid Glass theme.

    NUCLEUS is locked to dark mode: translucent dark surfaces with blur,
    hairline borders, soft shadows and light/high-contrast text.
    """
    return """
          :root {
              --nuc-bg-1: #07090e;
              --nuc-bg-2: #111827;
              --nuc-text: #e5e7eb;
              --nuc-text-dim: rgba(229, 231, 235, 0.6);
              --nuc-glass: rgba(255, 255, 255, 0.03);
              --nuc-glass-strong: rgba(255, 255, 255, 0.06);
              --nuc-border: rgba(255, 255, 255, 0.08);
              --nuc-border-strong: rgba(255, 255, 255, 0.16);
              --nuc-shadow: rgba(0, 0, 0, 0.3);
              --nuc-accent: #67e8f9;
          }
        """


def _settings_forecasting_tab() -> None:
    """Tab 2 — default/enabled forecasting models (persisted to settings.json)."""
    cfg = _settings()
    methods = forecasting.available_methods()
    with st.container(key="settings_panel_forecasting"):
        st.markdown(f"#### {t('settings.fc.title')}")
        st.caption(t("settings.fc.desc"))
        with st.form("fc_config_form"):
            cur_default = cfg.default_model()
            default_idx = methods.index(cur_default) \
                if cur_default in methods else 0
            default_model = st.selectbox(
                t("settings.fc.default_model"), methods, index=default_idx,
                key="set_fc_default",
            )
            cur_enabled = cfg.enabled_models() or methods
            enabled = st.multiselect(
                t("settings.fc.enabled_models"), methods,
                default=[m for m in cur_enabled if m in methods] or methods,
                key="set_fc_enabled",
            )
            if st.form_submit_button(t("settings.fc.save"), type="primary"):
                chosen = enabled or methods
                # Keep the default consistent with the enabled set.
                if default_model not in chosen:
                    default_model = chosen[0]
                cfg.update_section("forecasting", {
                    "default_model": default_model,
                    "enabled_models": chosen,
                })
                st.success(t("settings.fc.saved"))


def _settings_data_tab() -> None:
    """Tab 3 — data source + retention preferences (persisted to settings.json)."""
    cfg = _settings()
    with st.container(key="settings_panel_data"):
        st.markdown(f"#### {t('settings.data.title')}")
        with st.form("data_config_form"):
            source_opts = {
                t("settings.data.source.sample"): "sample",
                t("settings.data.source.upload"): "upload",
            }
            labels = list(source_opts.keys())
            cur = cfg.data_source()
            idx = list(source_opts.values()).index(cur) if cur in \
                source_opts.values() else 0
            picked = st.selectbox(t("settings.data.source"), labels, index=idx,
                                  key="set_data_source")
            retention = st.number_input(
                t("settings.data.retention"), min_value=1, max_value=3650,
                value=cfg.retention_days(), step=1, key="set_data_retention",
            )
            if st.form_submit_button(t("settings.data.save"), type="primary"):
                cfg.update_section("data", {
                    "source": source_opts[picked],
                    "retention_days": int(retention),
                })
                st.success(t("settings.data.saved"))


def _settings_system_tab() -> None:
    """Tab 4 — system language preference (persisted to settings.json).

    NUCLEUS is permanently themed in dark Apple Liquid Glass, so there is no
    display-mode selector here.
    """
    cfg = _settings()
    with st.container(key="settings_panel_system"):
        st.markdown(f"#### {t('settings.sys.title')}")
        with st.form("system_config_form"):
            # System language.
            lang_opts = ["EN", "ID"]
            cur_lang = cfg.language() if cfg.language() in lang_opts \
                else get_lang()
            lang_pick = st.selectbox(
                t("settings.sys.language"), lang_opts,
                index=lang_opts.index(cur_lang), key="set_sys_lang",
            )
            st.caption(t("settings.sys.theme.note"))
            if st.form_submit_button(t("settings.sys.save"), type="primary"):
                cfg.update_section("system", {"language": lang_pick})
                # Apply language immediately across the app.
                set_lang(lang_pick)
                st.success(t("settings.sys.saved"))
                st.rerun()


def _settings_page() -> None:
    """Admin-only centralized Settings hub with structured tabs."""
    _header()
    _settings_css()
    with st.sidebar:
        st.header(t("settings.header"))

    st.subheader(t("settings.header"))
    st.caption(t("settings.subtitle"))

    users_tab, fc_tab, data_tab, sys_tab = st.tabs([
        t("settings.tab.users"),
        t("settings.tab.forecasting"),
        t("settings.tab.data"),
        t("settings.tab.system"),
    ])
    with users_tab:
        _settings_users_tab()
    with fc_tab:
        _settings_forecasting_tab()
    with data_tab:
        _settings_data_tab()
    with sys_tab:
        _settings_system_tab()


def main() -> None:
    """Top-level router implementing the governance flow.

    Status 1 (login) -> Status 2 (mode selector) -> Status 3 (module page).
    """
    _enforce_idle_timeout()
    _init_state()

    # Status 1: not authenticated -> login portal.
    if not st.session_state[_AUTH_KEY]:
        _login_page()
        return

    with st.container(key="idle_watchdog"):
        _idle_watchdog()

    # Status 2/3: the portal or a module page. Each page lives in a container
    # keyed by its id, so moving between pages mounts a new element and the
    # fade-in from _page_transition_css plays (ordinary reruns reuse it).
    mode = _current_mode()
    with st.container(key=f"page_{mode or 'portal'}"):
        if mode is None:
            _mode_selector()                      # Status 2: landing portal
        elif mode == "monitoring":
            _guarded(auth.PERM_VIEW_MONITORING, _monitoring_dashboard)
        elif mode == "database":
            _guarded(auth.PERM_MANAGE_DATABASE, _database_page)
        elif mode == "settings":
            _guarded(auth.PERM_USER_MANAGEMENT, _settings_page)
        else:  # default to the existing analytics dashboard
            _guarded(auth.PERM_VIEW_ANALYTICS, _analytics_dashboard)


# --------------------------------------------------------------------------- #
# Database module (Administrator only)
# --------------------------------------------------------------------------- #
_DB_FLASH = "_db_flash"            # (kind, message) shown after a rerun
_DB_RESULT = "_db_query_result"    # last console result / error
_DB_UPLOAD_N = "_db_upload_n"      # bump to clear the import uploader


def _dba() -> database_admin.DatabaseAdmin:
    """Admin view of the same SQLite file the Analytics module uses."""
    return database_admin.DatabaseAdmin(_adb().path)


def _db_error_text(exc: Exception) -> str:
    code = str(exc)
    known = {"not_sqlite", "integrity", "missing", "unknown_table",
             "empty_query", "timeout"}
    if code in known:
        return t(f"db.err.{code}", secs=int(database_admin.QUERY_TIMEOUT_SECONDS))
    return t("db.err.generic", err=code)


def _db_done(kind: str, message: str) -> None:
    """Remember a result message, then rerun so every tab shows fresh data."""
    st.session_state[_DB_FLASH] = (kind, message)
    st.session_state.pop("_db_export_cache", None)
    st.rerun()


def _database_css() -> None:
    panels = ", ".join(f".st-key-db_panel_{p}" for p in
                       ("browser", "console", "manage_table", "manage_reset",
                        "export", "import"))
    st.markdown(
        f"""
        <style>
          {panels} {{
              background: var(--nuc-glass);
              backdrop-filter: blur(16px);
              -webkit-backdrop-filter: blur(16px);
              border: 1px solid var(--nuc-border);
              border-radius: 18px;
              box-shadow: 0 16px 44px var(--nuc-shadow);
              padding: 1.25rem 1.4rem;
              margin-bottom: 1.1rem;
          }}
          .st-key-db_kpis [data-testid="stMetric"] {{
              background: var(--nuc-glass);
              backdrop-filter: blur(16px);
              -webkit-backdrop-filter: blur(16px);
              border: 1px solid var(--nuc-border);
              border-radius: 16px;
              padding: 0.9rem 1.1rem;
          }}
          .st-key-db_kpis [data-testid="stMetricValue"] {{
              font-size: 1.75rem;
          }}
          [class*="st-key-db_panel_"] .stButton button,
          [class*="st-key-db_panel_"] .stDownloadButton button {{
              border-radius: 12px; font-weight: 600;
              border: 1px solid var(--nuc-border-strong);
          }}
          [class*="st-key-db_panel_"] textarea {{
              font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
              font-size: 0.9rem;
          }}
          /* The read-only file name field keeps a normal (undimmed) label,
             matching the table picker next to it. */
          .st-key-db_export_name label, .st-key-db_export_name label p {{
              color: inherit !important; opacity: 1 !important;
          }}
          /* Danger zone: a red hairline on the destructive panels. */
          .st-key-db_panel_manage_table, .st-key-db_panel_manage_reset {{
              border-color: rgba(255, 99, 99, 0.35);
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _database_page() -> None:
    """Admin-only Database module: browse, query, manage, import/export."""
    _header()
    _database_css()
    with st.sidebar:
        st.header(t("db.header"))
    st.subheader(t("db.header"))
    st.caption(t("db.subtitle"))

    flash = st.session_state.pop(_DB_FLASH, None)
    if flash:
        {"success": st.success, "error": st.error,
         "info": st.info}[flash[0]](flash[1])

    dba = _dba()
    try:
        tables = dba.tables()
    except (database_admin.DatabaseError, sqlite3.Error) as exc:
        st.error(t("db.err.generic", err=str(exc)))
        tables = []

    with st.container(key="db_kpis"):
        k1, k2, k3, k4 = st.columns(4)
        k1.metric(t("db.kpi.tables"), f"{len(tables)}")
        k2.metric(t("db.kpi.rows"), f"{sum(x.rows for x in tables):,}")
        k3.metric(t("db.kpi.size"), database_admin.format_bytes(dba.file_size()))
        modified = dba.modified()
        k4.metric(t("db.kpi.modified"),
                  modified.strftime("%d %b %Y") if modified else "-",
                  help=modified.strftime("%Y-%m-%d %H:%M:%S") if modified else None)
    st.caption(t("db.path", path=dba.path))

    browse, console, manage, transfer = st.tabs([
        t("db.tab.browser"), t("db.tab.console"),
        t("db.tab.manage"), t("db.tab.transfer"),
    ])
    with browse:
        _db_browser(dba, tables)
    with console:
        _db_console(dba, tables)
    with manage:
        _db_manage(dba, tables)
    with transfer:
        _db_transfer(dba, tables)


def _db_browser(dba, tables: list) -> None:
    with st.container(key="db_panel_browser"):
        st.markdown(f"#### {t('db.browser.title')}")
        if not tables:
            st.info(t("db.empty"))
            return
        st.dataframe(pd.DataFrame({
            t("db.col.table"): [x.name for x in tables],
            t("db.col.rows"): [x.rows for x in tables],
            t("db.col.columns"): [len(x.columns) for x in tables],
        }), use_container_width=True, hide_index=True)
        names = [x.name for x in tables]
        picked = st.selectbox(t("db.browser.pick"), names, key="db_browse_table")
        info = next(x for x in tables if x.name == picked)
        st.markdown(f"**{t('db.browser.schema')}**")
        st.dataframe(pd.DataFrame({
            t("db.col.column"): [c.name for c in info.columns],
            t("db.col.type"): [c.type or "-" for c in info.columns],
            t("db.col.notnull"): ["✓" if c.not_null else "" for c in info.columns],
            t("db.col.pk"): ["✓" if c.primary_key else "" for c in info.columns],
        }), use_container_width=True, hide_index=True)
        with st.expander(t("db.browser.preview", n=100), expanded=False):
            try:
                st.dataframe(dba.preview(picked, 100), use_container_width=True,
                             hide_index=True)
            except database_admin.DatabaseError as exc:
                st.error(_db_error_text(exc))


def _db_console(dba, tables: list) -> None:
    with st.container(key="db_panel_console"):
        st.markdown(f"#### {t('db.console.title')}")
        st.caption(t("db.console.readonly",
                     rows=database_admin.MAX_RESULT_ROWS,
                     secs=int(database_admin.QUERY_TIMEOUT_SECONDS)))
        default = (f"SELECT * FROM {database_admin.quote(tables[0].name)} LIMIT 100"
                   if tables else "SELECT name FROM sqlite_master")
        sql = st.text_area(t("db.console.sql"), value=default, height=140,
                           key="db_sql")
        if st.button(t("db.console.run"), type="primary", key="db_run"):
            try:
                st.session_state[_DB_RESULT] = ("ok", sql, dba.run_query(sql))
            except database_admin.DatabaseError as exc:
                st.session_state[_DB_RESULT] = ("error", sql, _db_error_text(exc))
        result = st.session_state.get(_DB_RESULT)
        if not result:
            return
        status, ran_sql, payload = result
        if status == "error":
            st.error(payload)
            return
        st.caption(t("db.console.stats", n=len(payload.frame),
                     ms=f"{payload.elapsed_ms:.1f}"))
        if payload.truncated:
            st.warning(t("db.console.truncated", rows=database_admin.MAX_RESULT_ROWS))
        if payload.frame.columns.empty:
            st.info(t("db.console.no_rows"))
        else:
            st.dataframe(payload.frame, use_container_width=True, hide_index=True)


def _confirmed(prefix: str, phrase: str) -> bool:
    """Two-step safety check: tick the acknowledgement AND type ``phrase``."""
    ack = st.checkbox(t("db.confirm.ack"), key=f"{prefix}_ack")
    typed = st.text_input(t("db.confirm.type", phrase=phrase), key=f"{prefix}_typed",
                          placeholder=phrase)
    return ack and typed.strip() == phrase


def _db_manage(dba, tables: list) -> None:
    with st.container(key="db_panel_manage_table"):
        st.markdown(f"#### {t('db.manage.table.title')}")
        if not tables:
            st.info(t("db.empty"))
        else:
            names = [x.name for x in tables]
            table = st.selectbox(t("db.manage.table.pick"), names, key="db_manage_table")
            actions = {t("db.manage.clear"): "clear", t("db.manage.drop"): "drop"}
            action = actions[st.radio(t("db.manage.action"), list(actions),
                                      key="db_manage_action", horizontal=True)]
            rows = next(x.rows for x in tables if x.name == table)
            st.caption(t(f"db.manage.{action}.help", table=table, rows=f"{rows:,}"))
            ok = _confirmed("db_manage", table)
            if st.button(t(f"db.manage.{action}.btn"), type="primary",
                         disabled=not ok, key="db_manage_go"):
                try:
                    if action == "clear":
                        n = dba.clear_table(table)
                        msg = t("db.manage.clear.done", table=table, rows=f"{n:,}")
                    else:
                        dba.drop_table(table)
                        msg = t("db.manage.drop.done", table=table)
                except database_admin.DatabaseError as exc:
                    st.error(_db_error_text(exc))
                else:
                    for key in ("db_manage_ack", "db_manage_typed"):
                        st.session_state.pop(key, None)
                    _db_done("success", msg)

    with st.container(key="db_panel_manage_reset"):
        st.markdown(f"#### {t('db.reset.title')}")
        st.caption(t("db.reset.help", n=len(tables)))
        ok = _confirmed("db_reset", "RESET")
        if st.button(t("db.reset.btn"), type="primary", disabled=not ok or not tables,
                     key="db_reset_go"):
            try:
                n = dba.reset()
            except database_admin.DatabaseError as exc:
                st.error(_db_error_text(exc))
            else:
                for key in ("db_reset_ack", "db_reset_typed"):
                    st.session_state.pop(key, None)
                _db_done("success", t("db.reset.done", n=n))
        st.caption(t("db.backup.note", keep=database_admin.KEEP_BACKUPS))


def _db_export_bytes(dba) -> bytes:
    """Whole-database snapshot, rebuilt only when the file changes."""
    fingerprint = _adb().fingerprint()
    cached = st.session_state.get("_db_export_cache")
    if not cached or cached[0] != fingerprint:
        cached = (fingerprint, dba.export_bytes())
        st.session_state["_db_export_cache"] = cached
    return cached[1]


def _db_transfer(dba, tables: list) -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    with st.container(key="db_panel_export"):
        st.markdown(f"#### {t('db.export.title')}")
        if not tables:
            st.info(t("db.empty"))
        else:
            # Two symmetric halves: a labelled field on one row, the two
            # download buttons on the next, so both columns line up exactly.
            left, right = st.columns(2, gap="medium")
            left.text_input(t("db.export.db.label"),
                            value=os.path.basename(dba.path),
                            disabled=True, key="db_export_name",
                            help=t("db.export.db.help"))
            table = right.selectbox(t("db.export.csv.pick"),
                                    [x.name for x in tables], key="db_export_table")
            left, right = st.columns(2, gap="medium")
            try:
                left.download_button(
                    t("db.export.db"), data=_db_export_bytes(dba),
                    file_name=f"nucleus_database_{stamp}.db",
                    mime="application/vnd.sqlite3", key="db_export_db",
                    use_container_width=True)
            except database_admin.DatabaseError as exc:
                left.error(_db_error_text(exc))
            try:
                right.download_button(
                    t("db.export.csv"), data=dba.export_csv(table),
                    file_name=f"{table}_{stamp}.csv", mime="text/csv",
                    key="db_export_csv", use_container_width=True)
            except database_admin.DatabaseError as exc:
                right.error(_db_error_text(exc))

    with st.container(key="db_panel_import"):
        st.markdown(f"#### {t('db.import.title')}")
        n = st.session_state.get(_DB_UPLOAD_N, 0)
        upload = st.file_uploader(t("db.import.file"), type=["db", "sqlite", "sqlite3"],
                                  key=f"db_import_file_{n}")
        if upload is None:
            st.caption(t("db.import.help"))
            return
        data = upload.getvalue()
        try:
            found = database_admin.validate_sqlite_bytes(data)
        except database_admin.DatabaseError as exc:
            st.error(_db_error_text(exc))
            return
        st.success(t("db.import.valid", n=len(found),
                     tables=", ".join(found) or "-"))
        modes = {t("db.import.mode.update"): "update",
                 t("db.import.mode.replace"): "replace"}
        mode = modes[st.radio(t("db.import.mode"), list(modes), key="db_import_mode")]
        st.caption(t(f"db.import.mode.{mode}.help"))
        ack = st.checkbox(t("db.confirm.ack"), key="db_import_ack")
        if st.button(t("db.import.btn"), type="primary", disabled=not ack,
                     key="db_import_go"):
            try:
                if mode == "replace":
                    names = dba.import_replace(data)
                else:
                    names = dba.import_update(data)
            except database_admin.DatabaseError as exc:
                st.error(_db_error_text(exc))
            else:
                st.session_state[_DB_UPLOAD_N] = n + 1
                st.session_state.pop("db_import_ack", None)
                _db_done("success", t(f"db.import.done.{mode}", n=len(names)))


def _guarded(permission: str, page_fn) -> None:
    """Render ``page_fn`` only if the role grants ``permission``.

    Otherwise show an access-denied notice with navigation back to the menu.
    """
    if _can(permission):
        page_fn()
        return
    _header()
    st.error(t("access.denied"))


if __name__ == "__main__":
    main()
