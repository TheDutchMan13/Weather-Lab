"""Pages under Outlook: forecast, heat, wind, sun and astronomy."""

import html
import streamlit as st
import time
from datetime import datetime, timedelta, timezone
from weatherlab import astro, charts, forecast_check, forecast_view, heat_safety, history, nws, storage, sun_uv, theme, units, wind_rose
from weatherlab.settings import Settings, load_settings
from weatherlab.screens.common import _alert_box, _clock, _hourly, _points, _start_of_today, _table, _tile, _tz, empty_card, start_poller


@st.cache_data(ttl=600, show_spinner=False)
def _alerts(lat: float, lon: float, contact: str) -> list[dict]:
    return nws.alerts(lat, lon, contact)


@st.cache_data(ttl=1800, show_spinner=False)
def _daily(url: str, contact: str) -> list[dict]:
    return nws.forecast_daily(url, contact)


def _forecast_accuracy(db, s: Settings) -> None:
    """How far the saved forecast highs were from what actually happened."""
    metric = units.is_metric(s.units)
    scale, unit = (5 / 9, "°C") if metric else (1, "°F")

    def delta(x: float) -> str:
        return f"{x * scale:.1f} {unit}"

    forecasts = storage.forecast_highs(db)
    actuals = {d: summary["tempf_max"] for d, summary in history.all_daily(db) if summary.get("tempf_max") is not None}
    rows = forecast_check.compare(forecasts, actuals)[:60]
    stats = forecast_check.accuracy(rows)
    st.markdown(theme.section_html("How accurate the forecast has been"), unsafe_allow_html=True)
    error = start_poller().status.forecast_error
    if error:
        st.caption(f"Couldn't save the forecast: {error}")
    if not stats["days"]:
        st.caption("This check starts once Weather Lab has saved a forecast and a day has finished. Forecasts are saved every three hours.")
        return
    sign = "+" if stats["bias"] > 0 else ""
    st.markdown(theme.grid_html([
        _tile("Average miss", delta(stats["mae"]), f"last {stats['days']} days"),
        _tile("Forecast bias", sign + delta(stats["bias"]), "plus means it ran high"),
    ]), unsafe_allow_html=True)
    body = [[html.escape(d.strftime("%a %b %d")), html.escape(units.format_value("tempf", f, metric, 0)),
             html.escape(units.format_value("tempf", a, metric, 0)), html.escape(delta(diff))]
            for d, f, a, diff in rows[:14]]
    st.markdown(_table(["Day", "Forecast high", "Actual high", "Forecast minus actual"], body, theme.is_dark()),
                unsafe_allow_html=True)


def _rain_accuracy(db, s: Settings) -> None:
    """How often rain was forecast, and how often it actually fell."""
    pops = storage.forecast_pops(db)
    rained = {d: (summary.get("rain_in") or 0.0) >= 0.01 for d, summary in history.all_daily(db)}
    stats = forecast_check.rain_summary(pops, rained)
    if not stats["wet_days"] and not stats["dry_days"]:
        return
    st.markdown(theme.section_html("How accurate the rain chance has been"), unsafe_allow_html=True)
    st.markdown(theme.grid_html([
        _tile("Forecast 50% or more", f"{stats['wet_rained']} of {stats['wet_days']}", "days it rained"),
        _tile("Forecast under 50%", f"{stats['dry_rained']} of {stats['dry_days']}", "days it rained"),
    ]), unsafe_allow_html=True)


def forecast_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html("Forecast"), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        st.info("Set your latitude and longitude on the Setup page.")
        return
    contact = s.nws_contact

    try:
        alerts = _alerts(s.latitude, s.longitude, contact)
        if alerts:
            st.markdown("".join(_alert_box(a) for a in alerts), unsafe_allow_html=True)
        else:
            st.markdown(theme.grid_html([_tile("Weather alerts", "None active")]), unsafe_allow_html=True)
        pts = _points(s.latitude, s.longitude, contact)
        periods = _daily(pts["forecast"], contact)
        hourly = _hourly(pts["forecastHourly"], contact) if pts.get("forecastHourly") else []
    except nws.NwsError as exc:
        st.error(str(exc))
        return

    metric = units.is_metric(s.units)
    now = datetime.now(tz)
    views = forecast_view.overview_html(hourly, s.latitude, s.longitude, tz, metric, len(alerts), now)
    views += forecast_view.days_html(periods, tz, metric, now.date())
    if views:
        st.markdown(forecast_view.STYLE + views, unsafe_allow_html=True)
    _forecast_accuracy(storage.connect(), s)
    _rain_accuracy(storage.connect(), s)


