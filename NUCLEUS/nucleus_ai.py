"""nucleus_ai.py — NUCLEUS Intelligent Insight assistant: natural-language
insight, text-to-speech, speech-to-text and a rules-based Q&A engine.

NUCLEUS = Network, Unified Compute, and Layered Environment Under Surveillance.

Optional voice backends (gTTS, pyttsx3, SpeechRecognition) are imported lazily
and the module degrades to text-only behaviour when they are missing.
"""
from __future__ import annotations

import io
import tempfile
from typing import Optional

ASSISTANT_NAME = "NUCLEUS Intelligent Insight"


# --------------------------------------------------------------------------- #
# Natural-language insight
# --------------------------------------------------------------------------- #
def build_insight(
    device: str,
    interface: str,
    metric: str,
    unit: str,
    method: str,
    current: float,
    peak: float,
    n_series: int = 1,
    lang: str = "ID",
) -> str:
    """Compose a concise forecast summary describing trend direction.

    ``lang`` selects the output language: "ID" (Bahasa Indonesia, default) or
    "EN" (English). ``n_series`` prefixes a note when several series are being
    analyzed together.
    """
    lang = (lang or "ID").upper()
    metric_label = metric.replace("_", " ")
    u = f"{unit}" if unit else ""
    where = device
    if interface and interface not in ("", "—"):
        where = f"{device} ({interface})"

    delta = peak - current
    if current:
        magnitude = f"{abs(delta / abs(current) * 100.0):.0f}%"
    else:
        magnitude = f"{abs(delta):.4g}{u}"
    direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")

    if lang == "EN":
        prefix = f"Analyzing {n_series} series. " if n_series > 1 else ""
        if direction == "up":
            body = (f"Based on the {method} model, {metric_label} on {where} is "
                    f"projected to rise by about {magnitude}, from {current:.4g}{u} "
                    f"to a peak of {peak:.4g}{u} across the forecast horizon. "
                    f"Keep an eye on remaining capacity.")
        elif direction == "down":
            body = (f"Based on the {method} model, {metric_label} on {where} is "
                    f"projected to ease by about {magnitude}, from {current:.4g}{u} "
                    f"toward {peak:.4g}{u} across the forecast horizon. Capacity "
                    f"pressure looks to be relaxing.")
        else:
            body = (f"Based on the {method} model, {metric_label} on {where} is "
                    f"projected to stay flat around {current:.4g}{u} across the "
                    f"forecast horizon. No material change expected.")
        return prefix + body

    # Default: Bahasa Indonesia.
    prefix = f"Menganalisis {n_series} deret data. " if n_series > 1 else ""
    if direction == "up":
        body = (f"Berdasarkan model {method}, penggunaan {metric_label} pada {where} "
                f"diproyeksikan naik sebesar {magnitude}, dari {current:.4g}{u} "
                f"hingga mencapai puncaknya di {peak:.4g}{u} selama horizon "
                f"prediksi. Harap pantau sisa kapasitas secara berkala.")
    elif direction == "down":
        body = (f"Berdasarkan model {method}, penggunaan {metric_label} pada {where} "
                f"diproyeksikan turun sebesar {magnitude}, dari {current:.4g}{u} "
                f"menuju {peak:.4g}{u} selama horizon prediksi. Tekanan kapasitas "
                f"tampak mereda.")
    else:
        body = (f"Berdasarkan model {method}, penggunaan {metric_label} pada {where} "
                f"diproyeksikan stabil di sekitar {current:.4g}{u} selama horizon "
                f"prediksi. Tidak ada perubahan berarti yang diperkirakan.")
    return prefix + body


# --------------------------------------------------------------------------- #
# Text-to-speech
# --------------------------------------------------------------------------- #
def tts_backend() -> Optional[str]:
    """Return the name of the first available TTS backend, or None."""
    try:
        import gtts  # noqa: F401
        return "gtts"
    except Exception:  # noqa: BLE001
        pass
    try:
        import pyttsx3  # noqa: F401
        return "pyttsx3"
    except Exception:  # noqa: BLE001
        pass
    return None


def synthesize_speech(text: str, lang: str = "id") -> Optional[bytes]:
    """Synthesize `text` to audio bytes. Returns None if no backend is available.

    ``lang`` is a gTTS language code ("id" for Indonesian, "en" for English).
    """
    if not text:
        return None
    backend = tts_backend()
    if backend == "gtts":
        try:
            from gtts import gTTS

            buf = io.BytesIO()
            gTTS(text=text, lang=(lang or "id")).write_to_fp(buf)
            return buf.getvalue()
        except Exception:  # noqa: BLE001
            pass  # fall through to pyttsx3
    if backend in ("gtts", "pyttsx3"):
        try:
            import pyttsx3

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                path = tmp.name
            engine = pyttsx3.init()
            engine.save_to_file(text, path)
            engine.runAndWait()
            with open(path, "rb") as fh:
                return fh.read()
        except Exception:  # noqa: BLE001
            return None
    return None


# --------------------------------------------------------------------------- #
# Speech-to-text
# --------------------------------------------------------------------------- #
def stt_available() -> bool:
    try:
        import speech_recognition  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def transcribe(audio_bytes: bytes) -> Optional[str]:
    """Transcribe WAV audio bytes to text. Returns None if unavailable/failed."""
    if not audio_bytes or not stt_available():
        return None
    try:
        import speech_recognition as sr

        recognizer = sr.Recognizer()
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# Rules-based Q&A
# --------------------------------------------------------------------------- #
def answer_question(question: str, context: dict) -> str:
    """Answer a question about the current forecast using the context dict.

    Expected context keys: device, metric, unit, method, threshold, current,
    peak, breach_days.
    """
    if not question or not question.strip():
        return (
            f"{ASSISTANT_NAME} here. Ask me about current usage, the predicted "
            f"peak, the trend direction, or which model is in use."
        )

    q = question.lower()
    device = context.get("device", "the device")
    metric = str(context.get("metric", "the metric")).replace("_", " ")
    unit = context.get("unit", "") or ""
    method = context.get("method", "the selected")
    current = context.get("current")
    peak = context.get("peak")

    def has(*words: str) -> bool:
        return any(w in q for w in words)

    if has("trend", "direction", "rising", "falling", "grow", "increase", "decrease"):
        if current is None or peak is None:
            return "Run a forecast first and I'll describe the trend."
        if peak > current:
            return f"{metric} on {device} is trending up toward {peak:.4g}{unit}."
        if peak < current:
            return f"{metric} on {device} is trending down toward {peak:.4g}{unit}."
        return f"{metric} on {device} is projected to stay roughly flat."

    if has("peak", "max", "highest", "worst"):
        if peak is None:
            return "I don't have a predicted peak yet. Run a forecast first."
        return f"The predicted peak for {metric} on {device} is {peak:.4g}{unit}."

    if has("current", "now", "latest", "present"):
        if current is None:
            return "I don't have a current reading yet."
        return f"Current {metric} on {device} is {current:.4g}{unit}."

    if has("method", "model", "algorithm", "which"):
        return f"The active forecasting model is {method}."

    if has("device", "host", "server"):
        return f"You're currently looking at {device}."

    return (
        f"I'm {ASSISTANT_NAME}. I can tell you the current usage, the predicted "
        f"peak, the trend direction, and which model is active. Try asking "
        f"'what's the predicted peak?'"
    )
