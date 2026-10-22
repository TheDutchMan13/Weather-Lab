"""Pages under Explore: rain calendar, rain events, questions, unusual days and replay."""

import calendar
import html
import plotly.graph_objects as go
import streamlit as st
from datetime import date, datetime, timedelta
from weatherlab import ask, charts, history, history_compare, rain_calendar, rain_events, replay, stations, storage, theme, units
from weatherlab.settings import load_settings
from weatherlab.screens.common import _all_days, _table, _tile, _tz, empty_card


def ask_page() -> None:
    s = load_settings()
    metric = units.is_metric(s.units)
    today = datetime.now(_tz(s)).date()
    st.markdown(theme.title_html("Ask"), unsafe_allow_html=True)
    question = st.text_input("Ask about your history", key="ask_question",
                             placeholder="for example: wettest month, or rain in March 2026")
    if not question.strip():
        st.caption("Try: " + ask.EXAMPLES + ".")
        return
    st.write(ask.answer(question, _all_days(stations.current()), today, metric))


@st.cache_data(ttl=600, show_spinner=False)
def _unusual_days(metric: bool = False, station: str = "main") -> list:
    """Days in the last year that stand out, newest first: (date, reasons)."""
    days = _all_days(stations.current())
    cutoff = date.today() - timedelta(days=365)
    found = []
    for day, summary in days:
        if day < cutoff:
            continue
        reasons = history_compare.unusual(day, summary, days, metric=metric)
        if reasons:
            found.append((day, reasons))
    return list(reversed(found))


def unusual_page() -> None:
    st.markdown(theme.title_html("Unusual days"), unsafe_allow_html=True)
    metric = units.is_metric(load_settings().units)
    if metric:
        st.caption("A day is listed when its high or low is 5.6 °C or more from the usual value for that date, "
                   "or when it had 25 mm or more of rain. Temperature comparisons need at least two earlier years. "
                   "Temperatures are in °C.")
    else:
        st.caption("A day is listed when its high or low is 10 °F or more from the usual value for that date, "
                   "or when it had 1 inch or more of rain. Temperature comparisons need at least two earlier years. "
                   "Temperatures are in °F.")
    found = _unusual_days(metric, stations.current())
    if not found:
        empty_card("Nothing stands out in the last year.")
        return
    body = [[html.escape(day.strftime("%a %b %d, %Y")), html.escape("; ".join(reasons))] for day, reasons in found]
    st.markdown(_table(["Day", "Why it stands out"], body, theme.is_dark()), unsafe_allow_html=True)


def rain_events_page() -> None:
    s = load_settings()
    tz = _tz(s)
    metric = units.is_metric(s.units)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("Rain events"), unsafe_allow_html=True)
    options = {"7 days": 7, "30 days": 30}
    choice = st.radio("Range", list(options), index=1, horizontal=True, key="rain_events_range")
    start = datetime.combine(today - timedelta(days=options[choice]), datetime.min.time(), tzinfo=tz).timestamp()
    end = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=tz).timestamp()
    found = rain_events.events(storage.readings_between(db, start, end))
    if not found:
        empty_card("No rain in this range")
        return
    wettest = max(found, key=lambda e: e["inches"])
    total = sum(e["inches"] for e in found)
    st.markdown(theme.grid_html([
        _tile("Rain events", str(len(found))),
        _tile("Total", units.format_value("dailyrainin", total, metric, 2)),
        _tile("Wettest event", units.format_value("dailyrainin", wettest["inches"], metric, 2),
              datetime.fromtimestamp(wettest["start"], tz).strftime("%b %d, %I:%M %p")),
    ]), unsafe_allow_html=True)
    body = []
    for e in reversed(found):
        minutes = max(1, round((e["end"] - e["start"]) / 60))
        length = f"{minutes // 60} h {minutes % 60} min" if minutes >= 60 else f"{minutes} min"
        peak = units.convert("dailyrainin", e["peak_rate"], metric)
        peak_text = f"{peak:.{1 if metric else 2}f} {units.unit('dailyrainin', metric)}/hr"
        body.append([html.escape(datetime.fromtimestamp(e["start"], tz).strftime("%a %b %d, %I:%M %p")),
                     html.escape(length), html.escape(units.format_value("dailyrainin", e["inches"], metric, 2)),
                     html.escape(peak_text)])
    st.markdown(_table(["Started", "Length", "Rain", "Peak rate"], body, theme.is_dark()), unsafe_allow_html=True)


