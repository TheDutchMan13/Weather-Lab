"""Weather Lab: Streamlit entry point. Run with: streamlit run app.py (or open WeatherLab.exe)."""

import html
import os
import streamlit as st
import streamlit.components.v1 as components
import time
from weatherlab import auth, autofit, health, stations, storage, theme
from weatherlab.config import APP_NAME, APP_VERSION
from weatherlab.nav_groups import DEFAULT_PAGE, GROUPS
from weatherlab.settings import load_settings
from weatherlab import api
from weatherlab.screens.common import start_poller
from weatherlab.screens.data import _import_page, backup_page, export_page, reports_page
from weatherlab.screens.explore import ask_page, rain_calendar_page, rain_events_page, replay_page, unusual_page
from weatherlab.screens.hazards import air_page, fire_page, lightning_page, radar_page, tropics_page
from weatherlab.screens.history import coverage_page, history_page, rewind_page
from weatherlab.screens.now import alerts_log_page, home_page, sensors_page
from weatherlab.screens.outlook import astronomy_page, forecast_page, heat_page, sun_page, wind_map_page, wind_page
from weatherlab.screens.help import help_page
from weatherlab.screens.system import health_check_page, settings_page, setup_page, stations_page, status_page, whats_new_page


def access_gate() -> bool:
    """True when the page may be shown. Once network access is on, other devices need the password."""
    if not load_settings().allow_network:
        return True
    if st.session_state.get("signed_in"):
        return True
    token = os.environ.get("WEATHERLAB_WINDOW_TOKEN", "")
    if token and st.query_params.get("wl_token") == token:
        st.session_state["signed_in"] = True
        return True
    if not auth.password_set():
        st.error("Other devices can't open Weather Lab until a password is set. Set one on the Setup page on this PC.")
        return False
    st.markdown(theme.page_head("Sign in", "Enter the password you set on the Setup page."), unsafe_allow_html=True)
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        wait = auth.locked_for()
        if wait:
            st.error(f"Too many attempts. Try again in {wait} seconds.")
        elif auth.sign_in(password):
            auth.reset_failures()
            st.session_state["signed_in"] = True
            st.rerun()
        else:
            auth.record_failure()
            st.error("That password isn't right.")
    return False


PAGE_ICONS = {  # emoji, so each sidebar page has a clear, coloured icon
    "Home": "🏠", "History": "🗓️", "Sensors": "🌡️", "Alert history": "🚨",
        "Coverage": "🗂️", "Rewind": "⏪",
    "Rain calendar": "📆", "Rain events": "💧", "Ask": "💬",
    "Unusual days": "🧐", "Replay": "▶️",
    "Forecast": "🔮", "Heat": "🥵", "Wind": "🌬️", "Wind map": "💨",
    "Sun": "☀️", "Astronomy": "🔭",
    "Air": "😷", "Fire": "🚒", "Lightning": "⚡", "Tropics": "🌀", "Radar": "📡",
    "Import": "📥", "Export": "📤", "Backup": "💾", "Reports": "📄",
    "Status": "✅", "Health check": "🩺",
    "What's New": "🆕", "Help": "❔", "Setup": "🧰", "Settings": "⚙️", "Stations": "📍",
}


SIDEBAR_CSS = """<style>
[data-testid="stSidebarNavLink"] { gap: .6rem; }
.st-key-setup_save { position: sticky; bottom: 0; z-index: 5; padding: .75rem 0; background: rgba(128, 128, 128, .12);
  backdrop-filter: blur(8px); border-top: 1px solid rgba(128, 128, 128, .3); }
</style>"""


PAGE_FUNCS = {"Home": home_page, "History": history_page, "Sensors": sensors_page, "Status": status_page, "Health check": health_check_page, "Help": help_page, "Alert history": alerts_log_page, "What's New": whats_new_page, "Settings": settings_page, 
              "Coverage": coverage_page, "Rain events": rain_events_page, "Ask": ask_page, "Unusual days": unusual_page, "Rewind": rewind_page,
              "Rain calendar": rain_calendar_page,
              "Replay": replay_page, "Reports": reports_page, "Forecast": forecast_page, "Heat": heat_page,
              "Wind": wind_page, "Wind map": wind_map_page, "Sun": sun_page, "Astronomy": astronomy_page, "Air": air_page,
              "Fire": fire_page, "Lightning": lightning_page, "Tropics": tropics_page, "Radar": radar_page,
              "Import": _import_page, "Export": export_page, "Backup": backup_page, "Setup": setup_page, "Stations": stations_page}


