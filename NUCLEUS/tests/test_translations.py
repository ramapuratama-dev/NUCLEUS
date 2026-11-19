import translations as tr


def test_default_is_english():
    assert tr.DEFAULT_LANG == "EN"
    # Outside Streamlit, get_lang falls back to the default.
    assert tr.get_lang() == "EN"


def test_translate_id_and_en():
    assert tr.t("sidebar.settings", lang="ID") == "⚙️ Pengaturan Prediksi"
    assert tr.t("sidebar.settings", lang="EN") == "⚙️ Forecast Settings"
    assert tr.t("sidebar.upload", lang="ID") == "Unggah Dokumen"
    assert tr.t("sidebar.method", lang="ID") == "Metode Prediksi"


def test_named_placeholder_formatting():
    out = tr.t("kpi.current", lang="EN", name="Host-01")
    assert out == "Current (Host-01)"
    out_id = tr.t("kpi.current", lang="ID", name="Host-01")
    assert "Host-01" in out_id and out_id.startswith("Nilai Terkini")


def test_unknown_key_returns_key():
    assert tr.t("does.not.exist", lang="EN") == "does.not.exist"


def test_unknown_lang_falls_back_to_default():
    # Unsupported language code resolves to the default (English).
    assert tr.t("sidebar.metric", lang="FR") == tr.t("sidebar.metric", lang="EN")


def test_every_key_has_both_languages():
    for key, entry in tr.TRANSLATIONS.items():
        assert "id" in entry and "en" in entry, f"missing translation for {key}"
        assert entry["id"] and entry["en"], f"empty translation for {key}"
