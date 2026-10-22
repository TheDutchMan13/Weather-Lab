"""Pages under History: daily summaries, records, rankings, rewind, climate charts and my year."""

import calendar
import html
import json
import time
from zoneinfo import ZoneInfo
import plotly.graph_objects as go
import streamlit as st
from datetime import date, datetime, timedelta
from weatherlab import charts, coverage, daily, history, history_compare, record_board, report, stations, storage, theme, units, wind_rose, yearly
from weatherlab.settings import load_settings
from weatherlab.screens.common import _all_days, _tile, _tz, empty_card


def _conv(key: str, values: list, metric: bool) -> list:
    """Each US value converted to the chosen units. None stays None."""
    return [units.convert(key, v, metric) for v in values]


# ---------------------------------------------------------------- Daily
def _typical_caption(db, day: date, summary: dict, metric: bool) -> None:
    """How this day compares with the same date in other years."""
    typical = history_compare.typical(history.all_daily(db), day)
    if typical["years"] < 2 or summary.get("tempf_max") is None or typical["high"] is None:
        return
    scale, unit = (5 / 9, "°C") if metric else (1, "°F")

    def word(change: float, label: str) -> str:
        amount = abs(change) * scale
        if amount < 0.5:
            return f"{label} about typical"
        return f"{label} {amount:.0f} {unit} {'above' if change > 0 else 'below'} typical"

    parts = [word(summary["tempf_max"] - typical["high"], "high")]
    if summary.get("tempf_min") is not None and typical["low"] is not None:
        parts.append(word(summary["tempf_min"] - typical["low"], "low"))
    st.caption(f"Compared with the 7 days around this date in {typical['years']} other years: " + ", ".join(parts) + ".")


def daily_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.page_head("Daily", "One day from your readings. Today shows what has been recorded so far."), unsafe_allow_html=True)
    day = st.date_input("Day", value=today - timedelta(days=1), max_value=today)

    rows = daily.day_rows(db, day, tz)
    if day == today:
        summary, _ = daily.summarize_day(rows, s.latitude or 0.0, s.longitude or 0.0, s.elevation_m, tz)
        note = "Today so far"
    else:
        found = db.execute("SELECT data FROM daily WHERE date = ?", (day.isoformat(),)).fetchone()
        summary = json.loads(found[0]) if found else None
        note = ""

    if not summary:
        empty_card("No summary for this day yet", "A day needs at least 20 readings.")
        return

    if summary.get("estimated"):
        st.caption("This day is an estimate, built from 4-hour readings. A high or a low can fall between readings.")

    metric = units.is_metric(s.units)

    def get(key, fmt="{:g}"):
        v = summary.get(key)
        return "--" if v is None else fmt.format(v)

    def shown(key: str, summary_key: str, decimals: int) -> str:
        return units.format_value(key, summary.get(summary_key), metric, decimals)

    tiles = [
        _tile("High", shown("tempf", "tempf_max", 0), note),
        _tile("Low", shown("tempf", "tempf_min", 0)),
        _tile("Average", shown("tempf", "tempf_avg", 0)),
        _tile("Rain", shown("dailyrainin", "rain_in", 2)),
        _tile("Wind run", shown("miles", "wind_run_mi", 1)),
        _tile("Gust max", shown("windgustmph", "gust_max", 0)),
        _tile("Sun hours", f"{get('sun_hours', '{:.1f}')} h"),
        _tile("Humidity", f"{get('humidity_min', '{:.0f}')}–{get('humidity_max', '{:.0f}')}%"),
    ]
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)

    _typical_caption(db, day, summary, units.is_metric(s.units))

    latest = storage.latest(db) if day == today else None
    st.download_button("Download PDF report", data=report.daily_pdf(day.isoformat(), summary, latest[1] if latest else None, units.is_metric(s.units)),
                       file_name=f"weather_report_{day.isoformat()}.pdf", mime="application/pdf")

    dark = theme.is_dark()
    times = [datetime.fromtimestamp(ts, tz) for ts, _ in rows]
    temp = charts.figure(dark)
    temp.add_trace(go.Scatter(x=times, y=_conv("tempf", [r.get("tempf") for _, r in rows], metric),
                              name=f"Temperature ({units.unit('tempf', metric)})",
                              line=dict(color=charts.MEASURE["temp"])))
    temp.add_trace(go.Scatter(x=times, y=_conv("tempf", [r.get("feelslikef") for _, r in rows], metric),
                              name=f"Feels like ({units.unit('tempf', metric)})",
                              line=dict(color=charts.CHART_COLORS[3], dash="dot")))
    charts.show(temp)

    wind = charts.figure(dark)
    wind.add_trace(go.Scatter(x=times, y=_conv("windspeedmph", [r.get("windspeedmph") for _, r in rows], metric),
                              name=f"Wind ({units.speed_unit(metric)})",
                              line=dict(color=charts.MEASURE["wind"])))
    wind.add_trace(go.Scatter(x=times, y=_conv("windgustmph", [r.get("windgustmph") for _, r in rows], metric),
                              name=f"Gust ({units.speed_unit(metric)})",
                              line=dict(color=charts.MEASURE["gust"], dash="dash")))
    charts.show(wind)


