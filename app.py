"""Weather Lab: Streamlit entry point. Run with: streamlit run app.py (or open WeatherLab.exe)."""

import html
import os
import streamlit as st
import time
from dataclasses import replace
from weatherlab import auth, health, sidebar, stations, storage, theme
from weatherlab.config import APP_NAME, APP_VERSION
from weatherlab import nav_groups
from weatherlab.nav_groups import DEFAULT_PAGE, GROUPS, TABS
from weatherlab.settings import load_settings, save_settings
from weatherlab import api
from weatherlab.screens.common import start_poller
from weatherlab.screens.data import _import_page, backup_page, export_page, reports_page
from weatherlab.screens.explore import ask_page, rain_calendar_page, rain_events_page, replay_page, unusual_page
from weatherlab.screens.hazards import air_page, fire_page, lightning_page, radar_page, tropics_page
from weatherlab.screens.compare import compare_stations_page
from weatherlab.screens.history import history_page
from weatherlab.screens.now import alerts_log_page, home_layout_page, home_page, sensors_page
from weatherlab.screens.outlook import astronomy_page, forecast_page, heat_page, sun_page, wind_map_page, wind_page
from weatherlab.screens.help import help_page
from weatherlab.screens.system import health_check_page, settings_page, stations_page, status_page, whats_new_page


def access_gate() -> bool:
    """True when the page may be shown. Once network access is on, other devices need the password.

    From 0.37.55: this PC is recognised by its connection (Streamlit reports no address for localhost, and headers
    can't fake one), and remembered in the session as on_pc, so risky settings can be limited to it. A password
    change signs other devices out. With network access off, a Host header that isn't this PC is refused."""
    cfg = load_settings()
    ip = st.context.ip_address
    local = auth.is_local(ip)
    if not cfg.allow_network:
        if not auth.local_host_header(st.context.headers.get("Host")):
            st.error("Weather Lab only answers to this PC while network access is off.")
            return False
        st.session_state["on_pc"] = True
        return True
    token = os.environ.get("WEATHERLAB_WINDOW_TOKEN", "")
    if local or (token and st.query_params.get("wl_token") == token):
        st.session_state["on_pc"] = True
        st.session_state["signed_in"] = True
        return True
    st.session_state["on_pc"] = False
    if not auth.client_allowed(ip, cfg.tailscale_only):
        st.error("This Weather Lab only accepts devices on Tailscale. Turn on Tailscale on this device, or change "
                 "the setting in Settings, Station, Access tab, on the PC.")
        return False
    version = auth.password_version()
    if st.session_state.get("signed_in") and version and st.session_state.get("pw_version") == version:
        return True
    st.session_state["signed_in"] = False  # signed out by a password change, or never signed in
    if not version:
        st.error("Other devices can't open Weather Lab until a password is set. Set one in Settings, Station, Access tab, on this PC.")
        return False
    st.markdown(theme.page_head("Sign in", "Enter the password you set in Settings, on the Access tab."), unsafe_allow_html=True)
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        ok, wait = auth.try_sign_in(password, ip or "")
        if wait:
            st.error(f"Too many attempts. Try again in {wait} seconds.")
        elif ok:
            st.session_state["signed_in"] = True
            st.session_state["pw_version"] = version
            st.rerun()
        else:
            st.error("That password isn't right.")
    return False


# Line icons (0.37.62, the redesign), replacing the emoji. Tab names show them too.
PAGE_ICONS = {
    "Home": ":material/home:", "Forecast": ":material/calendar_month:", "Alert history": ":material/notifications:",
    "Compare stations": ":material/compare_arrows:", "History": ":material/bar_chart:", "Ask": ":material/chat_bubble:",
    "Air and heat": ":material/thermostat:", "Wind": ":material/air:", "Sun and sky": ":material/wb_sunny:",
    "Lightning": ":material/bolt:", "Fire": ":material/local_fire_department:", "Tropics": ":material/cyclone:",
    "Radar": ":material/radar:", "Station health": ":material/monitor_heart:", "Stations": ":material/layers:",
    "Settings": ":material/settings:", "Home layout": ":material/dashboard_customize:", "Data": ":material/database:",
    "Help": ":material/help:",
    # Tabs (and the old page names that open them)
    "Rain calendar": ":material/calendar_month:", "Rain events": ":material/rainy:", "Unusual days": ":material/warning:",
    "Replay": ":material/play_circle:", "Air": ":material/air:", "Heat": ":material/thermostat:",
    "Wind map": ":material/map:", "Sun": ":material/light_mode:", "Astronomy": ":material/dark_mode:",
    "Backup": ":material/backup:", "Reports": ":material/bar_chart:", "Export": ":material/upload:",
    "Import": ":material/download:", "What's New": ":material/new_releases:",
    "Status": ":material/monitor_heart:", "Sensors": ":material/sensors:", "Health check": ":material/fact_check:",
}


