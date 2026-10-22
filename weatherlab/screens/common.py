"""Helpers shared by the sidebar in app.py and the pages in weatherlab/screens."""

import html
import streamlit as st
import time
from datetime import datetime
from weatherlab import health, history, nws, stations, storage, theme, wx_icons
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


def _clock(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def empty_card(message: str, detail: str = "") -> None:
    """The card a page shows when it has no data yet: what is missing, and when it fills in if known."""
    with st.container(border=True):
        st.markdown(f"**{message}**")
        if detail:
            st.caption(detail)


def freshness_line() -> None:
    """One line under the Live title: whether the station is reporting, and how long ago its last reading came in."""
    try:
        latest = storage.latest(storage.connect())
        state, text = health.age_status(latest[0] if latest else None, time.time())
    except Exception:
        return
    color, label = {"ok": ("#1e8a4c", "Station online"), "slow": ("#b45309", "Readings delayed"),
                    "silent": ("#b42318", "Station not reporting"),
                    "none": ("#5b6675", "Waiting for the first reading")}[state]
    detail = f" · {html.escape(text)}" if state != "none" else ""
    st.markdown(f'<div style="font-size:14px;color:#5b6675;margin:-8px 0 8px">'
                f'<span style="color:{color}">●</span> {label}{detail}</div>', unsafe_allow_html=True)


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


def _now_tile(short: str, night: bool) -> str:
    icon = wx_icons.forecast_icon(short, night, 64)
    return (f'<div class="wl-tile"><div style="display:flex;align-items:center;gap:12px">{icon}'
            f'<div style="min-width:0"><div class="wl-label">Right now</div>'
            f'<div class="wl-value" style="font-size:18px">{html.escape(short)}</div></div></div></div>')


# ---------------------------------------------------------------- History: rankings, rewind, climate, my year
@st.cache_data(ttl=600, show_spinner=False)
def _all_days(station: str) -> list:
    """Every daily summary as (date, summary) pairs, remembered for ten minutes."""
    return history.all_daily(storage.connect())


def _table(headers: list, rows: list, dark: bool) -> str:
    """A plain table in the theme's colours. Cell text must already be escaped."""
    p = theme.palette(dark)
    head = "".join(f'<th style="text-align:left;padding:6px 8px;font-weight:600;color:{p["muted"]}">{h}</th>'
                   for h in headers)
    body = "".join("<tr>" + "".join(f'<td style="padding:6px 8px;border-top:1px solid {p["line"]}">{c}</td>'
                                    for c in row) + "</tr>" for row in rows)
    return (f'<table style="width:100%;border-collapse:collapse;color:{p["text"]};font-size:14px">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")


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
