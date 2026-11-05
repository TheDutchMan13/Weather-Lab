"""Helpers shared by the sidebar in app.py and the pages in weatherlab/screens."""

import html
import streamlit as st
from datetime import datetime
from weatherlab import history, nws, stations, storage, theme
from weatherlab.poller import Poller
from weatherlab.settings import Settings
from zoneinfo import ZoneInfo


@st.cache_resource
def _collectors() -> dict:
    """The background collector for each station, started once and kept for as long as the app runs."""
    return {}


def start_poller() -> Poller:
    """The collector for the station on screen. Starts one for each station that doesn't have one running yet,
    and stops the ones for stations that were removed."""
    collectors = _collectors()
    ids = stations.ids()
    for sid in list(collectors):
        if sid not in ids:
            collectors.pop(sid).stop()
    for sid in ids:
        if sid not in collectors or not collectors[sid].is_alive():
            collectors[sid] = Poller(sid)
            collectors[sid].start()
    return collectors[stations.current()]


def with_picked_station(fn):
    """For parts of a page that run on their own: auto-refreshing fragments and button callbacks (0.37.55).

    Streamlit runs those on a fresh thread that starts on the main station, without app.py's station picker, so a
    second station's Home switched to the main station's readings after 30 seconds, and its layout buttons saved to
    the main station. This sets the station picked in the sidebar first."""
    import functools

    @functools.wraps(fn)
    def run(*args, **kwargs):
        from weatherlab import stations
        picked = st.session_state.get("station_pick", stations.MAIN)
        stations.set_current(picked if picked in stations.ids() else stations.MAIN)
        return fn(*args, **kwargs)
    return run


def on_this_pc() -> bool:
    """True when this page is open on the PC that runs Weather Lab (0.37.55). Set by the sign-in gate in app.py."""
    return bool(st.session_state.get("on_pc", True))


def pc_only(what: str) -> bool:
    """For settings that could take over the PC if someone else changed them (the password, the Android token,
    updates, the off-site folder, network access): True on this PC. Elsewhere it says why it can't be changed here
    and returns False."""
    if on_this_pc():
        return True
    st.caption(f":material/lock: {what} can only be changed on the PC that runs Weather Lab, so a phone or another "
               "device can't use it to take over this PC.")
    return False


def _clock(ts: float) -> str:
    from weatherlab import timefmt
    return timefmt.time_text(datetime.fromtimestamp(ts), seconds=True)


def empty_card(message: str, detail: str = "") -> None:
    """The card a page shows when it has no data yet: what is missing, and when it fills in if known."""
    with st.container(border=True):
        st.markdown(f"**{message}**")
        if detail:
            st.caption(detail)


def confirm_button(label: str, key: str, question: str, confirm_label: str, disabled: bool = False) -> bool:
    """A button that asks first. The first click shows the question with Confirm and Cancel. True only on a confirmed click."""
    armed = f"ask_{key}"
    if st.session_state.get(armed):
        st.caption(question)
        yes, no = st.columns(2)
        if yes.button(confirm_label, key=f"yes_{key}", type="primary"):
            st.session_state[armed] = False
            return True
        if no.button("Cancel", key=f"no_{key}"):
            st.session_state[armed] = False
            st.rerun()
        return False
    if st.button(label, key=key, disabled=disabled):
        st.session_state[armed] = True
        st.rerun()
    return False


def clear_key_button(name: str, label: str, saved: bool) -> bool:
    """Marks a saved key to be removed when Save is pressed, and offers to keep it. True while it is marked."""
    flag = f"clear_key_{name}"
    if not saved:
        st.session_state[flag] = False
        return False
    if st.session_state.get(flag):
        st.warning(f"The saved {label} will be removed when you press Save.")
        if st.button(f"Keep the {label}", key=f"keep_key_{name}"):
            st.session_state[flag] = False
            st.rerun()
        return True
    if st.button(f"Clear the saved {label}", key=f"clear_key_btn_{name}"):
        st.session_state[flag] = True
        st.rerun()
    return False


def _tile(label: str, value: str, note: str = "") -> str:
    body = theme.tile_html(html.escape(label), html.escape(value))
    if note:
        body = body.replace("</div></div>", f'</div><div class="wl-label">{html.escape(note)}</div></div>')
    return body


def _tz(s: Settings) -> ZoneInfo:
    try:
        return ZoneInfo(s.timezone)
    except Exception:
        return ZoneInfo("UTC")


# ---------------------------------------------------------------- History: rankings, rewind, climate, my year
@st.cache_data(ttl=600, show_spinner=False)
def _all_days(station: str) -> list:
    """Every daily summary as (date, summary) pairs, remembered for ten minutes."""
    return history.all_daily(storage.connect())


# ---------------------------------------------------------------- Forecast
@st.cache_data(ttl=86400, show_spinner=False)
def _points(lat: float, lon: float, contact: str) -> dict:
    return nws.points(lat, lon, contact)


@st.cache_data(ttl=1800, show_spinner=False)
def _hourly(url: str, contact: str) -> list[dict]:
    return nws.forecast_hourly(url, contact)


def _alert_box(a: dict) -> str:
    color = nws.SEVERITY_COLORS.get(a["severity"], nws.SEVERITY_COLORS["Unknown"])
    expires = f"Until {html.escape(a['expires'][:16].replace('T', ' '))}" if a["expires"] else ""
    return (f'<div class="wl-tile" style="border-left:4px solid {color};border-radius:8px;margin-bottom:8px">'
            f'<div class="wl-label" style="color:{color}">{html.escape(a["severity"].upper())}</div>'
            f'<div class="wl-value" style="font-size:16px">{html.escape(a["event"])}</div>'
            f'<div class="wl-label">{html.escape(a["headline"])}</div>'
            f'<div class="wl-label">{expires}</div></div>')


def _start_of_today(s: Settings) -> float:
    return datetime.now(_tz(s)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def _degrees(x, unit: str = "°F", fmt: str = ".0f") -> str:
    return "--" if x is None else f"{format(x, fmt)}{unit}"


