"""Compare stations (0.37.34): two of your stations side by side, now and over the last 24 hours."""

import html
import time
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from weatherlab import charts, station_compare, stations, storage, theme, units
from weatherlab.screens.common import _tz, empty_card
from weatherlab.settings import load_settings


def _read(station_id: str, now: float) -> tuple[dict, list]:
    """One station's summary and its last 24 hours of readings, read from that station's own database."""
    with stations.using(station_id):
        db = storage.connect()
        try:
            readings = storage.readings_between(db, now - 86400, now + 1)
        finally:
            db.close()
    return station_compare.summarize(stations.name_of(station_id), readings, now), readings


def compare_stations_page() -> None:
    st.markdown(theme.page_head("Compare stations", "Two of your stations side by side: now, and the last 24 hours."),
                unsafe_allow_html=True)
    rows = stations.all_stations()
    if len(rows) < 2:
        empty_card("Add a second station to compare",
                   "Open Stations in the Settings section, add a station, then set its Ecowitt address under Setup.")
        return
    ids = [r["id"] for r in rows]
    current = stations.current()
    left, right = st.columns(2)
    with left:
        first = st.selectbox("Station A", ids, index=ids.index(current) if current in ids else 0,
                             format_func=stations.name_of, key="compare_a")
    others = [i for i in ids if i != first]
    with right:
        second = st.selectbox("Station B", others, format_func=stations.name_of, key="compare_b")

    s = load_settings()
    metric = units.is_metric(s.units)
    now = time.time()
    a, a_readings = _read(first, now)
    b, b_readings = _read(second, now)

    st.markdown(f'<div class="wl-card" style="font-size:1.25rem;font-weight:600">'
                f'{html.escape(station_compare.headline(a, b, metric))}</div>', unsafe_allow_html=True)
    st.caption(f"{a['name']}: last reading {station_compare.age_text(a['age_seconds'])}. "
               f"{b['name']}: last reading {station_compare.age_text(b['age_seconds'])}.")

    table = station_compare.rows(a, b, metric)
    if not table:
        empty_card("Neither station has readings in the last 24 hours")
        return
    theme.table([{"": r["label"], a["name"]: r["a"], b["name"]: r["b"], "Difference (A − B)": r["diff"]}
                 for r in table])

    tz = _tz(s)
    fig = charts.figure(theme.is_dark(), height=300)
    for i, (summary, readings) in enumerate(((a, a_readings), (b, b_readings))):
        points = [(datetime.fromtimestamp(ts, tz), units.convert("tempf", d["tempf"], metric))
                  for ts, d in readings if isinstance(d.get("tempf"), (int, float))]
        if points:
            fig.add_trace(go.Scatter(x=[p[0] for p in points], y=[p[1] for p in points], name=summary["name"],
                                     mode="lines", line=dict(color=charts.CHART_COLORS[i], width=1.8)))
    fig.update_layout(title=dict(text="Temperature, last 24 hours", x=0, xanchor="left", font=dict(size=13)))
    fig.update_yaxes(title_text=units.unit("tempf", metric))
    if fig.data:
        charts.show(fig, use_container_width=True)