SIDEBAR_CSS = """<style>
[data-testid="stSidebarNavLink"] { gap: .6rem; }
[data-testid="stSidebar"] [data-testid="stPageLink"] a { gap: .6rem; padding: .15rem .5rem; }
[data-testid="stSidebar"] [data-testid="stExpander"] details { border: none; }
[data-testid="stSidebar"] [data-testid="stExpander"] summary { padding: .3rem .5rem; font-size: 12px; font-weight: 700;
  letter-spacing: .08em; text-transform: uppercase; opacity: .75; }
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] { padding: 0 0 .4rem 0; border: none; }
[data-testid="stSidebar"] [data-testid="stExpanderDetails"] [data-testid="stVerticalBlock"] { gap: .1rem; }
[data-testid="stSidebar"] [data-testid="stExpander"] hr { display: none; }
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] { gap: .25rem; }
.wl-nav-head { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; opacity: .75;
  padding: .5rem .5rem .2rem; margin-bottom: .35rem; line-height: 1.4; }
.st-key-setup_save { position: sticky; bottom: 0; z-index: 5; padding: .75rem 0; background: rgba(128, 128, 128, .12);
  backdrop-filter: blur(8px); border-top: 1px solid rgba(128, 128, 128, .3); }
</style>"""


# Station health (0.37.40): the three station pages as views of one page. Only the view you pick runs, so the
# health check's network tests don't run every time the page opens.
STATION_VIEWS = {"Status": status_page, "Sensors": sensors_page, "Health check": health_check_page}


def station_health_page() -> None:
    head = st.empty()  # the title goes above the tabs (0.37.62)
    theme.head_slot(head)
    view = st.segmented_control("Station health", list(STATION_VIEWS), default="Status", key="station_view",
                                format_func=_tab_label, label_visibility="collapsed") or "Status"
    STATION_VIEWS[view]()
    _fill_unused_head("Station health")


# Pages without tabs.
PAGE_FUNCS = {"Home": home_page, "Forecast": forecast_page, "Alert history": alerts_log_page,
              "Compare stations": compare_stations_page, "Ask": ask_page, "Fire": fire_page,
              "Lightning": lightning_page, "Tropics": tropics_page, "Radar": radar_page,
              "Station health": station_health_page, "Stations": stations_page, "Settings": settings_page,
              "Home layout": home_layout_page}

# The tabs of the tabbed pages (nav_groups.TABS, 0.37.56). Each was a page of its own before.
VIEW_FUNCS = {"History": history_page, "Rain calendar": rain_calendar_page, "Rain events": rain_events_page,
              "Unusual days": unusual_page, "Replay": replay_page, "Air": air_page, "Heat": heat_page,
              "Wind": wind_page, "Wind map": wind_map_page, "Sun": sun_page, "Astronomy": astronomy_page,
              "Backup": backup_page, "Reports": reports_page, "Export": export_page, "Import": _import_page,
              "Help": help_page, "What's New": whats_new_page}


def _tabbed(page: str):
    """A page made of tabs. ?tab=<name> picks the tab, so links and old page names land on the right one."""
    tabs = TABS[page]

    def run() -> None:
        key = nav_groups.view_key(page)
        wanted = st.query_params.get("tab")
        match = next((t for t in tabs if wanted and t.lower() == wanted.lower()), None)
        if match:
            st.session_state[key] = match
            del st.query_params["tab"]
        elif st.session_state.get(key) not in tabs:
            st.session_state[key] = tabs[0]
        head = st.empty()  # the page's title goes above its tabs (0.37.62)
        theme.head_slot(head)
        view = st.segmented_control(page, tabs, key=key, required=True, label_visibility="collapsed",
                                    format_func=_tab_label)
        VIEW_FUNCS[view if view in tabs else tabs[0]]()
        _fill_unused_head(page)
    return run


