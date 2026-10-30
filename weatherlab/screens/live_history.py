"""History window for the Home page: click a reading's button for its chart over 24 hours, 7 days or 30 days,
with the highest, lowest and average. Charts use the app's palette."""

import time
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from weatherlab import charts, history_series, stations, storage, theme, units, timefmt
from weatherlab.screens.common import _tz, empty_card
from weatherlab.settings import load_settings

PERIODS = {"24 hours": 1, "7 days": 7, "30 days": 30}
# key: (name shown, colour from charts.MEASURE, decimal places)
MEASURES = {
    "tempf": ("Temperature", "temp", 1),
    "feelslikef": ("Feels like", "temp", 1),
    "humidity": ("Humidity", "humidity", 0),
    "windspeedmph": ("Wind", "wind", 1),
    "baromrelin": ("Pressure", "pressure", 2),
    "dewpointf": ("Dew point", "dew", 1),
    "uv": ("UV index", "uv", 1),
    "windgustmph": ("Gust", "gust", 1),
    "dailyrainin": ("Rain today", "rain", 2),
    "solarradiation": ("Solar", "uv", 0),
    "tempinf": ("Indoor temp", "temp", 1),
    "humidityin": ("Indoor humidity", "humidity", 0),
}
# Units that units.suffix doesn't cover
SUFFIX = {"humidity": "%", "humidityin": "%", "solarradiation": " W/m²"}


@st.cache_data(ttl=600, show_spinner=False)
def _points(key: str, days: int, stamp: int, station: str) -> list:
    """One reading per ten minutes for the key over the period. The stamp changes every ten minutes."""
    now = time.time()
    raw = [(ts, r[key]) for ts, r in storage.readings_between(storage.connect(), now - days * 86400, now + 1)
           if r.get(key) is not None]
    return history_series.thin(raw, 600)


def request(key: str) -> None:
    """Called by a button: remembers which reading to show. The window itself is drawn by show_pending()."""
    st.session_state["live_history"] = key


def _clear() -> None:
    st.session_state.pop("live_history", None)


def show_pending(keys=None) -> None:
    """Keeps the window open while the Home page refreshes, until the user closes it. With keys, only those readings'
    windows open here (0.37.51), so two refreshing parts of a page never open the same window twice."""
    key = st.session_state.get("live_history")
    if keys is not None and key not in keys:
        return
    if key in MEASURES:
        _open(key)


@st.dialog("History", width="large", on_dismiss=_clear)
def _open(key: str) -> None:
    s = load_settings()
    tz = _tz(s)
    metric = units.is_metric(s.units)
    label, colour, decimals = MEASURES[key]
    period = st.segmented_control("Period", list(PERIODS), default="24 hours", key=f"hist_period_{key}") or "24 hours"
    stamp = int(time.time() // 600)
    points = _points(key, PERIODS[period], stamp, stations.current())
    values = [(ts, units.convert(key, v, metric)) for ts, v in points]
    found = history_series.summary(values)
    if found is None:
        empty_card(f"No {label.lower()} readings for this period yet.")
        return
    suffix = SUFFIX.get(key, units.suffix(key, metric))

    def shown(v: float) -> str:
        return f"{v:.{decimals}f}{suffix}"

    def when(ts: float) -> str:
        return timefmt.stamp(datetime.fromtimestamp(ts, tz))

    tiles = [theme.tile_html("Highest", f"{shown(found['high'][1])}"),
             theme.tile_html("Lowest", f"{shown(found['low'][1])}"),
             theme.tile_html("Average", shown(found["average"])),
             theme.tile_html("Now", shown(values[-1][1]))]
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    st.caption(f"Highest {when(found['high'][0])}. Lowest {when(found['low'][0])}.")
    fig = charts.figure(theme.is_dark())
    charts.night_bands(fig, s.latitude, s.longitude, tz, values[0][0], values[-1][0], theme.is_dark())
    fig.add_trace(go.Scatter(x=[datetime.fromtimestamp(ts, tz) for ts, _ in values], y=[v for _, v in values],
                             mode="lines", name=label, line=dict(color=charts.MEASURE[colour], width=2)))
    charts.show(fig)
