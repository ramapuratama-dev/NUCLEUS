import nucleus_ai


def _ctx():
    return {
        "device": "Host-01", "interface": "eth0", "metric": "Memory_Usage",
        "unit": "%", "method": "Prophet", "current": 60.0, "peak": 88.0,
    }


def test_build_insight_rising_trend_indonesian_default():
    text = nucleus_ai.build_insight("Host-01", "eth0", "Memory_Usage", "%",
                                    "Prophet", 60.0, 88.0)
    # Default language is Bahasa Indonesia.
    assert "diproyeksikan naik" in text.lower()
    assert "Host-01" in text and "Prophet" in text
    assert "pantau sisa kapasitas" in text.lower()


def test_build_insight_multi_series_prefix_id():
    text = nucleus_ai.build_insight("Host-01", "eth0", "Memory_Usage", "%",
                                    "Prophet", 60.0, 88.0, n_series=3)
    assert text.startswith("Menganalisis 3 deret data.")


def test_build_insight_english_switch():
    text = nucleus_ai.build_insight("Host-01", "eth0", "Memory_Usage", "%",
                                    "Prophet", 60.0, 88.0, lang="EN")
    assert "projected to rise" in text.lower()
    assert "menganalisis" not in text.lower()


def test_build_insight_falling_and_flat_id():
    down = nucleus_ai.build_insight("Host-01", "", "CPU_Usage", "%",
                                    "Holt-Winters", 70.0, 45.0)
    assert "diproyeksikan turun" in down.lower()
    flat = nucleus_ai.build_insight("Host-01", "", "CPU_Usage", "%",
                                    "Linear Regression", 50.0, 50.0)
    assert "stabil" in flat.lower()


def test_answer_question_trend_intent():
    ans = nucleus_ai.answer_question("what's the trend direction?", _ctx())
    assert "up" in ans.lower() or "88" in ans


def test_answer_question_peak_and_current():
    assert "88" in nucleus_ai.answer_question("what's the peak?", _ctx())
    assert "60" in nucleus_ai.answer_question("current usage now?", _ctx())


def test_answer_question_method():
    assert "Prophet" in nucleus_ai.answer_question("which model?", _ctx())


def test_answer_question_fallback():
    ans = nucleus_ai.answer_question("tell me a joke", _ctx())
    assert "NUCLEUS" in ans


def test_voice_backends_graceful():
    # These must never raise even when backends are absent.
    assert nucleus_ai.synthesize_speech("") is None
    assert nucleus_ai.transcribe(b"") is None