def _tab_label(name: str) -> str:
    icon = PAGE_ICONS.get(name)
    return f"{icon} {name}" if icon else name


def _fill_unused_head(page: str) -> None:
    """A tab whose view has no title of its own still shows the page's name above the tabs."""
    slot = theme.take_slot()
    if slot is not None:
        slot.markdown(theme.page_head(page), unsafe_allow_html=True)


def _moved(name: str):
    """An old page name (before 0.37.56): opens the page that holds it, on its tab. Old bookmarks and links keep
    working this way."""
    page, tab = nav_groups.where(name)

    def run() -> None:
        target = st.session_state.get("wl_pages", {}).get(page)
        if target is not None:
            st.switch_page(target, query_params={"tab": tab} if tab else None)
    return run


def _url(page: str) -> str:
    """Pages keep the web address they had (Streamlit names it after the page's function); new pages get one from
    their name."""
    fn = PAGE_FUNCS.get(page) or VIEW_FUNCS.get(page)
    return fn.__name__ if fn else page.lower().replace(" ", "_")


def _sections() -> dict:
    """The sidebar sections and their pages, as Streamlit page objects."""
    return {group: [st.Page(PAGE_FUNCS[name] if name in PAGE_FUNCS else _tabbed(name), title=name,
                            icon=PAGE_ICONS[name], url_path=_url(name), default=(name == DEFAULT_PAGE))
                    for name in names]
            for group, names in GROUPS.items()}


def _moved_pages() -> list:
    """Hidden pages under the old names, which send you to the new place."""
    return [st.Page(_moved(name), title=name, icon=PAGE_ICONS[name], url_path=VIEW_FUNCS[name].__name__,
                    visibility="hidden")
            for name in nav_groups.moved()]


def _jump_box(all_pages: dict) -> None:
    """Type part of a page name to go straight to it. At the top of the sidebar from 0.37.53."""
    def go() -> None:
        choice = st.session_state.get("jump_to_page")
        st.session_state["jump_to_page"] = None
        if choice in all_pages:
            st.switch_page(all_pages[choice])
    st.sidebar.selectbox("Jump to page", sorted(all_pages), index=None, placeholder="Jump to page…",
                         key="jump_to_page", on_change=go, label_visibility="collapsed")


def _save_sidebar(**changes) -> None:
    """Pins and folded groups live in the main station's settings, so they stay put when you switch station."""
    with stations.using(stations.MAIN):
        save_settings(replace(load_settings(), **changes))


def _toggle_pin(page: str) -> None:
    with stations.using(stations.MAIN):
        pins = load_settings().pinned_pages
    _save_sidebar(pinned_pages=sidebar.toggle_pin(pins, page))


def _group_changed(group: str) -> None:
    with stations.using(stations.MAIN):
        closed = load_settings().closed_groups
    _save_sidebar(closed_groups=sidebar.set_open(closed, group, bool(st.session_state.get(f"nav_group_{group}"))))


def _sidebar_menu(sections: dict, pages: dict, current: str) -> None:
    """The menu (0.37.53): Jump to page, then pinned pages, then the five groups, each of which folds shut.

    Streamlit's own menu is hidden (position="hidden"), so this one can have the box at the top and folding groups."""
    with stations.using(stations.MAIN):
        cfg = load_settings()
    st.sidebar.markdown(BRAND_HTML, unsafe_allow_html=True)
    _station_picker()  # under the brand from 0.37.63
    _jump_box(pages)
    pins = sidebar.clean_pins(cfg.pinned_pages)
    sb = st.sidebar
    if pins:
        sb.markdown('<div class="wl-nav-head">Pinned</div>', unsafe_allow_html=True)
        for name in pins:
            sb.page_link(pages[name])
    for group, group_pages in sections.items():
        key = f"nav_group_{group}"
        with sb.expander(group, expanded=sidebar.is_open(group, cfg.closed_groups, current), key=key,
                         on_change=_group_changed, args=(group,)):
            for page in group_pages:
                if page.title == current:  # a named box, so the redesign can fill the current page's row (0.37.62)
                    with st.container(key="wl-nav-current"):
                        st.page_link(page)
                else:
                    st.page_link(page)
    pinned = current in pins
    sb.button(("Unpin " if pinned else "Pin ") + current, icon=":material/keep_off:" if pinned else ":material/keep:",
              type="tertiary", key="pin_toggle", on_click=_toggle_pin, args=(current,),
              disabled=not pinned and len(pins) >= sidebar.MAX_PINS,
              help=None if pinned or len(pins) < sidebar.MAX_PINS else f"Up to {sidebar.MAX_PINS} pages can be pinned.")


