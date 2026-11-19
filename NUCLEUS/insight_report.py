"""insight_report.py — executive narrative for NUCLEUS Intelligent Insight.

Turns forecast results into a corporate-style, two-paragraph summary:

1. Model & trend analysis: the selected algorithm with its backtest error
   (MAPE), growth comparison across the analyzed metrics and the historical
   co-movement (Pearson correlation) between them.
2. Projection & recommendation: expected peak and date, a capacity assessment
   against utilization thresholds, and proactive mitigation advice.

English ("EN") and Indonesian ("ID") are supported. The module has no Streamlit
dependency, so it is unit-testable in isolation. Numbers are formatted per
language (ID uses "." for thousands and "," for decimals).

Capacity thresholds apply to metrics measured in percent only. For other units
no absolute capacity is known, so the assessment relies on relative growth.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

# Utilization bands (percent) used for the capacity assessment.
WARN_PCT = 70.0
CRIT_PCT = 85.0
# Relative growth over the horizon that is considered material for metrics
# without an absolute capacity (any unit other than percent).
GROWTH_NOTABLE_PCT = 20.0

_SEVERITY_RANK = {"stable": 0, "elevated": 1, "critical": 2}
_NO_INTERFACE = ("", "—")

_MONTHS = {
    "EN": ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"],
    "ID": ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
           "Agustus", "September", "Oktober", "November", "Desember"],
}


# --------------------------------------------------------------------------- #
# Formatting helpers (shared with the UI)
# --------------------------------------------------------------------------- #
def _lang(lang: Optional[str]) -> str:
    return "ID" if (lang or "EN").upper() == "ID" else "EN"


def _swap(text: str, lang: str) -> str:
    """Convert 1,234.56 to the Indonesian 1.234,56 when ``lang`` is ID."""
    if lang == "ID":
        return text.replace(",", "\0").replace(".", ",").replace("\0", ".")
    return text


def format_int(n, lang: str = "EN") -> str:
    """Whole number with thousands separators: 36,073 (EN) / 36.073 (ID)."""
    return _swap(f"{int(n):,}", _lang(lang))


def format_number(v: float, lang: str = "EN", decimals: int = 2) -> str:
    """Compact number: thousands separators from 1,000, else fixed decimals."""
    lang = _lang(lang)
    text = f"{v:,.0f}" if abs(v) >= 1000 else f"{v:.{decimals}f}"
    return _swap(text, lang)


def format_pct(v: float, lang: str = "EN", decimals: int = 2,
               signed: bool = False) -> str:
    """Percentage text such as 3.42% (EN) / 3,42% (ID)."""
    text = f"{v:+.{decimals}f}" if signed else f"{v:.{decimals}f}"
    return _swap(text, _lang(lang)) + "%"


def format_date(ts, lang: str = "EN") -> str:
    """Long date such as ``9 February 2026`` / ``9 Februari 2026``."""
    ts = pd.Timestamp(ts)
    return f"{ts.day} {_MONTHS[_lang(lang)][ts.month - 1]} {ts.year}"


def join_names(names: list, lang: str = "EN", limit: int = 8) -> str:
    """'a', 'a and b', 'a, b, and c' (ID: 'dan'); long lists are truncated."""
    lang = _lang(lang)
    names = [str(n) for n in names]
    word = "dan" if lang == "ID" else "and"
    more = None
    if len(names) > limit:
        more = len(names) - limit
        names = names[:limit]
    if more:
        tail = f"{more} lainnya" if lang == "ID" else f"{more} more"
        return ", ".join(names) + f", {word} {tail}"
    if len(names) <= 1:
        return "".join(names)
    if len(names) == 2:
        return f"{names[0]} {word} {names[1]}"
    return ", ".join(names[:-1]) + f", {word} {names[-1]}"


# --------------------------------------------------------------------------- #
# Facts extracted from a forecast
# --------------------------------------------------------------------------- #
@dataclass
class SeriesFacts:
    device: str
    interface: str
    metric: str
    unit: str
    model: str
    auto: bool
    mape: Optional[float]
    current: float
    peak: float
    peak_date: Optional[pd.Timestamp]
    last_date: Optional[pd.Timestamp]
    upper_peak: Optional[float] = None
    warn_date: Optional[pd.Timestamp] = None
    crit_date: Optional[pd.Timestamp] = None
    history: Optional[pd.Series] = None

    @property
    def pct_scale(self) -> bool:
        return (self.unit or "").strip() == "%"

    @property
    def change_pct(self) -> Optional[float]:
        """Projected peak versus current value, in percent (None if undefined)."""
        if not self.current:
            return None
        return (self.peak - self.current) / abs(self.current) * 100.0

    @property
    def full_name(self) -> str:
        where = self.device
        if self.interface not in _NO_INTERFACE:
            where = f"{self.device} ({self.interface})"
        return f"{where} · {self.metric}"


def facts_from_forecast(device: str, interface: str, metric: str, unit: str,
                        result) -> SeriesFacts:
    """Build ``SeriesFacts`` from a ``forecasting.ForecastResult``."""
    fc, hist = result.forecast, result.history
    meta = result.meta or {}
    unit = unit or ""
    pct = unit.strip() == "%"

    def first_at_or_above(level: float):
        over = fc[fc >= level]
        return over.index[0] if len(over) else None

    mape = meta.get("backtest_mape")
    mape = float(mape) if mape is not None and np.isfinite(mape) else None
    upper = getattr(result, "upper", None)
    return SeriesFacts(
        device=device, interface=interface or "", metric=metric, unit=unit,
        model=meta.get("model_used") or str(result.method).split("→")[-1].strip(),
        auto="auto_choice" in meta,
        mape=mape,
        current=float(hist.iloc[-1]),
        peak=float(fc.max()),
        peak_date=fc.idxmax() if len(fc) else None,
        last_date=hist.index[-1] if len(hist) else None,
        upper_peak=float(upper.max()) if upper is not None and len(upper) else None,
        warn_date=first_at_or_above(WARN_PCT) if pct else None,
        crit_date=first_at_or_above(CRIT_PCT) if pct else None,
        history=hist,
    )


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
def mape_quality(mape: float) -> str:
    """Accuracy band for a MAPE value (Lewis, 1982)."""
    if mape < 10:
        return "high"
    if mape < 20:
        return "good"
    if mape < 50:
        return "moderate"
    return "limited"


def severity(f: SeriesFacts) -> str:
    """``critical`` / ``elevated`` / ``stable`` for one series."""
    if f.pct_scale:
        if f.peak >= CRIT_PCT:
            return "critical"
        if f.peak >= WARN_PCT or (f.upper_peak is not None
                                  and f.upper_peak >= CRIT_PCT):
            return "elevated"
        return "stable"
    chg = f.change_pct
    return "elevated" if chg is not None and chg >= GROWTH_NOTABLE_PCT else "stable"


def _risk_key(f: SeriesFacts):
    secondary = f.peak if f.pct_scale else (f.change_pct or 0.0)
    return (_SEVERITY_RANK[severity(f)], secondary)


def strongest_correlation(facts: list) -> Optional[tuple]:
    """Pair ``(a, b, r)`` of series with the strongest historical correlation.

    Pearson r on the overlapping history (levels), at least 5 shared points and
    both series non-constant. At most 6 series are compared.
    """
    usable = [f for f in facts if f.history is not None and len(f.history) >= 5]
    best = None
    for i, a in enumerate(usable[:6]):
        for b in usable[i + 1:6]:
            joined = pd.concat([a.history, b.history], axis=1,
                               join="inner").dropna()
            if len(joined) < 5:
                continue
            x, y = joined.iloc[:, 0], joined.iloc[:, 1]
            if x.nunique() < 2 or y.nunique() < 2:
                continue
            r = float(x.corr(y))
            if np.isfinite(r) and (best is None or abs(r) > abs(best[2])):
                best = (a, b, r)
    return best


def _category(metric: str) -> str:
    m = metric.lower()
    if "cpu" in m:
        return "cpu"
    if "mem" in m or "ram" in m:
        return "mem"
    if any(k in m for k in ("bandwidth", "traffic", "throughput", "bps",
                            "util", "link", "interface")):
        return "net"
    if any(k in m for k in ("disk", "storage", "volume")):
        return "disk"
    if "temp" in m:
        return "temp"
    if any(k in m for k in ("power", "watt", "kw")):
        return "power"
    return "default"


# --------------------------------------------------------------------------- #
# Wording
# --------------------------------------------------------------------------- #
_T = {
    "EN": {
        "head1": "**Model & Trend Analysis.**",
        "head2": "**Projection & Recommendation.**",
        "intro_single": "NUCLEUS evaluated {name} over a {horizon} forecast horizon.",
        "intro_single_nohz": "NUCLEUS evaluated {name}.",
        "intro_multi": "NUCLEUS evaluated {n} series ({scope}) over a {horizon} forecast horizon.",
        "intro_multi_nohz": "NUCLEUS evaluated {n} series ({scope}).",
        "device": ("{n} device", "{n} devices"),
        "metric": ("{n} metric", "{n} metrics"),
        "model_auto": ("For {name}, the {model} algorithm was selected after "
                       "backtesting against the alternative models, achieving a "
                       "Mean Absolute Percentage Error (MAPE) of {mape}, which "
                       "indicates {quality} predictive reliability."),
        "model_manual": ("For {name}, the {model} algorithm was applied as "
                         "configured and recorded a backtest Mean Absolute "
                         "Percentage Error (MAPE) of {mape}, which indicates "
                         "{quality} predictive reliability."),
        "model_nomape": ("For {name}, the {model} algorithm was applied; backtest "
                         "accuracy could not be established (insufficient history "
                         "or near-zero actual values), so the projection should "
                         "be read as indicative."),
        "model_same": ("The same algorithm was applied to all analyzed series "
                       "(MAPE range {lo} to {hi})."),
        "model_vary": "Algorithm selection differs by series: {items}.",
        "quality": {"high": "high", "good": "good", "moderate": "moderate",
                    "limited": "limited"},
        "growth": ("On trend, {top} shows the steepest projected growth "
                   "({top_chg}), compared with {bottom} ({bottom_chg})."),
        "corr": ("Historical co-movement between {a} and {b} is {strength} and "
                 "{direction} (r = {r}); {meaning}"),
        "strength": {"strong": "strong", "moderate": "moderate", "weak": "weak"},
        "direction": {"positive": "positive", "negative": "negative"},
        "meaning": {
            "strong_pos": ("load on these resources rises and falls together, so a "
                           "surge is likely to strain both at once and capacity "
                           "should be planned jointly."),
            "moderate_pos": ("the two resources are partially coupled; a surge in "
                             "one is often, but not always, accompanied by the "
                             "other."),
            "weak": ("the resources behave largely independently and can be "
                     "managed as separate capacity lines."),
            "negative": ("the resources move in opposite directions, which may "
                         "indicate workload shifting between them."),
        },
        "proj": ("Forward projection: {name} is expected to peak at {peak} on "
                 "{date}, {chg} versus the current {current}."),
        "proj_nochg": ("Forward projection: {name} is expected to peak at {peak} "
                       "on {date}, against a current {current}."),
        "proj_upper": " The upper confidence bound reaches {upper}.",
        "status": {"critical": "CRITICAL", "elevated": "ELEVATED", "stable": "STABLE"},
        "assess": "Capacity assessment: ",
        "crit": ("{status} — the forecast crosses the {crit} critical utilization "
                 "threshold on {date} (in about {days} days)."),
        "crit_now": ("{status} — utilization is already at or above the {crit} "
                     "critical threshold and is projected to peak at {peak}."),
        "elev_point": ("{status} — projected peak utilization passes the {warn} "
                       "advisory threshold (first reached on {date}) and stays "
                       "{gap} points below the {crit} critical threshold."),
        "elev_band": ("{status} — the point forecast stays below the {warn} "
                      "advisory threshold, but its upper confidence bound reaches "
                      "{upper}, leaving a narrow safety margin to the {crit} "
                      "critical threshold."),
        "stable_pct": ("{status} — the projected peak of {peak} leaves {head} "
                       "percentage points of headroom to the {crit} critical "
                       "threshold."),
        "elev_rel": ("{status} — projected growth of {chg} over the horizon is "
                     "material; no absolute capacity threshold is defined for "
                     "{metric}, so the projected peak of {peak} should be "
                     "validated against provisioned capacity."),
        "stable_rel": "{status} — projected growth of {chg} is within normal variation.",
        "at_risk": " {k} of {n} analyzed series are at elevated or critical risk.",
        "rec_critical": ("Recommended action: start proactive mitigation before "
                         "{date} — {actions}. Escalate to capacity planning for "
                         "funding approval and enforce automated alerts at {warn} "
                         "and {crit}."),
        "rec_elevated_pct": ("Recommended action: schedule a capacity review "
                             "within the next 30 days — {actions}. Keep alerting at "
                             "{warn} and {crit} and re-run the forecast after each "
                             "data refresh."),
        "rec_elevated_rel": ("Recommended action: review capacity for the affected "
                             "resource within the next 30 days — {actions}. Define "
                             "an alert threshold aligned with provisioned capacity "
                             "and re-run the forecast after each data refresh."),
        "rec_stable": ("Recommended action: no intervention is required; continue "
                       "routine monitoring and refresh the forecast as new data "
                       "arrives."),
        "actions": {
            "cpu": ("rebalance workloads across hosts, validate autoscaling "
                    "policies, or add compute capacity"),
            "mem": ("review memory allocation and growth patterns (leaks, "
                    "caching), right-size instances, or add memory"),
            "net": ("assess link utilization for an upgrade, apply traffic "
                    "engineering or QoS, and rebalance flows"),
            "disk": "extend storage capacity or enforce retention and archival policies",
            "temp": "review cooling capacity and airflow in the affected zone",
            "power": "review power distribution headroom and redundancy",
            "default": ("review provisioned capacity and workload placement for "
                        "the affected resource"),
        },
    },
    "ID": {
        "head1": "**Analisis Model & Tren.**",
        "head2": "**Proyeksi & Rekomendasi.**",
        "intro_single": "NUCLEUS mengevaluasi {name} pada horizon prediksi {horizon}.",
        "intro_single_nohz": "NUCLEUS mengevaluasi {name}.",
        "intro_multi": "NUCLEUS mengevaluasi {n} deret data ({scope}) pada horizon prediksi {horizon}.",
        "intro_multi_nohz": "NUCLEUS mengevaluasi {n} deret data ({scope}).",
        "device": ("{n} perangkat", "{n} perangkat"),
        "metric": ("{n} metrik", "{n} metrik"),
        "model_auto": ("Untuk {name}, algoritma {model} dipilih setelah diuji "
                       "balik (backtest) terhadap model alternatif, dengan Mean "
                       "Absolute Percentage Error (MAPE) sebesar {mape}, yang "
                       "menunjukkan keandalan prediksi {quality}."),
        "model_manual": ("Untuk {name}, algoritma {model} diterapkan sesuai "
                         "konfigurasi dan mencatat MAPE hasil backtest sebesar "
                         "{mape}, yang menunjukkan keandalan prediksi {quality}."),
        "model_nomape": ("Untuk {name}, algoritma {model} diterapkan; akurasi "
                         "backtest tidak dapat ditentukan (riwayat data tidak "
                         "memadai atau nilai aktual mendekati nol), sehingga "
                         "proyeksi sebaiknya dibaca sebagai indikatif."),
        "model_same": ("Algoritma yang sama diterapkan pada seluruh deret yang "
                       "dianalisis (rentang MAPE {lo} hingga {hi})."),
        "model_vary": "Pemilihan algoritma berbeda pada tiap deret: {items}.",
        "quality": {"high": "tinggi", "good": "baik", "moderate": "sedang",
                    "limited": "terbatas"},
        "growth": ("Dari sisi tren, {top} menunjukkan proyeksi pertumbuhan "
                   "tertinggi ({top_chg}), dibandingkan {bottom} ({bottom_chg})."),
        "corr": ("Ko-pergerakan historis antara {a} dan {b} bersifat {strength} "
                 "dan {direction} (r = {r}); {meaning}"),
        "strength": {"strong": "kuat", "moderate": "sedang", "weak": "lemah"},
        "direction": {"positive": "positif", "negative": "negatif"},
        "meaning": {
            "strong_pos": ("beban pada kedua sumber daya cenderung naik dan turun "
                           "bersamaan sehingga lonjakan berpotensi menekan "
                           "keduanya sekaligus, dan kapasitas sebaiknya "
                           "direncanakan secara terpadu."),
            "moderate_pos": ("kedua sumber daya terkait sebagian; lonjakan pada "
                             "salah satunya sering, tetapi tidak selalu, diikuti "
                             "oleh yang lain."),
            "weak": ("kedua sumber daya bergerak relatif independen dan dapat "
                     "dikelola sebagai lini kapasitas yang terpisah."),
            "negative": ("kedua sumber daya bergerak berlawanan arah, yang dapat "
                         "mengindikasikan perpindahan beban kerja di antara "
                         "keduanya."),
        },
        "proj": ("Proyeksi ke depan: {name} diperkirakan mencapai puncak {peak} "
                 "pada {date}, {chg} dibandingkan nilai saat ini {current}."),
        "proj_nochg": ("Proyeksi ke depan: {name} diperkirakan mencapai puncak "
                       "{peak} pada {date}, dari nilai saat ini {current}."),
        "proj_upper": " Batas atas interval kepercayaan mencapai {upper}.",
        "status": {"critical": "KRITIS", "elevated": "MENINGKAT", "stable": "STABIL"},
        "assess": "Penilaian kapasitas: ",
        "crit": ("{status} — prakiraan melampaui ambang utilisasi kritis {crit} "
                 "pada {date} (sekitar {days} hari lagi)."),
        "crit_now": ("{status} — utilisasi sudah berada pada atau di atas ambang "
                     "kritis {crit} dan diproyeksikan mencapai puncak {peak}."),
        "elev_point": ("{status} — puncak utilisasi yang diproyeksikan melewati "
                       "ambang peringatan {warn} (pertama kali tercapai pada "
                       "{date}) dan masih {gap} poin di bawah ambang kritis "
                       "{crit}."),
        "elev_band": ("{status} — prakiraan titik masih di bawah ambang "
                      "peringatan {warn}, namun batas atas interval "
                      "kepercayaannya mencapai {upper}, sehingga margin "
                      "keamanan terhadap ambang kritis {crit} sempit."),
        "stable_pct": ("{status} — puncak proyeksi {peak} menyisakan ruang "
                       "{head} poin persentase terhadap ambang kritis {crit}."),
        "elev_rel": ("{status} — pertumbuhan proyeksi {chg} selama horizon "
                     "tergolong material; belum ada ambang kapasitas absolut "
                     "untuk {metric}, sehingga puncak proyeksi {peak} perlu "
                     "divalidasi terhadap kapasitas terpasang."),
        "stable_rel": "{status} — pertumbuhan proyeksi {chg} masih dalam variasi normal.",
        "at_risk": " {k} dari {n} deret yang dianalisis berada pada risiko meningkat atau kritis.",
        "rec_critical": ("Rekomendasi: mulai mitigasi proaktif sebelum {date} — "
                         "{actions}. Eskalasikan ke perencanaan kapasitas untuk "
                         "persetujuan pendanaan dan terapkan peringatan otomatis "
                         "pada {warn} dan {crit}."),
        "rec_elevated_pct": ("Rekomendasi: jadwalkan tinjauan kapasitas dalam 30 "
                             "hari ke depan — {actions}. Pertahankan peringatan "
                             "pada {warn} dan {crit}, lalu jalankan ulang "
                             "prakiraan setiap kali data diperbarui."),
        "rec_elevated_rel": ("Rekomendasi: tinjau kapasitas sumber daya terkait "
                             "dalam 30 hari ke depan — {actions}. Tetapkan "
                             "ambang peringatan yang selaras dengan kapasitas "
                             "terpasang dan jalankan ulang prakiraan setiap kali "
                             "data diperbarui."),
        "rec_stable": ("Rekomendasi: tidak diperlukan intervensi; lanjutkan "
                       "pemantauan rutin dan perbarui prakiraan saat data baru "
                       "tersedia."),
        "actions": {
            "cpu": ("seimbangkan ulang beban kerja antar-host, validasi kebijakan "
                    "autoscaling, atau tambah kapasitas komputasi"),
            "mem": ("tinjau alokasi dan pola pertumbuhan memori (kebocoran, "
                    "cache), sesuaikan ukuran instans, atau tambah memori"),
            "net": ("evaluasi utilisasi tautan untuk peningkatan kapasitas, "
                    "terapkan rekayasa trafik atau QoS, dan seimbangkan ulang "
                    "aliran"),
            "disk": ("perluas kapasitas penyimpanan atau terapkan kebijakan "
                     "retensi dan pengarsipan"),
            "temp": "tinjau kapasitas pendinginan dan aliran udara pada zona terkait",
            "power": "tinjau ruang cadangan dan redundansi distribusi daya",
            "default": ("tinjau kapasitas terpasang dan penempatan beban kerja "
                        "untuk sumber daya terkait"),
        },
    },
}


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
@dataclass
class Insight:
    """The narrative as paragraphs plus its overall severity."""
    paragraphs: list
    severity: str

    @property
    def markdown(self) -> str:
        return "\n\n".join(self.paragraphs)

    @property
    def plain(self) -> str:
        """Text without Markdown emphasis (for text-to-speech)."""
        return self.markdown.replace("**", "")


def _short_names(facts: list) -> dict:
    """Compact, unambiguous labels for comparing the analyzed series."""
    devices = {(f.device, f.interface) for f in facts}
    metrics = {f.metric for f in facts}
    names = {}
    for f in facts:
        if len(devices) == 1:
            names[id(f)] = f.metric
        elif len(metrics) == 1:
            names[id(f)] = f.full_name.rsplit(" · ", 1)[0]
        else:
            names[id(f)] = f.full_name
    return names


def _val(v: float, unit: str, lang: str) -> str:
    text = format_number(v, lang)
    if not unit:
        return text
    return text + (unit if unit.strip() == "%" else f" {unit}")


def build_executive_insight(facts: list, lang: str = "EN",
                            horizon_label: str = "") -> Insight:
    """Compose the executive summary for the analyzed series.

    ``facts`` holds one ``SeriesFacts`` per series; the series with the highest
    risk is the focus of the model, projection and recommendation statements.
    """
    if not facts:
        raise ValueError("no_series")
    lang = _lang(lang)
    T = _T[lang]
    focus = max(facts, key=_risk_key)
    multi = len(facts) > 1
    short = _short_names(facts)

    # ------------------------------ paragraph 1 ----------------------------- #
    parts = []
    if multi:
        scope = ", ".join([
            T["device"][0 if len({f.device for f in facts}) == 1 else 1].format(
                n=len({f.device for f in facts})),
            T["metric"][0 if len({f.metric for f in facts}) == 1 else 1].format(
                n=len({f.metric for f in facts})),
        ])
        key = "intro_multi" if horizon_label else "intro_multi_nohz"
        parts.append(T[key].format(n=len(facts), scope=scope,
                                   horizon=horizon_label))
    else:
        key = "intro_single" if horizon_label else "intro_single_nohz"
        parts.append(T[key].format(name=focus.full_name, horizon=horizon_label))

    if focus.mape is None:
        parts.append(T["model_nomape"].format(name=focus.full_name,
                                              model=focus.model))
    else:
        parts.append(T["model_auto" if focus.auto else "model_manual"].format(
            name=focus.full_name, model=focus.model,
            mape=format_pct(focus.mape, lang),
            quality=T["quality"][mape_quality(focus.mape)]))

    if multi:
        others = [f for f in facts if f is not focus]
        if len({f.model for f in facts}) == 1:
            scored = [f.mape for f in facts if f.mape is not None]
            if scored:
                parts.append(T["model_same"].format(
                    lo=format_pct(min(scored), lang),
                    hi=format_pct(max(scored), lang)))
        else:
            items = "; ".join(
                f"{short[id(f)]} — {f.model}"
                + (f" (MAPE {format_pct(f.mape, lang)})" if f.mape is not None else "")
                for f in others[:4])
            parts.append(T["model_vary"].format(items=items))

        ranked = sorted((f for f in facts if f.change_pct is not None),
                        key=lambda f: f.change_pct, reverse=True)
        if len(ranked) >= 2:
            top, bottom = ranked[0], ranked[-1]
            parts.append(T["growth"].format(
                top=short[id(top)], bottom=short[id(bottom)],
                top_chg=format_pct(top.change_pct, lang, 1, signed=True),
                bottom_chg=format_pct(bottom.change_pct, lang, 1, signed=True)))

        pair = strongest_correlation(facts)
        if pair:
            a, b, r = pair
            strength = "strong" if abs(r) >= 0.7 else (
                "moderate" if abs(r) >= 0.4 else "weak")
            if strength == "weak":
                meaning = T["meaning"]["weak"]
            elif r < 0:
                meaning = T["meaning"]["negative"]
            else:
                meaning = T["meaning"]["strong_pos" if strength == "strong"
                                       else "moderate_pos"]
            parts.append(T["corr"].format(
                a=short[id(a)], b=short[id(b)], strength=T["strength"][strength],
                direction=T["direction"]["negative" if r < 0 else "positive"],
                r=format_number(r, lang), meaning=meaning))

    p1 = T["head1"] + " " + " ".join(parts)

    # ------------------------------ paragraph 2 ----------------------------- #
    sev = severity(focus)
    unit = focus.unit
    proj_args = dict(name=focus.full_name,
                     peak=_val(focus.peak, unit, lang),
                     date=format_date(focus.peak_date, lang) if focus.peak_date is not None else "-",
                     current=_val(focus.current, unit, lang))
    chg = focus.change_pct
    if chg is None:
        proj = T["proj_nochg"].format(**proj_args)
    else:
        proj = T["proj"].format(chg=format_pct(chg, lang, 1, signed=True),
                                **proj_args)
    if focus.upper_peak is not None and focus.upper_peak > focus.peak + 1e-9:
        proj += T["proj_upper"].format(upper=_val(focus.upper_peak, unit, lang))

    status = T["status"][sev]
    warn, crit = (format_pct(WARN_PCT, lang, 0), format_pct(CRIT_PCT, lang, 0))
    if focus.pct_scale:
        if sev == "critical" and focus.current >= CRIT_PCT:
            assess = T["crit_now"].format(status=status, crit=crit,
                                          peak=_val(focus.peak, unit, lang))
        elif sev == "critical":
            days = max((focus.crit_date - focus.last_date).days, 1) \
                if focus.crit_date is not None and focus.last_date is not None else 0
            assess = T["crit"].format(
                status=status, crit=crit, days=format_int(days, lang),
                date=format_date(focus.crit_date, lang))
        elif sev == "elevated" and focus.peak >= WARN_PCT:
            assess = T["elev_point"].format(
                status=status, warn=warn, crit=crit,
                date=format_date(focus.warn_date, lang),
                gap=format_number(CRIT_PCT - focus.peak, lang, 1))
        elif sev == "elevated":
            assess = T["elev_band"].format(
                status=status, warn=warn, crit=crit,
                upper=_val(focus.upper_peak, unit, lang))
        else:
            assess = T["stable_pct"].format(
                status=status, peak=_val(focus.peak, unit, lang), crit=crit,
                head=format_number(CRIT_PCT - focus.peak, lang, 1))
    else:
        rel = format_pct(chg, lang, 1, signed=True) if chg is not None else "-"
        if sev == "elevated":
            assess = T["elev_rel"].format(status=status, chg=rel,
                                          metric=focus.metric,
                                          peak=_val(focus.peak, unit, lang))
        else:
            assess = T["stable_rel"].format(status=status, chg=rel)
    assess = T["assess"] + assess

    at_risk = [f for f in facts if severity(f) != "stable"]
    if multi and at_risk:
        assess += T["at_risk"].format(k=len(at_risk), n=len(facts))

    # Overall severity is the worst across all series.
    overall = max((severity(f) for f in facts), key=_SEVERITY_RANK.get)
    if overall == "stable":
        rec = T["rec_stable"]
    else:
        actions, seen = [], set()
        for f in sorted(at_risk, key=_risk_key, reverse=True):
            cat = _category(f.metric)
            if cat not in seen and len(actions) < 2:
                seen.add(cat)
                actions.append(T["actions"][cat])
        joined = "; ".join(actions)
        if overall == "critical":
            crit_dates = [f.crit_date for f in at_risk if f.crit_date is not None]
            when = format_date(min(crit_dates), lang) if crit_dates else "-"
            rec = T["rec_critical"].format(date=when, actions=joined,
                                           warn=warn, crit=crit)
        elif focus.pct_scale:
            rec = T["rec_elevated_pct"].format(actions=joined, warn=warn,
                                               crit=crit)
        else:
            rec = T["rec_elevated_rel"].format(actions=joined)

    p2 = f"{T['head2']} {proj} {assess} {rec}"
    return Insight(paragraphs=[p1, p2], severity=overall)