# ---------------------------------------------------------------- History
HISTORY_RANGES = {"Last 30 days": 30, "Last 90 days": 90, "Last year": 365, "All": None}
SUN_COLOUR = "#f4a259"  # the dashboard's sunshine orange


def _date_text(day: date) -> str:
    return f"{day:%b %d, %Y}"


def _highlight_tiles(rows: list, metric: bool) -> list[str]:
    """The summary strip: hottest day, coldest night, average high, rain, wettest day and highest gust."""
    tiles = []

    def best(key, pick):
        found = [(s[key], d) for d, s in rows if s.get(key) is not None]
        return pick(found) if found else None

    hot = best("tempf_max", max)
    if hot:
        tiles.append(theme.strip_tile_html("Hottest day", units.format_value("tempf", hot[0], metric, 1),
                                           _date_text(hot[1]), "bad"))
    cold = best("tempf_min", min)
    if cold:
        tiles.append(theme.strip_tile_html("Coldest night", units.format_value("tempf", cold[0], metric, 1),
                                           _date_text(cold[1]), "info"))
    highs = [s["tempf_max"] for _, s in rows if s.get("tempf_max") is not None]
    if highs:
        hot_days = sum(1 for v in highs if v >= 100)
        tiles.append(theme.strip_tile_html("Average high", units.format_value("tempf", sum(highs) / len(highs), metric, 1),
                                           f"{hot_days} days at {units.format_value('tempf', 100, metric, 0)} or more"))
    rain = [(s["rain_in"], d) for d, s in rows if s.get("rain_in") is not None]
    if rain:
        total = sum(v for v, _ in rain)
        wet_days = sum(1 for v, _ in rain if v > 0)
        tiles.append(theme.strip_tile_html("Total rain", units.format_value("dailyrainin", total, metric, 2),
                                           f"{wet_days} rainy days", "info"))
        wettest = max(rain, key=lambda x: x[0])
        if wettest[0] > 0:
            tiles.append(theme.strip_tile_html("Wettest day", units.format_value("dailyrainin", wettest[0], metric, 2),
                                               _date_text(wettest[1])))
    gust = best("gust_max", max)
    if gust:
        tiles.append(theme.strip_tile_html("Highest gust", units.format_value("windgustmph", gust[0], metric, 0),
                                           _date_text(gust[1]), "warn"))
    return tiles


def _daily_lines(days: list, series: list, title: str, unit_text: str, dark: bool) -> go.Figure:
    """One line per (values, name). Colours follow the dashboard's palette in order."""
    fig = charts.figure(dark)
    for i, (values, name) in enumerate(series):
        fig.add_trace(go.Scatter(x=days, y=values, name=name, mode="lines",
                                 line=dict(color=charts.CHART_COLORS[i % len(charts.CHART_COLORS)], width=1.6)))
    fig.update_layout(title=dict(text=title, x=0, xanchor="left", font=dict(size=13)))
    fig.update_yaxes(title_text=unit_text)
    return fig


def _daily_bars(days: list, values: list, title: str, unit_text: str, colour: str, dark: bool) -> go.Figure:
    fig = charts.figure(dark)
    fig.add_trace(go.Bar(x=days, y=values, name=unit_text, marker_color=colour))
    fig.update_layout(title=dict(text=title, x=0, xanchor="left", font=dict(size=13)))
    fig.update_yaxes(title_text=unit_text)
    return fig


