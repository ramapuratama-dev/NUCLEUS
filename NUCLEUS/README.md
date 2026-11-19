# NUCLEUS — Network, Unified Compute, and Layered Environment Under Surveillance

An IT infrastructure **monitoring & analytics platform** built with Python + Streamlit. Upload metric readings from Excel, forecast future usage with multiple models, and let **NUCLEUS** proactively warn you — in text and voice — before thresholds are breached.

## Features

- 📥 **Excel ingestion** — upload a `.xlsx`/`.xls` with `Timestamp, Device_Name, Metric_Name, Value, Unit`. Automatic cleaning, interpolation of gaps, and aggregation.
- 📈 **Forecasting engine** — SMA / Exponential Smoothing, Linear Regression, Holt-Winters, and Meta **Prophet** (trend + seasonality), with graceful fallback when optional models aren't installed.
- 🎛️ **Interactive controls** — pick device, metric, horizon (7/14/30 days), threshold (default 70%), and method.
- 📊 **Visualization & KPIs** — historical vs forecast line chart with projection band and threshold line; KPI cards for Current Usage, Peak Predicted Usage, and Days Until Threshold Breach.
- 🧬 **NUCLEUS Intelligent Insight** — plain-language summary with optional **text-to-speech** (gTTS / pyttsx3).
- 🎙️ **Voice command** — ask NUCLEUS by voice (speech-to-text) or text; it answers against the current forecast.

## Project structure

```
app.py           # Streamlit dashboard (UI + wiring)
data_loader.py   # Excel loading, cleaning, aggregation
forecasting.py   # Forecasting methods behind one interface
nucleus_ai.py    # NUCLEUS Intelligent Insight text, TTS, STT, rules-based Q&A
requirements.txt
tests/           # pytest unit tests
.kiro/specs/cam-ai/   # requirements.md, design.md, tasks.md
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

The core app runs with just the core packages. `prophet`, `gTTS`, `pyttsx3`, and `SpeechRecognition` are optional — the app detects what's installed and degrades gracefully (e.g. Prophet falls back to Linear Regression; voice features show a note instead of failing).

## Run

```bash
streamlit run app.py
```

Open the URL Streamlit prints (default http://localhost:8501). With no file uploaded, the dashboard loads a built-in sample dataset so you can explore immediately.

## Excel format

| Timestamp | Device_Name | Metric_Name | Value | Unit |
| --- | --- | --- | --- | --- |
| 2026-01-01 00:00 | Host-01 | CPU_Usage | 42.5 | % |
| 2026-01-01 00:00 | Host-01 | Memory_Usage | 61.0 | % |
| 2026-01-01 00:00 | Switch-A | Bandwidth | 310 | Mbps |

## Tests

```bash
pytest -q
```