# ---------------------------------------------------------------- Rain calendar
def _month_html(year: int, month: int, rain: dict, p: dict, metric: bool = False) -> str:
    cell = f"padding:4px 0;border:1px solid {p['line']};text-align:center;font-size:12px;"
    head = "".join(f'<th style="{cell}color:{p["muted"]};font-weight:600">{d}</th>' for d in "SMTWTFS")
    body = []
    for week in rain_calendar.month_cells(year, month, rain):
        cells = []
        for item in week:
            if item is None:
                cells.append(f'<td style="{cell}"></td>')
                continue
            day, value = item
            shade = ""
            detail = ""
            if value is not None:
                if value > 0:
                    pct = min(100, 25 + value * 30)
                    shade = f"background:color-mix(in srgb, {p['accent']} {pct:.0f}%, transparent);"
                shown = units.convert("dailyrainin", value, metric)
                detail = f'<br><span style="font-size:11px;color:{p["muted"]}">{shown:.{1 if metric else 2}f}</span>'
            cells.append(f'<td style="{cell}{shade}">{day}{detail}</td>')
        body.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div style="margin-bottom:12px"><div class="wl-label">{calendar.month_name[month]}</div>'
            f'<table style="width:100%;border-collapse:collapse"><tr>{head}</tr>{"".join(body)}</table></div>')


def _year_heatmap(year: int, rain: dict, p: dict, dark: bool, metric: bool = False) -> go.Figure:
    jan1 = date(year, 1, 1)
    days = 366 if calendar.isleap(year) else 365
    offset = (jan1.weekday() + 1) % 7  # Sunday is row 0
    weeks = (days + offset - 1) // 7 + 1
    z = [[None] * weeks for _ in range(7)]
    text = [[""] * weeks for _ in range(7)]
    tick_cols, tick_text = [], []
    for i in range(days):
        day = jan1 + timedelta(days=i)
        col, row = divmod(i + offset, 7)
        value = rain.get(day)
        z[row][col] = value
        text[row][col] = f"{day:%b %d}: " + ("no data" if value is None else
                                             units.format_value("dailyrainin", value, metric, 1 if metric else 2))
        if day.day == 1:
            tick_cols.append(col)
            tick_text.append(calendar.month_abbr[day.month])
    peak = max((v for d, v in rain.items() if d.year == year and v is not None), default=0) or 1
    fig = charts.figure(dark, height=240)
    fig.add_trace(go.Heatmap(z=z, text=text, hoverinfo="text", zmin=0, zmax=peak, showscale=False,
                             colorscale=[[0, p["surface"]], [1, p["accent"]]], xgap=2, ygap=2))
    fig.update_xaxes(showgrid=False, tickmode="array", tickvals=tick_cols, ticktext=tick_text)
    fig.update_yaxes(showgrid=False, tickmode="array", tickvals=list(range(7)),
                     ticktext=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], autorange="reversed")
    return fig