def _sections() -> dict:
    """The sidebar sections and their pages, as Streamlit page objects."""
    return {group: [st.Page(PAGE_FUNCS[name], title=name, icon=PAGE_ICONS[name], default=(name == DEFAULT_PAGE))
                    for name in names]
            for group, names in GROUPS.items()}


def _jump_box(all_pages: dict) -> None:
    """Type part of a page name to go straight to it."""
    def go() -> None:
        choice = st.session_state.get("jump_to_page")
        st.session_state["jump_to_page"] = None
        if choice in all_pages:
            st.switch_page(all_pages[choice])
    st.sidebar.selectbox("Jump to page", sorted(all_pages), index=None, placeholder="Type to search pages",
                         key="jump_to_page", on_change=go)


def _sidebar_status() -> None:
    """One line under the menu: is the station reporting, with the exact time on hover."""
    try:
        latest = storage.latest(storage.connect())
        state, text = health.age_status(latest[0] if latest else None, time.time())
    except Exception:
        return
    icon, label = {"ok": ("🟢", "Feeds current"), "slow": ("🟠", "Readings delayed"),
                   "silent": ("🔴", "Station not reporting"), "none": ("⚪", "No readings yet")}[state]
    st.sidebar.markdown(f'<div title="{html.escape(text, quote=True)}" style="font-size:13px;padding:4px 8px">'
                        f'{icon} {label}</div>', unsafe_allow_html=True)


HEAD_SCRIPT = """<script>
(function () {
  try {
    var head = window.parent.document.head;
    var tags = [
      ['link', {rel: 'manifest', href: '/app/static/manifest.webmanifest'}],
      ['link', {rel: 'apple-touch-icon', href: '/app/static/apple-touch-icon.png'}],
      ['meta', {name: 'apple-mobile-web-app-capable', content: 'yes'}],
      ['meta', {name: 'apple-mobile-web-app-title', content: 'Weather Lab'}],
      ['meta', {name: 'theme-color', content: '#0b3d91'}]
    ];
    tags.forEach(function (t) {
      var key = t[1].rel || t[1].name;
      if (head.querySelector('[data-weatherlab="' + key + '"]')) { return; }
      var el = window.parent.document.createElement(t[0]);
      Object.keys(t[1]).forEach(function (k) { el.setAttribute(k, t[1][k]); });
      el.setAttribute('data-weatherlab', key);
      head.appendChild(el);
    });
  } catch (e) {}
})();
</script>"""


def _install_app_head() -> None:
    """Adds the app icon and home-screen settings, so Weather Lab can be added to a phone's home screen."""
    components.html(HEAD_SCRIPT, height=0)


def _select_station() -> None:
    """Sets the station for this run: the one picked in the sidebar, or the first one if that station is gone."""
    pending = st.session_state.pop("pending_station", None)
    if pending:
        st.session_state["station_pick"] = pending
    if st.session_state.get("station_pick") not in stations.ids():
        st.session_state["station_pick"] = stations.MAIN
    stations.set_current(st.session_state["station_pick"])


def _station_picker() -> None:
    """The station the pages show. Shown once a second station has been added."""
    options = stations.all_stations()
    if len(options) < 2:
        return
    names = {r["id"]: r["name"] for r in options}
    st.sidebar.selectbox("Station", list(names), format_func=lambda sid: names.get(sid, sid), key="station_pick")


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    _select_station()
    cfg = load_settings()
    st.markdown(theme.css(theme.is_dark(), cfg.color_scheme, cfg.compact, cfg.large_text), unsafe_allow_html=True)
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    autofit.install()
    _install_app_head()
    start_poller()
    api.ensure(cfg.api_enabled and cfg.allow_network, cfg.api_port)
    with stations.using(stations.MAIN):
        allowed = access_gate()
    if not allowed:
        return
    sections = _sections()
    _station_picker()
    nav = st.navigation(sections, position="sidebar")
    _jump_box({page.title: page for group in sections.values() for page in group})
    _sidebar_status()
    nav.run()
    st.caption(f"{APP_NAME} version {APP_VERSION}")


main()
