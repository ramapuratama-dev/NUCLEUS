"""The module portal: a glass sliding tab bar that goes straight to a module."""
import os
import re

import pytest
from streamlit.testing.v1 import AppTest

import auth

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("NUCLEUS_DB_PATH", str(tmp_path / "nucleus_database.db"))


def _portal(role="administrator", **state):
    at = AppTest.from_file(APP, default_timeout=120)
    at.session_state["authenticated"] = True
    at.session_state["username"] = "tester"
    at.session_state["user_role"] = role
    for key, value in state.items():
        at.session_state[key] = value
    at.run()
    assert not at.exception, at.exception
    return at


def _tabs(at):
    groups = at.get("button_group")
    assert len(groups) == 1, "the portal must have exactly one tab bar"
    return [(o.content_icon, o.content) for o in groups[0].proto.options]


# ------------------------------- the portal ---------------------------------- #
def test_portal_is_one_tab_bar_instead_of_two_cards():
    at = _portal()
    assert _tabs(at) == [("", "Analytics"), ("", "Monitoring"), ("", "Database")]
    # The old cards had "Open ..." buttons; only the footer actions remain.
    labels = [b.label.replace("\ufe0f", "") for b in at.button]   # ignore emoji variation selector
    assert labels == ["⚙ Settings", "🚪 Log Out"]


def test_portal_starts_with_no_module_selected():
    at = _portal()
    assert at.session_state["mode"] is None
    assert "mode" not in at.query_params


@pytest.mark.parametrize("role", ["engineer", "viewer"])
def test_non_admins_see_analytics_and_monitoring_only(role):
    assert [name for _, name in _tabs(_portal(role=role))] == ["Analytics", "Monitoring"]


def test_admin_sees_three_tabs():
    names = [name for _, name in _tabs(_portal(role="administrator"))]
    assert names == ["Analytics", "Monitoring", "Database"]


def test_a_tab_is_hidden_when_the_role_lacks_its_permission(monkeypatch):
    monkeypatch.setattr(
        auth, "has_permission",
        lambda role, perm: perm != auth.PERM_VIEW_MONITORING)
    assert [name for _, name in _tabs(_portal())] == ["Analytics", "Database"]


# ------------------------------- bypass -------------------------------------- #
@pytest.mark.parametrize("label, mode, tabs_left", [
    ("Analytics", "analytics", ["Compute Stream", "Network Stream", "Facility Stream"]),
    ("Monitoring", "monitoring", []),
])
def test_picking_a_tab_goes_straight_to_the_module(label, mode, tabs_left):
    at = _portal(portal_nav_ctl=label)
    assert at.session_state["mode"] == mode
    assert at.query_params["mode"] == [mode]
    # The portal's tab bar is gone; only the module's own controls remain.
    assert [o.content for g in at.get("button_group") for o in g.proto.options] == tabs_left


def test_monitoring_tab_renders_the_monitoring_page():
    at = _portal(portal_nav_ctl="Monitoring")
    assert any("Real-Time Monitoring" in s.value for s in at.subheader)


def test_analytics_tab_renders_the_analytics_page():
    at = _portal(portal_nav_ctl="Analytics")
    labels = [o.content for o in at.get("button_group")[0].proto.options]
    assert labels == ["Compute Stream", "Network Stream", "Facility Stream"]


# ------------------------------- the styling --------------------------------- #
def test_glass_tabs_css_slides_one_indicator_per_option():
    import app
    css = app._glass_tabs_css("portal_nav", 3)
    root = '.st-key-portal_nav [data-baseweb="button-group"]'
    for index, shift in ((1, 0), (2, 100), (3, 200)):
        rule = (f'{root}:has(> button:nth-child({index})'
                f'[kind="segmented_controlActive"])::before')
        assert rule in css
        assert f"translateX({shift}%)" in css
    assert "calc((100% - 10px) / 3)" in css           # indicator = one slot
    assert "calc(100% / 3)" in css                     # equal tab slots
    assert "backdrop-filter: blur(22px)" in css       # liquid glass
    assert "prefers-reduced-motion" in css            # motion can be turned off
    assert "__" not in css                             # every placeholder filled


def test_glass_tabs_css_is_scoped_to_its_container():
    import app
    css = app._glass_tabs_css("stream_selector", 3, "700px")
    selectors = re.findall(r"^\s*([.\w\[\]\"=\-:>() *,]+?)\s*\{", css, re.M)
    assert selectors and all(
        s.lstrip().startswith(".st-key-stream_selector") or s.startswith("@")
        for s in selectors if "keyframes" not in s and "from" not in s)
    assert "min(700px, 94vw)" in css


def test_page_transition_is_opacity_only_and_respects_reduced_motion():
    import app
    css = app._page_transition_css()
    assert 'st-key-page_' in css and "nucPageIn" in css
    assert "transform" not in css           # would break the fixed footer/pill
    assert "prefers-reduced-motion" in css


# ------------------------- size and centering -------------------------------- #
def _css_blocks(at, needle):
    return [m.value for m in at.markdown if needle in m.value]


def test_large_preset_is_bigger_than_the_regular_one():
    import app
    regular = app._glass_tabs_css("x", 2, size="regular")
    large = app._glass_tabs_css("x", 2, size="large")
    assert "min-height: 2.75rem" in regular
    assert "min-height: clamp(3.75rem, 11vw, 5.5rem)" in large
    assert "calc((100% - 10px) / 2)" in regular      # 5px padding each side
    assert "calc((100% - 16px) / 2)" in large        # 8px padding each side
    assert "font-size: clamp(1.05rem, 4.2vw, 1.65rem)" in large
    # The icon is sized from the label so it is never smaller than the text.
    assert "calc(clamp(1.05rem, 4.2vw, 1.65rem) * 1.25)" in large
    for css in (regular, large, app._glass_tabs_css("x", 3, centered=True)):
        assert "__" not in css                        # every placeholder filled


def test_centered_bar_uses_fixed_auto_margins_and_no_transform():
    import app
    css = app._glass_tabs_css("portal_nav", 2, "800px", size="large", centered=True)
    media = css[css.index("@media (min-height:"):]
    assert f"@media (min-height: {app._CENTER_MIN_HEIGHT_PX}px)" in media
    for rule in ("position: fixed", "margin: auto", "height: fit-content",
                 "min(800px, 94vw)"):
        assert rule in media
    assert "transform" not in media       # a transform would re-parent fixed children
    assert "position: fixed" not in app._glass_tabs_css("x", 2)   # opt-in only


def test_short_screens_fall_back_to_the_normal_flow():
    import app
    # 24px of air between the title (ends ~242px) and a bar of 106px that is
    # centred on the viewport needs at least this much height.
    assert app._CENTER_MIN_HEIGHT_PX >= 2 * (242 + 24 + 106 // 2)


def test_portal_uses_the_large_centered_bar():
    at = _portal()
    css = " ".join(_css_blocks(at, ".st-key-portal_nav"))
    assert "min-height: clamp(3.75rem, 11vw, 5.5rem)" in css
    assert "min(800px, 94vw)" in css and "height: fit-content" in css


def test_analytics_stream_selector_stays_regular_and_in_flow():
    at = _portal(portal_nav_ctl="Analytics")
    css = " ".join(_css_blocks(at, ".st-key-stream_selector"))
    assert "min-height: 2.75rem" in css
    assert "height: fit-content" not in css          # not viewport-centered
