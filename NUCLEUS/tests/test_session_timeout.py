"""30-minute idle timeout: policy, token TTL and the app's logout behaviour."""
import json
import os
from datetime import datetime, timedelta

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import auth
import session_guard
import settings_store

REAL_TOKENS = auth.SessionTokens

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")
WARNING_EN = "inactivity"


# --------------------------------------------------------------------------- #
# session_guard
# --------------------------------------------------------------------------- #
def test_boundary_is_inclusive_of_exactly_1800_seconds():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert not session_guard.is_expired(now - timedelta(seconds=1800), now, 1800)
    assert session_guard.is_expired(now - timedelta(seconds=1801), now, 1800)


def test_no_recorded_activity_is_not_expired():
    assert not session_guard.is_expired(None, datetime.now(), 1800)


def test_default_and_env_override(monkeypatch):
    monkeypatch.delenv(session_guard.ENV_VAR, raising=False)
    assert session_guard.timeout_seconds() == 1800
    monkeypatch.setenv(session_guard.ENV_VAR, "6")
    assert session_guard.timeout_seconds() == 6
    for bad in ("abc", "0", "-5", ""):
        monkeypatch.setenv(session_guard.ENV_VAR, bad)
        assert session_guard.timeout_seconds() == 1800


def test_tick_seconds_is_bounded():
    assert session_guard.tick_seconds(1800) == 60
    assert session_guard.tick_seconds(60) == 6
    assert session_guard.tick_seconds(3) == 1


def test_format_duration():
    assert session_guard.format_duration(1800, "EN") == "30 minutes"
    assert session_guard.format_duration(60, "EN") == "1 minute"
    assert session_guard.format_duration(8, "EN") == "8 seconds"
    assert session_guard.format_duration(1800, "ID") == "30 menit"
    assert session_guard.format_duration(8, "ID") == "8 detik"


# --------------------------------------------------------------------------- #
# SessionTokens TTL
# --------------------------------------------------------------------------- #
class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_token_expires_after_idle_ttl_and_is_remembered():
    clock = Clock()
    reg = auth.SessionTokens(idle_ttl=1800, clock=clock)
    tok = reg.issue("alice")
    clock.now += 1800
    assert reg.username_for(tok) == "alice"
    clock.now += 1
    assert reg.username_for(tok) is None
    assert reg.was_expired(tok)
    assert not reg.was_expired("never-issued")


def test_touch_extends_token_life():
    clock = Clock()
    reg = auth.SessionTokens(idle_ttl=100, clock=clock)
    tok = reg.issue("alice")
    for _ in range(5):
        clock.now += 90
        reg.touch(tok)
    assert reg.username_for(tok) == "alice"


def test_revoked_token_is_unknown_not_expired():
    reg = REAL_TOKENS(idle_ttl=100, clock=Clock())
    tok = reg.issue("alice")
    reg.revoke(tok)
    assert reg.username_for(tok) is None
    assert not reg.was_expired(tok)


def test_expired_memory_is_capped():
    clock = Clock()
    reg = auth.SessionTokens(idle_ttl=1, clock=clock)
    for _ in range(auth.SessionTokens._EXPIRED_CAP + 50):
        reg.issue("u")
    clock.now += 10
    reg.username_for("x")
    assert len(reg._expired) <= auth.SessionTokens._EXPIRED_CAP


# --------------------------------------------------------------------------- #
# App behaviour
# --------------------------------------------------------------------------- #
@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_DB_PATH", str(tmp_path / "db.sqlite"))
    monkeypatch.delenv(session_guard.ENV_VAR, raising=False)
    settings_path = str(tmp_path / "settings.json")
    with open(settings_path, "w", encoding="utf-8") as fh:
        json.dump({"data": {"source": "sample"}}, fh)
    monkeypatch.setattr(settings_store.SettingsStore.__init__, "__defaults__",
                        (settings_path,))
    users_path = str(tmp_path / "users.json")
    store = auth.UserStore(users_path)
    store.add_user("tester", "Tester", "t@x.io", auth.ROLE_ADMIN, "pw12345!")
    monkeypatch.setattr(auth.UserStore.__init__, "__defaults__", (users_path,))

    # AppTest re-executes app.py, so its cache_resource differs from an imported
    # copy. Share one registry through the ``auth`` module they both import.
    shared = auth.SessionTokens(idle_ttl=1800)

    class Shared:
        VERSION = auth.SessionTokens.VERSION

        def __new__(cls, *a, **k):
            return shared

    monkeypatch.setattr(auth, "SessionTokens", Shared)
    st.cache_resource.clear()
    return shared