WIND_PERIODS = {"Last 24 hours": 1, "Last 7 days": 7, "Last 30 days": 30}


def heat_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    metric = units.is_metric(s.units)
    db = storage.connect()
    st.markdown(theme.title_html("Heat safety"), unsafe_allow_html=True)
    latest = storage.latest(db)
    if latest is None:
        empty_card("No readings yet", "Heat safety fills in once the station has reported.")
        return
    _, data = latest
    now = heat_safety.status(data.get("tempf"), data.get("humidity"))
    today = storage.readings_between(db, _start_of_today(s), time.time() + 1)
    series = [(ts, r.get("tempf"), heat_safety.heat_index(r.get("tempf"), r.get("humidity"))) for ts, r in today]
    peak = max((x for x in series if x[2] is not None), key=lambda x: x[2], default=None)
    st.markdown(theme.grid_html([
        _tile("Heat index now", units.format_value("heat_index", now["heat_index"], metric, 0), now["level"]),
        _tile("Air temperature", units.format_value("tempf", data.get("tempf"), metric, 0), "right now"),
        _tile("Highest heat index today", units.format_value("heat_index", peak[2] if peak else None, metric, 0),
              _clock(peak[0]) if peak else "no data yet"),
    ]), unsafe_allow_html=True)
    if now["advice"]:
        show = st.warning if now["level"] in ("Extreme caution", "Danger", "Extreme danger") else st.info
        show(now["advice"])
    fig = charts.figure(dark)
    xs = [datetime.fromtimestamp(ts, _tz(s)) for ts, _, _ in series]
    fig.add_scatter(x=xs, y=[units.convert("tempf", t, metric) for _, t, _ in series], name="Air temperature", mode="lines",
                    line=dict(color=charts.CHART_COLORS[0]))
    fig.add_scatter(x=xs, y=[units.convert("heat_index", h, metric) for _, _, h in series], name="Heat index", mode="lines",
                    line=dict(color=charts.CHART_COLORS[1]))
    charts.show(fig)
    st.caption("Heat index combines air temperature and humidity. This is general guidance, not medical advice.")


def wind_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    metric = units.is_metric(s.units)
    db = storage.connect()
    st.markdown(theme.title_html("Wind"), unsafe_allow_html=True)
    period = st.segmented_control("Period", list(WIND_PERIODS), default="Last 24 hours",
                                  key="wind_period", label_visibility="collapsed") or "Last 24 hours"
    end = time.time()
    rows = [r for _, r in storage.readings_between(db, end - WIND_PERIODS[period] * 86400, end + 1)]
    counts, total = wind_rose.rose(rows)
    if total == 0:
        empty_card("No wind readings yet", "Wind readings appear once the station has reported for this period.")
        return
    speeds = [r["windspeedmph"] for r in rows if r.get("windspeedmph") is not None]
    gusts = [r["windgustmph"] for r in rows if r.get("windgustmph") is not None]
    st.markdown(theme.grid_html([
        _tile("Average wind", units.format_value("windspeedmph", sum(speeds) / len(speeds), metric, 1)),
        _tile("Strongest gust", units.format_value("windgustmph", max(gusts) if gusts else None, metric, 0)),
        _tile("Most common direction", wind_rose.dominant(counts)),
    ]), unsafe_allow_html=True)
    pct = wind_rose.percentages(counts, total)
    fig = charts.figure(dark, height=480)
    for i in range(len(wind_rose.SPEED_BINS)):
        fig.add_barpolar(r=pct[i], theta=wind_rose.NAMES, name=wind_rose.label(i, metric),
                         marker_color=charts.CHART_COLORS[i % len(charts.CHART_COLORS)])
    fig.update_layout(polar=dict(barmode="stack", angularaxis=dict(direction="clockwise", rotation=90),
                                 radialaxis=dict(ticksuffix="%")))
    charts.show(fig)
    st.caption("Each wedge shows how often the wind came from that direction, coloured by speed.")