def rain_calendar_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    dark = theme.is_dark()
    p = theme.palette(dark, s.color_scheme)
    metric = units.is_metric(s.units)
    st.markdown(theme.title_html("Rain calendar"), unsafe_allow_html=True)
    rain = {day: data.get("rain_in") for day, data in history.all_daily(db)}
    if not any(v is not None for v in rain.values()):
        empty_card("The rain calendar fills in once there are daily summaries.", "Each day's rain is added after that day's readings are in.")
        return

    totals, rainy = rain_calendar.year_totals(rain)
    current = datetime.now(tz).year
    years = sorted(set(totals) | {current})
    year = st.selectbox("Year", years, index=years.index(current), key="rain-year")
    this_year = {d: v for d, v in rain.items() if d.year == year and v is not None}
    wettest = max(this_year.items(), key=lambda kv: kv[1], default=None)
    st.markdown(theme.grid_html([
        _tile(f"Rain in {year}", units.format_value("dailyrainin", totals.get(year, 0.0), metric, 2)),
        _tile("Rainy days", str(rainy.get(year, 0))),
        _tile("Wettest day", "--" if wettest is None else units.format_value("dailyrainin", wettest[1], metric, 2),
              "" if wettest is None else f"{wettest[0]:%b %d}"),
    ]), unsafe_allow_html=True)

    st.markdown(theme.section_html("Year at a glance"), unsafe_allow_html=True)
    charts.show(_year_heatmap(year, rain, p, dark, metric))
    st.markdown(theme.section_html("Month by month"), unsafe_allow_html=True)
    st.caption(f"Each day shows its rain in {'millimetres' if metric else 'inches'}. Darker days got more rain.")
    for first in (1, 4, 7, 10):
        cols = st.columns(3)
        for col, month in zip(cols, range(first, first + 3)):
            with col:
                st.markdown(_month_html(year, month, rain, p, metric), unsafe_allow_html=True)

    st.markdown(theme.section_html("Year totals"), unsafe_allow_html=True)
    rain_dec = 1 if metric else 2
    noaa_rain = _noaa_rain_by_year(storage.connect())
    unit = units.unit("dailyrainin", metric)

    def shown(inches: float) -> str:
        return f"{units.convert('dailyrainin', inches, metric):.{rain_dec}f}"

    theme.table([{"Year": y,
                  f"Rain from your readings ({unit})": shown(totals[y]) if y in totals else "--",
                  f"Rain from NOAA ({unit})": shown(noaa_rain[y]) if y in noaa_rain else "--",
                  "Rainy days": rainy.get(y, 0) if y in totals else "--"}
                 for y in sorted(set(totals) | set(noaa_rain), reverse=True)])


def _noaa_rain_by_year(db) -> dict:
    """Yearly rain in inches from the NOAA history, for years where NOAA has rain values."""
    by_year: dict = {}
    for day, values in storage.noaa_days_between(db, "0000-01-01", "9999-12-31"):
        if values.get("rain_in") is not None:
            year = int(day[:4])
            by_year[year] = by_year.get(year, 0.0) + values["rain_in"]
    return by_year


# ---------------------------------------------------------------- Replay
def _shown(reading: dict, key: str, metric: bool, unit: str = "") -> str:
    value = reading.get(key)
    if value is None:
        return "--"
    if units.converts(key):
        return units.format_value(key, value, metric)
    return f"{value:g}{unit}"


def replay_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    metric = units.is_metric(s.units)
    st.markdown(theme.title_html("Replay"), unsafe_allow_html=True)
    today = datetime.now(tz).date()
    day = st.date_input("Day", value=today, max_value=today, key="replay-day")
    start, end = replay.day_bounds(day, tz)
    rows = storage.readings_between(db, start, end)
    if not rows:
        empty_card(f"No readings for {day:%b %d, %Y}", "Pick another day.")
        return
    if len(rows) > 1:
        index = st.slider("Move through the day", 0, len(rows) - 1, len(rows) - 1,
                          key=f"replay-{day.isoformat()}", label_visibility="collapsed")
    else:
        index = 0
    ts, reading = rows[index]
    when = datetime.fromtimestamp(ts, tz)
    st.caption(f"Showing {when:%a %b %d, %Y at %I:%M %p}. Drag the slider to move through the day.")
    st.markdown(theme.grid_html([
        _tile("Outdoor", _shown(reading, "tempf", metric)),
        _tile("Humidity", _shown(reading, "humidity", metric, "%")),
        _tile("Wind", _shown(reading, "windspeedmph", metric)),
        _tile("Gust", _shown(reading, "windgustmph", metric)),
        _tile("Rain today", _shown(reading, "dailyrainin", metric)),
        _tile("Pressure", _shown(reading, "baromrelin", metric)),
    ]), unsafe_allow_html=True)

    fig = charts.figure(theme.is_dark())
    fig.add_scatter(x=[datetime.fromtimestamp(t, tz) for t, _ in rows],
                    y=[units.convert("tempf", r.get("tempf"), metric) for _, r in rows],
                    mode="lines", name="Outdoor", line=dict(color=charts.MEASURE["temp"]))
    fig.add_scatter(x=[when], y=[units.convert("tempf", reading.get("tempf"), metric)], mode="markers",
                    name="Selected time", marker=dict(size=12, color=charts.CHART_COLORS[4]))
    fig.update_yaxes(title_text=units.unit("tempf", metric))
    charts.show(fig)
