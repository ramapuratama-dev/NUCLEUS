"""settings_store.py — persistent application configuration for NUCLEUS.

A small JSON-backed store (``settings.json`` next to this module) holding the
admin-configurable preferences exposed on the Settings page:

  * forecasting: default model + the set of enabled models
  * data:        default data source + retention window (days)
  * system:      primary language (NUCLEUS is permanently dark-themed)

Dependency-free (stdlib only) and importable without Streamlit, so it stays
unit-testable. Writes are atomic (temp file + ``os.replace``).
"""
from __future__ import annotations

import json
import os
from typing import Any

_DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "settings.json")

# The canonical default configuration. ``enabled_models == None`` means
# "all available models" (resolved at the UI layer against the live method
# list, which varies with installed optional dependencies).
_DEFAULTS: dict[str, Any] = {
    "forecasting": {
        "default_model": "Auto (Best Fit)",
        "enabled_models": None,
    },
    "data": {
        "source": "sample",          # "sample" | "upload"
        "retention_days": 90,
    },
    "system": {
        "language": "EN",            # "EN" | "ID"
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge ``override`` onto a copy of ``base``."""
    out = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.items()}
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class SettingsStore:
    """JSON-backed application settings with typed section helpers."""

    def __init__(self, path: str = _DEFAULT_PATH):
        self.path = path
        self._data: dict = _deep_merge(_DEFAULTS, {})
        self._load()

    # ---- persistence ----------------------------------------------------- #
    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as fh:
                    disk = json.load(fh)
                # Merge onto defaults so new keys appear even for old files.
                self._data = _deep_merge(_DEFAULTS, disk)
            except (json.JSONDecodeError, OSError):
                self._data = _deep_merge(_DEFAULTS, {})
        else:
            # Persist the defaults on first use so the file exists.
            self._save()

    def _save(self) -> None:
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    # ---- generic access -------------------------------------------------- #
    def all(self) -> dict:
        return _deep_merge(self._data, {})

    def get(self, section: str, key: str, default: Any = None) -> Any:
        return self._data.get(section, {}).get(key, default)

    def update_section(self, section: str, values: dict) -> None:
        """Merge ``values`` into ``section`` and persist."""
        current = dict(self._data.get(section, {}))
        current.update(values)
        self._data[section] = current
        self._save()

    # ---- typed convenience getters --------------------------------------- #
    def default_model(self) -> str:
        return self.get("forecasting", "default_model",
                        _DEFAULTS["forecasting"]["default_model"])

    def enabled_models(self):
        return self.get("forecasting", "enabled_models", None)

    def data_source(self) -> str:
        return self.get("data", "source", _DEFAULTS["data"]["source"])

    def retention_days(self) -> int:
        return int(self.get("data", "retention_days",
                            _DEFAULTS["data"]["retention_days"]))

    def language(self) -> str:
        return self.get("system", "language", _DEFAULTS["system"]["language"])
