"""Pages under History: daily summaries, records, rankings, rewind, climate charts and my year."""

import calendar
import html
import json
import plotly.graph_objects as go
import streamlit as st
from datetime import date, datetime, timedelta
from weatherlab import charts, coverage, daily, history, history_compare, report, stations, storage, theme, units, yearly
from weatherlab.settings import load_settings
from weatherlab.screens.common import _all_days, _table, _tile, _tz, empty_card


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
    st.markdown(theme.title_html("Daily"), unsafe_allow_html=True)
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
        st.info("No summary for this day yet. A day needs at least 20 readings.")
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
                              line=dict(color=charts.CHART_COLORS[0])))
    temp.add_trace(go.Scatter(x=times, y=_conv("tempf", [r.get("feelslikef") for _, r in rows], metric),
                              name=f"Feels like ({units.unit('tempf', metric)})",
                              line=dict(color=charts.CHART_COLORS[3], dash="dot")))
    charts.show(temp)

    wind = charts.figure(dark)
    wind.add_trace(go.Scatter(x=times, y=_conv("windspeedmph", [r.get("windspeedmph") for _, r in rows], metric),
                              name=f"Wind ({units.speed_unit(metric)})",
                              line=dict(color=charts.CHART_COLORS[1])))
    wind.add_trace(go.Scatter(x=times, y=_conv("windgustmph", [r.get("windgustmph") for _, r in rows], metric),
                              name=f"Gust ({units.speed_unit(metric)})",
                              line=dict(color=charts.CHART_COLORS[4], dash="dot")))
    charts.show(wind)


# ---------------------------------------------------------------- History
def history_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("History"), unsafe_allow_html=True)

    latest = storage.latest(db)
    live_rain = latest[1].get("dailyrainin") if latest else None
    totals = history.rain_totals(db, today, live_rain)
    st.markdown(theme.grid_html([
        _tile("Rain today", f"{totals['today']:.2f} in"),
        _tile("Last 7 days", f"{totals['last_7_days']:.2f} in"),
        _tile("This month", f"{totals['this_month']:.2f} in"),
        _tile("This year", f"{totals['this_year']:.2f} in"),
    ]), unsafe_allow_html=True)

    options = {"7 days": 7, "30 days": 30, "90 days": 90, "1 year": 365}
    choice = st.radio("Range", list(options), index=1, horizontal=True)
    n = options[choice]
    rows = history.daily_between(db, today - timedelta(days=n), today - timedelta(days=1))
    if not rows:
        st.info("No daily summaries yet. Each day's summary is written once that day's readings are in, so the first ones appear after Weather Lab has run for a day.")
    else:
        _history_charts(rows, theme.is_dark())
    _compare_periods(db, today)


def _history_charts(rows: list, dark: bool) -> None:
    metric = units.is_metric(load_settings().units)
    tu, ru = units.unit("tempf", metric), units.unit("dailyrainin", metric)
    days = [d for d, _ in rows]
    temps = charts.figure(dark)
    temps.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("tempf_max") for _, r in rows], metric),
                               name=f"High ({tu})", line=dict(color=charts.CHART_COLORS[4])))
    temps.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("tempf_min") for _, r in rows], metric),
                               name=f"Low ({tu})", line=dict(color=charts.CHART_COLORS[0])))
    charts.show(temps)

    rain = charts.figure(dark)
    rain.add_trace(go.Bar(x=days, y=_conv("dailyrainin", [r.get("rain_in", 0.0) for _, r in rows], metric),
                          name=f"Rain ({ru})", marker_color=charts.CHART_COLORS[0]))
    charts.show(rain)
    if any(r.get("indoor_tempf_avg") is not None for _, r in rows):
        indoor = charts.figure(dark)
        indoor.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("indoor_tempf_max") for _, r in rows], metric),
                                    name=f"Indoor high ({tu})", line=dict(color=charts.CHART_COLORS[4])))
        indoor.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("indoor_tempf_avg") for _, r in rows], metric),
                                    name=f"Indoor average ({tu})", line=dict(color=charts.CHART_COLORS[2])))
        indoor.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("indoor_tempf_min") for _, r in rows], metric),
                                    name=f"Indoor low ({tu})", line=dict(color=charts.CHART_COLORS[0])))
        charts.show(indoor)
    if any(r.get("indoor_humidity_max") is not None for _, r in rows):
        damp = charts.figure(dark)
        damp.add_trace(go.Scatter(x=days, y=[r.get("indoor_humidity_max") for _, r in rows], name="Indoor humidity high (%)",
                                  line=dict(color=charts.CHART_COLORS[1])))
        damp.add_trace(go.Scatter(x=days, y=[r.get("indoor_humidity_min") for _, r in rows], name="Indoor humidity low (%)",
                                  line=dict(color=charts.CHART_COLORS[3], dash="dot")))
        charts.show(damp)


def _compare_periods(db, today: date) -> None:
    """Two date ranges side by side: totals and averages for each, and the change between them."""
    st.markdown("**Compare two periods**")
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
        body.append([html.escape(label), html.escape(shown(a[key], fmt, conv, unit)),
                     html.escape(shown(b[key], fmt, conv, unit)), html.escape(delta_text)])
    st.markdown(_table(["", "First period", "Second period", "Change"], body, theme.is_dark()), unsafe_allow_html=True)
    st.caption("Change is the first period minus the second.")