def sun_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    db = storage.connect()
    st.markdown(theme.title_html("Sun and UV"), unsafe_allow_html=True)
    latest = storage.latest(db)
    if latest is None:
        empty_card("No readings yet", "Sun and UV fill in once the station has reported.")
        return
    _, data = latest
    end = time.time()
    week = storage.readings_between(db, end - 7 * 86400, end + 1)
    today_start = _start_of_today(s)
    sun_week = [(ts, r.get("solarradiation")) for ts, r in week]
    sun_today = [x for x in sun_week if x[0] >= today_start]
    uv_today = [(ts, r.get("uv")) for ts, r in week if ts >= today_start]
    uv_peak = max((u for _, u in uv_today if u is not None), default=None)
    uv_now = data.get("uv")
    st.markdown(theme.grid_html([
        _tile("UV index now", "--" if uv_now is None else f"{uv_now:.1f}"),
        _tile("UV peak today", "--" if uv_peak is None else f"{uv_peak:.1f}"),
        _tile("Sunshine today", f"{sun_uv.sunshine_hours(sun_today):.1f} h"),
        _tile("Sunshine, last 7 days", f"{sun_uv.sunshine_hours(sun_week):.1f} h"),
    ]), unsafe_allow_html=True)
    st.subheader("Sunburn time at this UV index")
    theme.table([{"Skin type": k, "Minutes until sunburn": "--" if m is None else f"{m:.0f}"}
              for k in sun_uv.MED_J_M2 for m in [sun_uv.burn_minutes(uv_now, k)]])
    fig = charts.figure(dark)
    fig.add_scatter(x=[datetime.fromtimestamp(ts, _tz(s)) for ts, _ in uv_today], y=[u for _, u in uv_today],
                    mode="lines", name="UV index", line=dict(color=charts.CHART_COLORS[2]))
    charts.show(fig)
    st.caption("Estimates from the station's UV reading. They assume full sun with no shade and no sunscreen.")


# ---------------------------------------------------------------- Astronomy
def _local_time(dt, tz) -> str:
    return "--" if dt is None else dt.astimezone(tz).strftime("%I:%M %p").lstrip("0")


def astronomy_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html("Astronomy"), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        st.info("Set your location on the Setup page to see sunrise, sunset and the moon.")
        return

    now = datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    rise, set_ = astro.sun_times(s.latitude, s.longitude, today)
    if rise is None or set_ is None:
        length = "--"
    else:
        minutes = round((set_ - rise).total_seconds() / 60)
        length = f"{minutes // 60} h {minutes % 60} min"
    moon = astro.moon_phase(now)
    full = astro.next_phase(now, astro.FULL_AGE).astimezone(tz)
    new = astro.next_phase(now, 0).astimezone(tz)
    st.markdown(theme.grid_html([
        _tile("Sunrise", _local_time(rise, tz)),
        _tile("Sunset", _local_time(set_, tz)),
        _tile("Day length", length),
        _tile("Moon", moon["name"], f"{moon['illumination']:.0f}% lit"),
        _tile("Next full moon", f"{full:%b %d}"),
        _tile("Next new moon", f"{new:%b %d}"),
    ]), unsafe_allow_html=True)

    st.subheader("Next 7 days")
    rows = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        day_rise, day_set = astro.sun_times(s.latitude, s.longitude, day)
        rows.append({"Date": f"{day:%a %b %d}", "Sunrise": _local_time(day_rise, tz),
                     "Sunset": _local_time(day_set, tz)})
    theme.table(rows)
    st.caption(f"Times are in {s.timezone}. Sun times use the standard NOAA method, accurate to about a minute. "
               "Moon dates can be off by about a day.")