BRAND_HTML = ('<div class="wl-brand"><svg viewBox="0 0 48 48" width="42" height="42" fill="none" stroke-linecap="round" '
              'stroke-linejoin="round" aria-hidden="true"><circle cx="19" cy="18" r="7" stroke="#f6c445" stroke-width="3"/>'
              '<path d="M19 4v3M8 8l2 2M5 18h3M30 8l-2 2" stroke="#f6c445" stroke-width="3"/>'
              '<path d="M15 39a8 8 0 0 1-.7-16 11 11 0 0 1 21 3.3A6.5 6.5 0 0 1 35 39z" stroke="#38c6ec" stroke-width="3" '
              'fill="#101a28"/></svg><div><b>Weather Lab</b><small>Ecowitt station</small></div></div>')


def _latest_reading():
    try:
        return storage.latest(storage.connect())
    except Exception:
        return None


@st.cache_data(ttl=86400, show_spinner=False)
def _place(lat: float, lon: float, contact: str) -> str:
    """The town the station is in, as the National Weather Service names it ("Springfield, IL"), or ""."""
    from weatherlab import nws
    try:
        return nws.place_name(lat, lon, contact)
    except Exception:
        return ""


def _header_context(page: str) -> None:
    """What the bar under each title says (0.37.62): the station's name, its town and whether readings are live."""
    cfg = load_settings()
    names = {r["id"]: r["name"] for r in stations.all_stations()}
    latest = _latest_reading()
    live = health.age_status(latest[0] if latest else None, time.time())
    place = _place(round(cfg.latitude, 3), round(cfg.longitude, 3), cfg.nws_contact) \
        if cfg.latitude is not None and cfg.longitude is not None else ""
    theme.set_context(page, names.get(stations.current(), ""), place, live)


def _top_right() -> None:
    """Top right of every page (0.37.62): the time of the latest reading and a refresh button."""
    from zoneinfo import ZoneInfo
    from weatherlab import timefmt
    from datetime import datetime
    latest = _latest_reading()
    with st.container(key="wl-topright", horizontal=True):
        if latest:
            try:
                tz = ZoneInfo(load_settings().timezone)
            except Exception:
                tz = None
            st.markdown(f"Last updated {timefmt.time_text(datetime.fromtimestamp(latest[0], tz))}")
        st.button("", icon=":material/refresh:", key="wl_refresh", help="Refresh")


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
      ['meta', {name: 'theme-color', content: '#0b1828'}]
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
    st.iframe(HEAD_SCRIPT, height=1)  # runs the script; same-origin, so it can reach the page's <head>


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
    from weatherlab import settings as settings_module
    if settings_module.load_problem:  # a damaged or partly wrong settings file is said out loud (0.37.55)
        st.warning(settings_module.load_problem, icon=":material/settings_alert:")
    st.markdown(theme.css(theme.is_dark(), cfg.color_scheme, cfg.compact, cfg.large_text), unsafe_allow_html=True)
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    _install_app_head()
    start_poller()
    with stations.using(stations.MAIN):  # the API and sign-in belong to the whole app: always the main station's (0.37.55)
        main_cfg = load_settings()
        api.ensure(main_cfg.api_enabled and main_cfg.allow_network, main_cfg.api_port, main_cfg.tailscale_only)
        allowed = access_gate()
    if not allowed:
        return
    sections = _sections()
    moved = _moved_pages()
    # The sidebar menu is drawn by _sidebar_menu (0.37.53). Old page names (0.37.56) are in the navigation so their
    # addresses still open, but not in the menu.
    nav = st.navigation({**sections, "Moved": moved}, position="hidden")
    pages = {page.title: page for group in sections.values() for page in group}
    pages.update({page.title: page for page in moved})
    st.session_state["wl_pages"] = pages  # lets a page link to another, such as Customize on Home
    _sidebar_menu(sections, pages, nav.title)
    _sidebar_status()
    _header_context(nav.title)
    _top_right()
    nav.run()
    st.caption(f"{APP_NAME} version {APP_VERSION}")


main()
