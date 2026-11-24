"""Compare stations (0.37.34): two of your stations side by side, now and over the last 24 hours."""

import html
import time
from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from weatherlab import charts, health, hero, line_icons, sparks, station_compare, stations, storage, theme, units, wind_rose, wx_icons
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


def _swap() -> None:
    a, b = st.session_state.get("compare_a"), st.session_state.get("compare_b")
    if a and b:
        st.session_state["compare_a"], st.session_state["compare_b"] = b, a


def _hourly_line(readings: list, key: str, metric: bool, colour: str) -> str:
    hours: dict = {}
    for ts, d in readings:
        if isinstance(d.get(key), (int, float)):
            hours.setdefault(int(ts // 3600), []).append(d[key])
    values = [units.convert(key, sum(v) / len(v), metric) for _, v in sorted(hours.items())]
    return sparks.spark_svg(values, colour, h=34)


def _station_card(summary: dict, readings: list, metric: bool) -> str:
    """One station's head card: name, live state, temperature, sky icon and the 24-hour high and low."""
    state, age = health.age_status(time.time() - summary["age_seconds"] if summary["age_seconds"] is not None else None, time.time())
    word, colour = theme.LIVE_WORDS.get(state, theme.LIVE_WORDS["none"])
    now = summary["now"]
    temp = now.get("tempf")
    last = readings[-1][1] if readings else {}
    sunny = (last.get("solarradiation") or 0) > 20 if "solarradiation" in last else True
    kind = "clear_day" if sunny else "night"
    hi_lo = ""
    if summary["high"] is not None:
        hi_lo = (f'<div style="font-size:16px;margin-top:4px">High {units.convert("tempf", summary["high"], metric):.0f}° '
                 f'&nbsp;/&nbsp; Low {units.convert("tempf", summary["low"], metric):.0f}°</div>')
    temp_html = (f'<div class="wl-ct">{units.convert("tempf", temp, metric):.0f}<sup>{units.unit("tempf", metric)}</sup></div>'
                 if temp is not None else '<div class="wl-ct">--</div>')
    tail = f" · updated {html.escape(age)}" if state != "none" else ""
    sky = f"{hero._clouds_svg(kind == 'night')} center/cover no-repeat, {hero.sky_bg(kind, hero.GRADS[kind])}"
    return (f'<div class="wl-panel wl-cmphead"><div class="wl-hx-sky" style="position:absolute;inset:0 0 0 55%;background:{sky};'
            f'-webkit-mask-image:linear-gradient(90deg,transparent,#000 50%);mask-image:linear-gradient(90deg,transparent,#000 50%);opacity:.85"></div>'
            f'<div style="position:relative;z-index:1;width:100%"><div style="display:flex;justify-content:space-between;align-items:center">'
            f'<span class="wl-cn">{line_icons.icon("station", 22)}{html.escape(summary["name"])}</span>'
            f'<span style="font-size:14px"><b style="color:{colour}">● {word}</b>{tail}</span></div>'
            f'<div style="display:flex;align-items:center;gap:18px;margin-top:10px">{wx_icons.now_icon(kind, 76)}{temp_html}'
            f'<div style="border-left:1px solid rgba(160,190,220,.3);padding-left:18px">{hi_lo}</div></div></div></div>')


COMPARE_ROWS = [("tempf", "Temperature", "Now", "thermo", "#f07a5a"), ("humidity", "Humidity", "Relative humidity", "drop", "#7cc4ff"),
                ("windspeedmph", "Wind", "Speed and direction", "wind", "#7cc4ff"), ("dailyrainin", "Rain (today)", "Total accumulation", "rain", "#7cc4ff"),
                ("baromrelin", "Pressure", "Sea-level pressure", "gauge", "#7cc4ff")]


def compare_stations_page() -> None:
    """Compare stations (0.37.63, the redesign): a head card for each station, the readings side by side with their
    last 24 hours and the gap, then both temperature lines and the rain totals."""
    st.markdown(theme.page_head("Compare stations", "Two of your stations side by side: now, and the last 24 hours."),
                unsafe_allow_html=True)
    rows = stations.all_stations()
    if len(rows) < 2:
        empty_card("Add a second station to compare",
                   "Open Stations in the Settings section, add a station, then set its Ecowitt address in Settings, under Station.")
        return
    ids = [r["id"] for r in rows]
    current = stations.current()
    if st.session_state.get("compare_a") not in ids:
        st.session_state["compare_a"] = current if current in ids else ids[0]
    left, mid, right = st.columns([5, 1, 5], vertical_alignment="bottom")
    with left:
        first = st.selectbox("Station A", ids, format_func=stations.name_of, key="compare_a", label_visibility="collapsed")
    others = [i for i in ids if i != first]
    if st.session_state.get("compare_b") not in others:
        st.session_state["compare_b"] = others[0]
    with mid:
        st.button("", icon=":material/swap_horiz:", key="compare_swap", on_click=_swap, help="Swap the stations",
                  use_container_width=True)
    with right:
        second = st.selectbox("Station B", others, format_func=stations.name_of, key="compare_b", label_visibility="collapsed")

    s = load_settings()
    metric = units.is_metric(s.units)
    now = time.time()
    a, a_readings = _read(first, now)
    b, b_readings = _read(second, now)
    ca, cb = st.columns(2)
    ca.markdown(_station_card(a, a_readings, metric), unsafe_allow_html=True)
    cb.markdown(_station_card(b, b_readings, metric), unsafe_allow_html=True)
    if not a["count"] and not b["count"]:
        empty_card("Neither station has readings in the last 24 hours")
        return

    out = []
    for key, label, sub, icon, colour in COMPARE_ROWS:
        va, vb = a["now"].get(key), b["now"].get(key)
        if va is None and vb is None:
            continue
        diff = station_compare._signed(key, va - vb, metric) if va is not None and vb is not None else "--"
        tone = "#3ddc84" if diff.startswith("+") else "#7cc4ff" if diff.startswith("−") else "#9db0c4"
        arrow = "▲ " if diff.startswith("+") else "▼ " if diff.startswith("−") else ""
        shown = diff.lstrip("+−") + ("%" if key == "humidity" and diff not in ("same", "--") else "")

        def val(v, readings):
            text = station_compare._text(key, v, metric)
            direction = readings[-1][1].get("winddir") if readings else None
            if key == "windspeedmph" and v is not None and direction is not None and v >= 1:
                text += " " + wind_rose.NAMES[round(direction / 22.5) % 16]
            return text
        out.append(f'<div><div style="display:flex;align-items:center;gap:12px">{line_icons.icon(icon, 26, colour)}'
                   f'<div><b>{html.escape(label)}</b><small>{html.escape(sub)}</small></div></div>'
                   f'<span class="wl-cv">{html.escape(val(va, a_readings))}</span><span class="wl-sp">{_hourly_line(a_readings, key, metric, "#f6c445")}</span>'
                   f'<span><span class="wl-delta" style="color:{tone}">{arrow}{html.escape(shown)}</span></span>'
                   f'<span class="wl-cv">{html.escape(val(vb, b_readings))}</span><span class="wl-sp">{_hourly_line(b_readings, key, metric, "#38c6ec")}</span></div>')
    st.markdown(f'<div class="wl-panel wl-cmprows" style="padding:6px 0;margin-bottom:14px">{"".join(out)}</div>', unsafe_allow_html=True)

    tz = _tz(s)
    chart_col, rain_col = st.columns([2.2, 1], gap="medium")
    with chart_col, st.container(border=True):
        fig = charts.figure(theme.is_dark(), height=290)
        for summary, readings, colour in ((a, a_readings, "#38c6ec"), (b, b_readings, "#f6c445")):
            points = [(datetime.fromtimestamp(ts, tz), units.convert("tempf", d["tempf"], metric))
                      for ts, d in readings if isinstance(d.get("tempf"), (int, float))]
            if points:
                fig.add_trace(go.Scatter(x=[p[0] for p in points], y=[p[1] for p in points], name=summary["name"],
                                         mode="lines", line=dict(color=colour, width=2.4)))
        fig.update_layout(title=dict(text="24-hour temperature", x=0, xanchor="left", font=dict(size=16)),
                          legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
        fig.update_yaxes(title_text=units.unit("tempf", metric))
        if fig.data:
            charts.show(fig, use_container_width=True)
    with rain_col:
        ra, rb = a["now"].get("dailyrainin"), b["now"].get("dailyrainin")
        fmt = lambda v: "--" if v is None else units.format_value("dailyrainin", v, metric, 2)
        diff = station_compare._signed("dailyrainin", ra - rb, metric) if ra is not None and rb is not None else "--"
        st.markdown('<div class="wl-panel" style="padding:16px 20px"><div class="wl-ptitle">Rain totals <span class="wl-note">(today)</span></div>'
                    '<div class="wl-statrows" style="background:transparent;border:none;margin:0">'
                    f'<div>{line_icons.icon("station", 22)}<div><b style="font-weight:600">{html.escape(a["name"])}</b></div><span class="wl-big" style="font-size:20px">{fmt(ra)}</span></div>'
                    f'<div>{line_icons.icon("station", 22)}<div><b style="font-weight:600">{html.escape(b["name"])}</b></div><span class="wl-big" style="font-size:20px">{fmt(rb)}</span></div>'
                    f'<div>{line_icons.icon("drop", 22, "#7cc4ff")}<div><b style="font-weight:600">Difference</b></div><span class="wl-big" style="font-size:20px;color:#3ddc84">{html.escape(diff)}</span></div>'
                    '</div></div>', unsafe_allow_html=True)

    states = [health.age_status(now - x["age_seconds"] if x["age_seconds"] is not None else None, now)[0] for x in (a, b)]
    good = all(x == "ok" for x in states)
    text = "both stations reporting" if good else "; ".join(
        f'{x["name"]}: {"reporting" if st_ == "ok" else "late" if st_ == "slow" else "not reporting"}' for x, st_ in zip((a, b), states))
    colour = "#3ddc84" if good else "#f6c445"
    st.markdown(f'<div class="wl-panel wl-health" style="margin-top:14px">{line_icons.icon("check" if good else "alert", 26, colour, 2.2)}'
                f'<span><b style="color:{colour}">Station health:</b> {html.escape(text)}</span></div>', unsafe_allow_html=True)