def _history_charts(rows: list, dark: bool, metric: bool) -> None:
    days = [d for d, _ in rows]

    def col(key: str, conv: str | None = None) -> list:
        values = [s.get(key) for _, s in rows]
        return _conv(conv, values, metric) if conv else values

    st.markdown(theme.section_html("Temperature and rain"), unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        charts.show(_daily_lines(days, [(col("tempf_max", "tempf"), "High"), (col("tempf_avg", "tempf"), "Average"),
                                        (col("tempf_min", "tempf"), "Low")],
                                 "Daily temperature", units.unit("tempf", metric), dark))
    with c2:
        charts.show(_daily_bars(days, col("rain_in", "dailyrainin"), "Daily rainfall",
                                units.unit("dailyrainin", metric), charts.MEASURE["rain"], dark))

    st.markdown(theme.section_html("Humidity and pressure"), unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        charts.show(_daily_lines(days, [(col("humidity_max"), "Max"), (col("humidity_min"), "Min")],
                                 "Daily humidity", "%", dark))
    with c4:
        charts.show(_daily_lines(days, [(col("baro_max", "baromrelin"), "Max"), (col("baro_min", "baromrelin"), "Min")],
                                 "Daily pressure", units.unit("baromrelin", metric), dark))

    st.markdown(theme.section_html("Indoors"), unsafe_allow_html=True)
    c5, c6 = st.columns(2)
    with c5:
        if any(s.get("indoor_tempf_max") is not None for _, s in rows):
            charts.show(_daily_lines(days, [(col("indoor_tempf_max", "tempf"), "High"),
                                            (col("indoor_tempf_avg", "tempf"), "Average"),
                                            (col("indoor_tempf_min", "tempf"), "Low")],
                                     "Daily indoor temperature", units.unit("tempf", metric), dark))
        else:
            st.info("Daily indoor temperature: no readings for this period. Check that the indoor sensor is connected.")
    with c6:
        if any(s.get("indoor_humidity_max") is not None for _, s in rows):
            charts.show(_daily_lines(days, [(col("indoor_humidity_max"), "Max"), (col("indoor_humidity_min"), "Min")],
                                     "Daily indoor humidity", "%", dark))
        else:
            st.info("Daily indoor humidity: no readings for this period. Check that the indoor sensor is connected.")

    st.markdown(theme.section_html("Wind and sunshine"), unsafe_allow_html=True)
    c7, c8 = st.columns(2)
    with c7:
        charts.show(_daily_lines(days, [(col("gust_max", "windgustmph"), "Max gust"),
                                        (col("wind_max", "windspeedmph"), "Max wind")],
                                 "Daily wind", units.speed_unit(metric), dark))
    with c8:
        if any(s.get("sun_hours") is not None for _, s in rows):
            charts.show(_daily_bars(days, col("sun_hours"), "Sunshine hours", "hours", SUN_COLOUR, dark))


@st.cache_data(ttl=1800, show_spinner="Working out wind patterns...")  # the wind rows are many; patterns move slowly
def _wind_patterns(start_ts: int, end_ts: int, stamp: int, tz_name: str) -> dict:
    db = storage.connect()
    return wind_rose.patterns(storage.readings_sampled(db, start_ts, end_ts), ZoneInfo(tz_name))


def _wind_section(rows: list, tz, metric: bool, all_time: bool, today: date, dark: bool) -> None:
    """The wind rose for the period, and the prevailing wind for each month. Readings run up to today's midnight."""
    first = rows[0][0]
    start_ts = 0 if all_time else int(datetime(first.year, first.month, first.day, tzinfo=tz).timestamp())
    end_ts = int(datetime(today.year, today.month, today.day, tzinfo=tz).timestamp())
    info = _wind_patterns(start_ts, end_ts, int(time.time() // 1800), tz.key)
    if not info["total"]:
        return
    counts, total = info["counts"], info["total"]
    pct = wind_rose.percentages(counts, total)
    fig = charts.figure(dark, height=420)
    for i in range(len(wind_rose.SPEED_BINS)):
        fig.add_barpolar(r=pct[i], theta=wind_rose.NAMES, name=wind_rose.label(i, metric),
                         marker_color=charts.CHART_COLORS[i % len(charts.CHART_COLORS)])
    fig.update_layout(title=dict(text="Wind rose for this period", x=0, xanchor="left", font=dict(size=13)),
                      polar=dict(barmode="stack", angularaxis=dict(direction="clockwise", rotation=90),
                                 radialaxis=dict(ticksuffix="%")))
    c1, c2 = st.columns(2)
    with c1:
        charts.show(fig)
        top = wind_rose.dominant(counts)
        top_share = round(100 * max(sum(row[i] for row in counts) for i in range(len(wind_rose.NAMES))) / total, 1)
        st.caption(f"Bars point to where the wind comes from. Most often from the {top} ({top_share:g}% of readings). "
                   f"Based on {total:,} readings, about one every ten minutes.")
    with c2:
        st.markdown("**Prevailing wind by month**")
        theme.table([{"Month": m["month"], "Prevailing from": m["from"] or "--",
                      "Share of windy readings (%)": f"{m['share']:.1f}" if m["share"] is not None else "--",
                      "Average speed": units.format_value("windspeedmph", m["avg_mph"], metric, 1)}
                     for m in info["months"]])


def history_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    metric = units.is_metric(s.units)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)
    st.markdown(theme.page_head("Daily history", "Each day's high, low, rain, wind and humidity over the range you choose."), unsafe_allow_html=True)

    choice = st.radio("Time range", list(HISTORY_RANGES), index=2, horizontal=True, key="history_range")
    n = HISTORY_RANGES[choice]
    if n is None:
        rows = [(d, s_) for d, s_ in history.all_daily(db) if d <= yesterday]
    else:
        rows = history.daily_between(db, yesterday - timedelta(days=n - 1), yesterday)
    if not rows:
        empty_card("No daily summaries yet", "Each day's summary is written once that day's readings are in, so the first ones appear after Weather Lab has run for a day.")
        _compare_periods(db, today)
        return

    st.caption(f"{len(rows)} days: {_date_text(rows[0][0])} to {_date_text(rows[-1][0])}")
    tiles = _highlight_tiles(rows, metric)
    with st.container(border=True):
        st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)

    dark = theme.is_dark()
    _history_charts(rows, dark, metric)
    _wind_section(rows, tz, metric, all_time=n is None, today=today, dark=dark)

    latest = storage.latest(db)
    live_rain = latest[1].get("dailyrainin") if latest else None
    totals = history.rain_totals(db, today, live_rain)
    st.markdown(theme.section_html("Rain totals"), unsafe_allow_html=True)
    st.markdown(theme.grid_html([
        _tile("Rain today", f"{totals['today']:.2f} in"),
        _tile("Last 7 days", f"{totals['last_7_days']:.2f} in"),
        _tile("This month", f"{totals['this_month']:.2f} in"),
        _tile("This year", f"{totals['this_year']:.2f} in"),
    ]), unsafe_allow_html=True)

    monthly: dict[str, float] = {}
    for d, s_ in rows:
        if s_.get("rain_in") is not None:
            key = d.strftime("%Y-%m")
            monthly[key] = monthly.get(key, 0.0) + s_["rain_in"]
    with st.expander("Monthly rainfall"):
        theme.table([{"Month": datetime.strptime(k, "%Y-%m").strftime("%b %Y"),
                      "Rain": units.format_value("dailyrainin", v, metric, 2)} for k, v in sorted(monthly.items())])
    with st.expander("Daily table"):
        table_rows = []
        for d, s_ in reversed(rows):
            humidity = (f"{s_['humidity_min']:.0f}–{s_['humidity_max']:.0f}%"
                        if s_.get("humidity_min") is not None and s_.get("humidity_max") is not None else "--")
            table_rows.append({"Date": _date_text(d),
                               "High": units.format_value("tempf", s_.get("tempf_max"), metric, 0),
                               "Low": units.format_value("tempf", s_.get("tempf_min"), metric, 0),
                               "Average": units.format_value("tempf", s_.get("tempf_avg"), metric, 1),
                               "Rain": units.format_value("dailyrainin", s_.get("rain_in"), metric, 2),
                               "Gust max": units.format_value("windgustmph", s_.get("gust_max"), metric, 0),
                               "Sun hours": "--" if s_.get("sun_hours") is None else f"{s_['sun_hours']:.1f}",
                               "Humidity": humidity})
        if theme.is_phone():
            # A phone is too narrow for every column: the table scrolls, but these are the least useful ones.
            # The CSV below still has them all.
            table_rows = [{k: v for k, v in r.items() if k not in ("Average", "Gust max", "Sun hours", "Humidity")}
                          for r in table_rows]
        theme.table(table_rows)
        st.download_button("Download CSV", history.daily_csv(rows).encode(), "weather_daily.csv", "text/csv")

    _compare_periods(db, today)


def _compare_periods(db, today: date) -> None:
    """Two date ranges side by side: totals and averages for each, and the change between them."""
    st.markdown(theme.section_html("Compare two periods"), unsafe_allow_html=True)
    yesterday = today - timedelta(days=1)
    c1, c2 = st.columns(2)
    with c1:
        a_start = st.date_input("First period from", value=yesterday - timedelta(days=29), max_value=yesterday, key="cmp_a_start")
        a_end = st.date_input("First period to", value=yesterday, max_value=yesterday, key="cmp_a_end")
    with c2:
        b_start = st.date_input("Second period from", value=yesterday - timedelta(days=59), max_value=yesterday, key="cmp_b_start")
        b_end = st.date_input("Second period to", value=yesterday - timedelta(days=30), max_value=yesterday, key="cmp_b_end")
    if a_end < a_start or b_end < b_start:
        st.error("An end date is before its start date.")
        return
    a = history_compare.period_stats(history.daily_between(db, a_start, a_end))
    b = history_compare.period_stats(history.daily_between(db, b_start, b_end))
    if not a["days"] and not b["days"]:
        empty_card("Not enough days yet", "Neither period has daily summaries yet.")
        return
    metric = units.is_metric(load_settings().units)
    # (label, key, format, reading key used for units or None, unit text when there is none)
    metrics = [("Days with data", "days", "{:.0f}", None, ""), ("Average high", "avg_high", "{:.1f}", "tempf", ""),
               ("Average low", "avg_low", "{:.1f}", "tempf", ""), ("Highest high", "max_high", "{:.0f}", "tempf", ""),
               ("Lowest low", "min_low", "{:.0f}", "tempf", ""), ("Rain total", "rain_total", "{:.2f}", "dailyrainin", ""),
               ("Rainy days", "rain_days", "{:.0f}", None, ""), ("Sun hours", "sun_hours", "{:.1f}", None, " h")]

    def shown(value, fmt, conv, unit):
        if value is None:
            return "-"
        if conv is None:
            return fmt.format(value) + unit
        return fmt.format(units.convert(conv, value, metric)) + units.suffix(conv, metric)

    body = []
    for label, key, fmt, conv, unit in metrics:
        delta = history_compare.change(a[key], b[key])
        if delta is None:
            delta_text = "-"
        else:
            change = units.convert_change(conv, delta, metric) if conv else delta
            delta_text = ("+" if delta > 0 else "") + fmt.format(change) + (units.suffix(conv, metric) if conv else unit)
        body.append({"Measure": label, "First period": shown(a[key], fmt, conv, unit),
                     "Second period": shown(b[key], fmt, conv, unit), "Change": delta_text})
    theme.table(body)
    st.caption("Change is the first period minus the second.")


def coverage_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    yesterday = datetime.now(tz).date() - timedelta(days=1)
    st.markdown(theme.page_head("Coverage", "How many days have an exact summary, an estimate or nothing at all."), unsafe_allow_html=True)
    days = dict(history.all_daily(db))
    if not days:
        empty_card("Coverage appears once Weather Lab has a finished day to record.")
        return
    options = {"30 days": 30, "90 days": 90, "1 year": 365, "All": None}
    choice = st.radio("Show", list(options), index=2, horizontal=True, key="coverage_span")
    span = options[choice]
    first = min(days)
    start = first if span is None else max(first, yesterday - timedelta(days=span - 1))
    rows = coverage.coverage(days, start, yesterday)
    counted = coverage.counts(rows)
    total = len(rows)
    st.markdown(theme.grid_html([
        _tile("Exact days", str(counted[coverage.EXACT]), f"of {total} days"),
        _tile("Estimated", str(counted[coverage.ESTIMATED]), "from 4-hour readings"),
        _tile("Missing", str(counted[coverage.MISSING]), "no summary"),
        _tile("Covered", f"{coverage.percent(counted, total):.0f}%", "exact or estimated"),
    ]), unsafe_allow_html=True)
    gaps = [(day, state) for day, state in reversed(rows) if state != coverage.EXACT]
    if not gaps:
        st.success("Every day in this range has an exact summary.")
        return
    shown_gaps = gaps[:200]
    theme.table([{"Day": day.strftime("%a %b %d, %Y"), "Status": coverage.LABELS[state]} for day, state in shown_gaps])
    if len(gaps) > len(shown_gaps):
        st.caption(f"Showing the newest 200 of {len(gaps)} days that are not exact.")


# ---------------------------------------------------------------- Records
def _heat_days_section(db, metric: bool) -> None:
    """Days at or above 100 °F and 110 °F, by year."""
    by_year = history_compare.heat_days_by_year(history.all_daily(db))
    if not by_year:
        return
    st.markdown(theme.section_html("Hot days by year"), unsafe_allow_html=True)
    h100 = f"At or above {units.format_value('tempf', 100, metric, 0)}"
    h110 = f"At or above {units.format_value('tempf', 110, metric, 0)}"
    theme.table([{"Year": str(year), h100: str(counts[100]), h110: str(counts[110])} for year, counts in by_year.items()])


def _on_this_day(db, today: date) -> None:
    """The same date in earlier years: high, low and rain."""
    metric = units.is_metric(load_settings().units)
    earlier = history.same_day_before(history.all_daily(db), today)
    if not earlier:
        return
    st.markdown(theme.section_html(f"On {today:%B} {today.day} in earlier years"), unsafe_allow_html=True)
    theme.table([{"Year": str(d.year), "High": units.format_value("tempf", s.get("tempf_max"), metric, 0),
                  "Low": units.format_value("tempf", s.get("tempf_min"), metric, 0),
                  "Rain": units.format_value("dailyrainin", s.get("rain_in"), metric, 2)}
                 for d, s in earlier])


# Colours for the record groups (the dashboard's measure colours) and the dots (highest and lowest).
GROUP_STYLE = {  # group: (icon, top border colour)
    "Temperature": ("🌡️", "#e8a53c"),
    "Rain": ("🌧️", "#4ea1ff"),
    "Wind": ("🌬️", "#3ddc84"),
    "Humidity and pressure": ("💧", "#8a5cf0"),
}
HIGH_DOT, LOW_DOT = "#f07a3c", "#4ea1ff"


def _record_value(r: dict, metric: bool) -> str:
    """A record in the chosen units, such as 118.4°F, 0.62 in, 64 days or 29.53 inHg."""
    if r["unit_key"]:
        shown = units.convert(r["unit_key"], r["value"], metric)
        return f"{shown:.{r['dec']}f}{units.suffix(r['unit_key'], metric)}"
    return f"{r['value']:.{r['dec']}f}{r['plain']}"


def _highlights_html(items: list, metric: bool) -> str:
    """The six numbers that sum up the station, on a gradient card."""
    tiles = "".join(
        '<div style="background:rgba(8,14,24,0.28);border:1px solid rgba(255,255,255,0.14);border-radius:12px;'
        'padding:12px 14px;min-height:96px">'
        f'<div style="display:flex;justify-content:space-between;gap:8px;font-size:14px;opacity:0.9">'
        f'<span>{html.escape(r["title"])}</span><span>{r["icon"]}</span></div>'
        f'<div style="font-size:28px;font-weight:650;margin-top:6px">{html.escape(_record_value(r, metric))}</div>'
        f'<div style="font-size:13px;opacity:0.85;margin-top:2px">'
        f'{html.escape(r["when"])}</div></div>'
        for r in items)
    return ('<div style="background:linear-gradient(120deg,#1f3d5e 0%,#3c5878 45%,#b8683a 100%);border-radius:16px;'
            'padding:18px 18px 16px;color:#ffffff;margin:8px 0 18px">'
            '<div style="font-size:12px;letter-spacing:0.12em;text-transform:uppercase;opacity:0.85">Record highlights</div>'
            '<div style="font-size:22px;font-weight:650;margin:2px 0 14px">Six numbers that sum up your station</div>'
            f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px">{tiles}</div>'
            '</div>')


def _group_html(title: str, rows: list, metric: bool, dark: bool) -> str:
    """One card of records: a coloured top border, a dot for highest or lowest, the value and the date."""
    p = theme.palette(dark)
    icon, colour = GROUP_STYLE[title]
    body = []
    for r in rows:
        dot = HIGH_DOT if r["high"] else LOW_DOT
        badge = ('<span style="margin-left:8px;background:#2fbf71;color:#ffffff;font-size:10px;font-weight:700;'
                 'letter-spacing:0.06em;border-radius:999px;padding:2px 7px;vertical-align:middle">NEW</span>'
                 if r["new"] else "")
        body.append(
            f'<div style="display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid {p["line"]}">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{dot};flex:none"></span>'
            f'<span style="flex:1;font-size:15px">{html.escape(r["label"])}{badge}</span>'
            f'<span style="font-weight:700;font-size:16px;white-space:nowrap">{html.escape(_record_value(r, metric))}</span>'
            f'<span style="font-size:13px;color:{p["muted"]};text-align:right;min-width:96px">'
            f'{html.escape(r["when"])}</span></div>')
    return (f'<div style="background:{p["card"]};border:1px solid {p["line"]};border-top:4px solid {colour};'
            f'border-radius:14px;padding:14px 16px 6px">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:4px">'
            f'<span style="font-size:18px;font-weight:650">{icon} {html.escape(title)}</span>'
            f'<span style="font-size:13px;color:{p["muted"]}">{len(rows)} records</span></div>'
            + "".join(body) + '</div>')


def records_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    db = storage.connect()
    st.markdown(theme.page_head("Weather records", "All-time records for your station, with the day each one happened."), unsafe_allow_html=True)
    days = history.all_daily(db)
    if not days:
        empty_card("Records aren't ready yet", "Records appear once there are a few days of summaries to compare. They fill in as Weather Lab keeps collecting.")
        return
    today = datetime.now(_tz(s)).date()
    board = record_board.board(days, today)
    st.caption(f"All-time records for your station · {len(board['records'])} records")
    if board["highlights"]:
        st.markdown(_highlights_html(board["highlights"], metric), unsafe_allow_html=True)
    st.markdown(theme.section_html("Every record", "grouped by type · NEW = set in the last 30 days"),
                unsafe_allow_html=True)
    cards = "".join(_group_html(title, rows, metric, dark) for title, rows in board["groups"])
    st.markdown('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px">'
                + cards + '</div>', unsafe_allow_html=True)
    st.markdown(f'<div style="font-size:13px;color:{theme.palette(dark)["muted"]};margin:10px 0 4px">'
                f'<span style="color:{HIGH_DOT}">●</span> highest / most &nbsp; '
                f'<span style="color:{LOW_DOT}">●</span> lowest / least</div>', unsafe_allow_html=True)
    st.caption("Records cover only the time since this app started collecting data. Records marked estimate come from 4-hour readings.")
    _on_this_day(storage.connect(), datetime.now(_tz(s)).date())
    _heat_days_section(storage.connect(), units.is_metric(s.units))


def _fmt(key: str, value, metric: bool, decimals: int = 0) -> str:
    """A reading in the chosen units, or a dash when there is no value."""
    return "-" if value is None else units.format_value(key, value, metric, decimals)


RANKINGS = {  # label: (summary key, "max" or "min", units key or None, unit text, decimals)
    "Warmest days": ("tempf_max", "max", "tempf", "", 0),
    "Coldest nights": ("tempf_min", "min", "tempf", "", 0),
    "Wettest days": ("rain_in", "max", "dailyrainin", "", 2),
    "Windiest days": ("gust_max", "max", "windgustmph", "", 0),
    "Highest UV": ("uvi", "max", None, "UV", 1),
    "Sunniest days": ("sun_hours", "max", None, "hours", 1),
}


def rankings_page() -> None:
    s = load_settings()
    metric = units.is_metric(s.units)
    st.markdown(theme.page_head("Rankings", "The top 10 days for the measure you choose."), unsafe_allow_html=True)
    days = _all_days(stations.current())
    if not days:
        empty_card("Rankings appear once there are daily summaries.", "Each day's summary is written once that day's readings are in.")
        return
    choice = st.selectbox("Rank the days by", list(RANKINGS), key="rank_choice")
    key, kind, unit_key, unit_text, decimals = RANKINGS[choice]
    top = yearly.ranking(days, key, kind, 10)
    if not top:
        empty_card("Nothing to rank yet", "No days have that measure yet.")
        return
    rows = []
    for i, (day, value) in enumerate(top, 1):
        text = _fmt(unit_key, value, metric, decimals) if unit_key else f"{value:.{decimals}f} {unit_text}".strip()
        rows.append({"#": str(i), "Day": day.strftime("%a %b %d, %Y"), choice: text})
    theme.table(rows)


def rewind_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    today = datetime.now(_tz(s)).date()
    st.markdown(theme.page_head("Rewind", "What the same day looked like in earlier years."), unsafe_allow_html=True)
    days = _all_days(stations.current())
    picked = st.date_input("Day and month to look up", value=today, max_value=today, key="rewind_day")
    rows = yearly.on_this_day(days, picked.month, picked.day)
    if not rows:
        empty_card(f"No summaries for {picked.strftime('%B %d')} yet", "Each day's summary is built from that day's readings.")
        return
    tiles = []
    for day, sm in rows:
        note = f"Rain {_fmt('dailyrainin', sm['rain_in'], metric, 2)}" if sm.get("rain_in") is not None else ""
        value = f"{_fmt('tempf', sm.get('tempf_max'), metric)} / {_fmt('tempf', sm.get('tempf_min'), metric)}"
        tiles.append(_tile(str(day.year), value, note))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    with_high = [(day, sm) for day, sm in rows if sm.get("tempf_max") is not None]
    fig = charts.figure(dark, height=300)
    fig.add_trace(go.Bar(x=[str(day.year) for day, _ in with_high],
                         y=[units.convert("tempf", sm["tempf_max"], metric) for _, sm in with_high],
                         name=f"High ({units.unit('tempf', metric)})", marker_color=charts.MEASURE["temp"]))
    charts.show(fig)


def _year_over_year(dark: bool, metric: bool) -> None:
    """Daily highs for two years drawn over each other, so this year can be compared with last year."""
    days = _all_days(stations.current())
    years = sorted({d.year for d, _ in days})
    if len(years) < 2:
        return
    st.markdown(theme.section_html("Daily highs, one year against another"), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        year_a = st.selectbox("First year", years, index=len(years) - 1, key="yoy_a")
    with right:
        year_b = st.selectbox("Second year", years, index=len(years) - 2, key="yoy_b")
    fig = charts.figure(dark, height=340)
    for i, year in enumerate([year_a, year_b]):
        pts = [(date(2000, d.month, d.day), summary.get("tempf_max")) for d, summary in days if d.year == year]
        fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[units.convert("tempf", p[1], metric) for p in pts],
                                 name=str(year), line=dict(color=charts.CHART_COLORS[i * 3])))
    fig.update_xaxes(tickformat="%b")
    charts.show(fig)


def climate_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    st.markdown(theme.page_head("Climate charts", "Monthly averages and totals across all of your years of data."), unsafe_allow_html=True)
    table = yearly.monthly(_all_days(stations.current()))
    if not table:
        empty_card("Monthly charts appear once there are daily summaries.", "Each day's summary is written once that day's readings are in.")
        return
    years = sorted(table)
    months = [calendar.month_abbr[m] for m in range(1, 13)]

    def cell(year: int, month: int, field: str):
        return table.get(year, {}).get(month, {}).get(field)

    temp_unit = units.unit("tempf", metric)
    heat = charts.figure(dark, height=max(260, 40 * len(years) + 90))
    heat.add_trace(go.Heatmap(
        z=[[units.convert("tempf", cell(y, m, "temp"), metric) for m in range(1, 13)] for y in years],
        x=months, y=[str(y) for y in years], colorscale="RdYlBu_r", colorbar=dict(title=temp_unit)))
    heat.update_yaxes(autorange="reversed")
    st.markdown(theme.section_html(f"Average temperature by month ({temp_unit})"), unsafe_allow_html=True)
    charts.show(heat)

    rain = charts.figure(dark, height=340)
    for year in years:
        rain.add_trace(go.Bar(x=months, name=str(year),
                              y=[units.convert("dailyrainin", cell(year, m, "rain"), metric) for m in range(1, 13)]))
    rain.update_layout(barmode="group")
    st.markdown(theme.section_html(f"Rain by month ({units.unit('dailyrainin', metric)})"), unsafe_allow_html=True)
    charts.show(rain)
    _year_over_year(dark, metric)


def my_year_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    st.markdown(theme.page_head("My year", "A review of one calendar year at a time."), unsafe_allow_html=True)
    days = _all_days(stations.current())
    years = sorted({day.year for day, _ in days}, reverse=True)
    if not years:
        empty_card("A year in review appears once there are daily summaries.")
        return
    year = st.selectbox("Year", years, key="my_year_pick")
    summary = yearly.year_summary(days, year, hot_f=100.4 if metric else 100.0, freeze_f=32.0)
    tiles = [_tile("Days with data", str(summary["days"])),
             _tile("Rain total", _fmt("dailyrainin", summary["rain"], metric, 2)),
             _tile("Rainy days", str(summary["rainy_days"]))]
    if summary["hottest"]:
        day, value = summary["hottest"]
        tiles.append(_tile("Hottest day", _fmt("tempf", value, metric), day.strftime("%b %d")))
    if summary["coldest"]:
        day, value = summary["coldest"]
        tiles.append(_tile("Coldest low", _fmt("tempf", value, metric), day.strftime("%b %d")))
    if summary["windiest"]:
        day, value = summary["windiest"]
        tiles.append(_tile("Windiest gust", _fmt("windgustmph", value, metric), day.strftime("%b %d")))
    tiles.append(_tile("Days at 38°C or hotter" if metric else "Days at 100°F or hotter", str(summary["hot_days"])))
    tiles.append(_tile("Days at or below freezing", str(summary["freezing"])))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    monthly_rain = yearly.monthly(days).get(year, {})
    if monthly_rain:
        months = sorted(monthly_rain)
        fig = charts.figure(dark, height=300)
        fig.add_trace(go.Bar(x=[calendar.month_abbr[m] for m in months],
                             y=[units.convert("dailyrainin", monthly_rain[m]["rain"], metric) for m in months],
                             name=f"Rain ({units.unit('dailyrainin', metric)})", marker_color=charts.MEASURE["rain"]))
        charts.show(fig)