def coverage_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    yesterday = datetime.now(tz).date() - timedelta(days=1)
    st.markdown(theme.title_html("Coverage"), unsafe_allow_html=True)
    days = dict(history.all_daily(db))
    if not days:
        st.info("Coverage appears once Weather Lab has a finished day to record.")
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
    body = [[html.escape(day.strftime("%a %b %d, %Y")), html.escape(coverage.LABELS[state])]
            for day, state in shown_gaps]
    st.markdown(_table(["Day", "Status"], body, theme.is_dark()), unsafe_allow_html=True)
    if len(gaps) > len(shown_gaps):
        st.caption(f"Showing the newest 200 of {len(gaps)} days that are not exact.")


# ---------------------------------------------------------------- Records
def _heat_days_section(db, metric: bool) -> None:
    """Days at or above 100 °F and 110 °F, by year."""
    by_year = history_compare.heat_days_by_year(history.all_daily(db))
    if not by_year:
        return
    st.markdown(theme.section_html("Hot days by year"), unsafe_allow_html=True)
    body = [[html.escape(str(year)), html.escape(str(counts[100])), html.escape(str(counts[110]))]
            for year, counts in by_year.items()]
    st.markdown(_table(["Year", f"At or above {units.format_value('tempf', 100, metric, 0)}",
                        f"At or above {units.format_value('tempf', 110, metric, 0)}"], body, theme.is_dark()),
                unsafe_allow_html=True)


def _on_this_day(db, today: date) -> None:
    """The same date in earlier years: high, low and rain."""
    metric = units.is_metric(load_settings().units)
    earlier = history.same_day_before(history.all_daily(db), today)
    if not earlier:
        return
    st.markdown(theme.section_html(f"On {today:%B} {today.day} in earlier years"), unsafe_allow_html=True)
    body = [[html.escape(str(d.year)), html.escape(units.format_value("tempf", s.get("tempf_max"), metric, 0)),
             html.escape(units.format_value("tempf", s.get("tempf_min"), metric, 0)),
             html.escape(units.format_value("dailyrainin", s.get("rain_in"), metric, 2))]
            for d, s in earlier]
    st.markdown(_table(["Year", "High", "Low", "Rain"], body, theme.is_dark()), unsafe_allow_html=True)


def _record_text(r: dict, metric: bool) -> str:
    """A record in the chosen units, such as "95°F" or "35.0°C"."""
    key = history.RECORD_UNIT.get(r["key"])
    if key is None:
        return f"{r['value']:g}{r['unit']}"
    shown = units.convert(key, r["value"], metric)
    return (f"{shown:.1f}" if metric else f"{r['value']:g}") + units.suffix(key, metric)


def records_page() -> None:
    st.markdown(theme.title_html("Records"), unsafe_allow_html=True)
    items = history.records(storage.connect())
    if not items:
        empty_card("Records aren't ready yet", "Records appear once there are a few days of summaries to compare. They fill in as Weather Lab keeps collecting.")
        return
    metric = units.is_metric(load_settings().units)
    tiles = [_tile(r["label"], _record_text(r, metric),
                   r["date"].strftime("%b %d, %Y") + (" · estimate" if r.get("estimated") else "")) for r in items]
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    st.caption("Records cover only the time since this app started collecting data. Records marked estimate come from 4-hour readings.")
    _on_this_day(storage.connect(), datetime.now(_tz(load_settings())).date())
    _heat_days_section(storage.connect(), units.is_metric(load_settings().units))


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
    metric, dark = units.is_metric(s.units), theme.is_dark()
    st.markdown(theme.title_html("Rankings"), unsafe_allow_html=True)
    days = _all_days(stations.current())
    if not days:
        st.info("Rankings appear once there are daily summaries. Each day's summary is written once that day's readings are in.")
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
        rows.append([str(i), day.strftime("%a %b %d, %Y"), text])
    st.markdown(_table(["#", "Day", choice], rows, dark), unsafe_allow_html=True)


def rewind_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    today = datetime.now(_tz(s)).date()
    st.markdown(theme.title_html("Rewind"), unsafe_allow_html=True)
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
                         name=f"High ({units.unit('tempf', metric)})", marker_color=charts.CHART_COLORS[3]))
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
    st.markdown(theme.title_html("Climate charts"), unsafe_allow_html=True)
    table = yearly.monthly(_all_days(stations.current()))
    if not table:
        st.info("Monthly charts appear once there are daily summaries. Each day's summary is written once that day's readings are in.")
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
    st.markdown(theme.title_html("My year"), unsafe_allow_html=True)
    days = _all_days(stations.current())
    years = sorted({day.year for day, _ in days}, reverse=True)
    if not years:
        st.info("A year in review appears once there are daily summaries.")
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
                             name=f"Rain ({units.unit('dailyrainin', metric)})", marker_color=charts.CHART_COLORS[0]))
        charts.show(fig)
