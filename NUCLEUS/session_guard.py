"""session_guard.py — idle-timeout policy for NUCLEUS sessions.

A signed-in session expires after 30 minutes without user interaction. This
module only holds the policy (how long, whether a session has expired, how to
word the duration); it has no Streamlit dependency, so it is unit-testable.

The timeout can be overridden with the ``NUCLEUS_IDLE_TIMEOUT_SECONDS``
environment variable (a positive integer). The default is 1800 seconds.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

DEFAULT_TIMEOUT_SECONDS = 1800          # 30 minutes
ENV_VAR = "NUCLEUS_IDLE_TIMEOUT_SECONDS"
# How often the browser-side watchdog checks for expiry, at most.
MAX_TICK_SECONDS = 60


def timeout_seconds() -> int:
    """Configured idle timeout in seconds (invalid values fall back to 30 min)."""
    raw = os.environ.get(ENV_VAR)
    if raw is None:
        return DEFAULT_TIMEOUT_SECONDS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return value if value > 0 else DEFAULT_TIMEOUT_SECONDS


def idle_seconds(last_active: datetime, now: datetime) -> float:
    """Seconds elapsed since ``last_active``."""
    return (now - last_active).total_seconds()


def is_expired(last_active: Optional[datetime], now: datetime,
               timeout: Optional[int] = None) -> bool:
    """True when the session has been idle for MORE than the timeout.

    ``last_active`` of ``None`` means "no activity recorded yet" and is never
    expired. Exactly the timeout is still valid.
    """
    if last_active is None:
        return False
    limit = timeout_seconds() if timeout is None else timeout
    return idle_seconds(last_active, now) > limit


def tick_seconds(timeout: Optional[int] = None) -> int:
    """Watchdog interval: a tenth of the timeout, between 1 and 60 seconds."""
    limit = timeout_seconds() if timeout is None else timeout
    return max(1, min(MAX_TICK_SECONDS, limit // 10))


def format_duration(seconds: int, lang: str = "EN") -> str:
    """'30 minutes' / '1 minute' / '8 seconds' (ID: '30 menit' / '8 detik')."""
    seconds = int(seconds)
    indonesian = (lang or "EN").upper() == "ID"
    if seconds % 60 == 0:
        n = seconds // 60
        unit = "menit" if indonesian else ("minute" if n == 1 else "minutes")
    else:
        n = seconds
        unit = "detik" if indonesian else ("second" if n == 1 else "seconds")
    return f"{n} {unit}"