def _app(authenticated=True, last_active=None, **state):
    at = AppTest.from_file(APP, default_timeout=60)
    if authenticated:
        at.session_state["authenticated"] = True
        at.session_state["username"] = "tester"
        at.session_state["user_role"] = auth.ROLE_ADMIN
    if last_active is not None:
        at.session_state["last_active_time"] = last_active
    for k, v in state.items():
        at.session_state[k] = v
    return at


def _warnings(at):
    return [w.value for w in at.warning]


def test_idle_over_30_minutes_logs_out_with_warning(env):
    at = _app(last_active=datetime.now() - timedelta(minutes=31),
              some_leftover="secret")
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["authenticated"] is False
    assert at.session_state["username"] == ""
    assert "some_leftover" not in at.session_state
    assert any(WARNING_EN in w for w in _warnings(at))
    assert any("30 minutes" in w for w in _warnings(at))
    assert len(at.text_input) == 2          # login form is shown


def test_idle_logout_keeps_language(env):
    at = _app(last_active=datetime.now() - timedelta(minutes=31),
              nucleus_lang="ID", _lang_seeded=True)
    at.run()
    assert not at.exception, at.exception
    assert any("tidak ada aktivitas" in w for w in _warnings(at))


def test_active_within_limit_stays_signed_in_and_refreshes_clock(env):
    old = datetime.now() - timedelta(minutes=29)
    at = _app(last_active=old)
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["authenticated"] is True
    assert at.session_state["last_active_time"] > old + timedelta(minutes=28)
    assert not any(WARNING_EN in w for w in _warnings(at))


def test_missing_clock_on_authenticated_session_is_initialised(env):
    at = _app()
    at.run()
    assert at.session_state["authenticated"] is True
    assert isinstance(at.session_state["last_active_time"], datetime)


def test_idle_logout_revokes_the_token(env):
    token = env.issue("tester")
    at = _app(last_active=datetime.now() - timedelta(minutes=31))
    at.query_params["token"] = token
    at.run()
    assert env.username_for(token) is None
    assert "token" not in at.query_params


def test_valid_token_resumes_and_sets_clock(env):
    token = env.issue("tester")
    at = _app(authenticated=False)
    at.query_params["token"] = token
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["authenticated"] is True
    assert isinstance(at.session_state["last_active_time"], datetime)


def test_expired_token_does_not_resume_and_warns(env):
    clock = Clock()
    reg = REAL_TOKENS(idle_ttl=10, clock=clock)
    token = reg.issue("tester")
    clock.now += 11
    reg.username_for(token)            # moves it to the expired set
    env._tokens, env._expired = reg._tokens, reg._expired
    at = _app(authenticated=False)
    at.query_params["token"] = token
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["authenticated"] is False
    assert any(WARNING_EN in w for w in _warnings(at))
    assert "token" not in at.query_params


def test_login_clears_the_expired_notice(env):
    at = _app(last_active=datetime.now() - timedelta(minutes=31))
    at.run()
    assert at.session_state["session_expired"] is True
    at.text_input[0].set_value("tester")
    at.text_input[1].set_value("pw12345!")
    at.button[0].click()
    at.run()
    assert not at.exception, at.exception
    assert at.session_state["authenticated"] is True
    assert "session_expired" not in at.session_state
    assert isinstance(at.session_state["last_active_time"], datetime)
