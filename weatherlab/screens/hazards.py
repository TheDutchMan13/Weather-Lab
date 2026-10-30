"""Pages under Hazards: air quality, fire weather, lightning, tropics and radar."""

import html
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from weatherlab import airquality, charts, lightning_history, nws, secrets, storage, theme, tropics, units, timefmt
from weatherlab.config import RISK_COLORS
from weatherlab.settings import load_settings
from weatherlab.screens.common import _clock, _tile, _tz, empty_card, start_poller


# ---------------------------------------------------------------- Air
def air_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.page_head("Air quality", "Air quality for your area from AirNow, with the pollutant levels."), unsafe_allow_html=True)
    if not secrets.get_key("airnow"):
        empty_card("Add a free AirNow API key in Settings, under Station to see air quality.")
        return
    if s.latitude is None or s.longitude is None:
        empty_card("Set your latitude and longitude in Settings, under Station.")
        return

    poller = start_poller()
    row = storage.latest_aqi(storage.connect())
    if row is None:
        empty_card("No air quality reading yet", "Weather Lab checks AirNow about every 30 minutes, and AirNow updates about once an hour.")
        if poller.status.aqi_error:
            st.warning(poller.status.aqi_error)
        return

    ts, data = row
    risk = data.get("risk", "")
    color = RISK_COLORS.get(risk, "#6b7280")
    aqi_tile = (f'<div class="wl-tile" style="border-left:4px solid {color};border-radius:8px">'
                f'<div class="wl-label">Air quality index</div>'
                f'<div class="wl-value">{html.escape(str(data.get("aqi", "--")))}</div>'
                f'<div class="wl-label" style="color:{color}">{html.escape(str(data.get("category", "")))}</div>'
                f'<div class="wl-label">{html.escape(str(data.get("station", "")))} · updated {_clock(ts)}</div></div>')
    tiles = [aqi_tile]
    for name, key in airquality.POLLUTANTS.items():
        if data.get(key) is not None:
            tiles.append(_tile(name, f"{data[key]:g}"))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    if poller.status.aqi_error:
        st.warning(poller.status.aqi_error)


# ---------------------------------------------------------------- Lightning
def lightning_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    now = datetime.now(tz)
    metric = units.is_metric(s.units)
    st.markdown(theme.page_head("Lightning", "Strikes the app saw while it was running, today and over time."), unsafe_allow_html=True)
    start_of_day = datetime.combine(now.date(), datetime.min.time(), tzinfo=tz).timestamp()
    today = storage.strikes_between(db, start_of_day, now.timestamp())
    last = storage.latest_strike(db)

    if last is None:
        empty_card("No lightning recorded yet", "Strikes appear here when the station reports them.")
    else:
        last_ts, last_mi = last
        when = timefmt.stamp(datetime.fromtimestamp(last_ts, tz))
        closest = min((d for _, d in today), default=None)
        st.markdown(theme.grid_html([
            _tile("Last strike", units.format_value("miles", last_mi, metric, 1), when),
            _tile("Strikes today", str(len(today)), "seen while the app runs"),
            _tile("Closest today", units.format_value("miles", closest, metric, 1)),
        ]), unsafe_allow_html=True)

    if today:
        st.markdown(theme.section_html("Today"), unsafe_allow_html=True)
        theme.table([{"time": timefmt.time_text(datetime.fromtimestamp(ts, tz)),
                   f"Distance ({units.unit('miles', metric)})": round(units.convert("miles", d, metric), 1)}
                  for ts, d in reversed(today[-20:])])
    st.caption("Counts only strikes the app saw while it was running. Distances follow the switch in Settings, under Station.")

    st.markdown(theme.section_html("History"), unsafe_allow_html=True)
    span_choice = st.radio("Range", ["30 days", "1 year"], index=0, horizontal=True, key="lightning_range")
    span = 30 if span_choice == "30 days" else 365
    since = datetime.combine(now.date() - timedelta(days=span - 1), datetime.min.time(), tzinfo=tz).timestamp()
    by_day = lightning_history.per_day(storage.strikes_between(db, since, now.timestamp()), tz)
    if not by_day:
        empty_card("No strikes in this range")
    else:
        dark = theme.is_dark()
        days = [d for d, _, _ in by_day]
        counts_fig = charts.figure(dark)
        counts_fig.add_trace(go.Bar(x=days, y=[c for _, c, _ in by_day], name="Strikes",
                                    marker_color=charts.MEASURE["lightning"]))
        charts.show(counts_fig)
        closest_fig = charts.figure(dark)
        closest_fig.add_trace(go.Scatter(x=days, y=[units.convert("miles", m, metric) for _, _, m in by_day],
                                         name=f"Closest strike ({units.unit('miles', metric)})",
                                         mode="markers+lines", line=dict(color=charts.CHART_COLORS[4])))
        charts.show(closest_fig)


# ---------------------------------------------------------------- Fire
def _fire_day_note(f: dict, metric: bool) -> str:
    """Temperature, humidity and wind for one forecast day, in the chosen units."""
    if not metric:
        return f"{f['temperature']}°F · {f['humidity']}% · {f['wind_speed']} mph"
    import re
    temp = f"{units.convert('tempf', f['temperature'], True):.0f} °C"
    wind = re.sub(r"\d+(?:\.\d+)?", lambda m: f"{float(m.group(0)) * units.speed_factor(True):.0f}",
                  str(f["wind_speed"]).replace(" mph", "").replace("mph", ""))
    return f"{temp} · {f['humidity']}% · {wind} km/h"


def fire_page() -> None:
    db = storage.connect()
    st.markdown(theme.page_head("Fire weather", "Fire danger from your station's readings and the National Weather Service forecast."), unsafe_allow_html=True)
    rec = storage.latest_fire(db)
    if rec is None:
        empty_card("Fire weather appears once the station has sent readings for an hour.", "It updates every hour.")
        return
    st.markdown(theme.grid_html([
        _tile("Fire Weather Index", f"{rec['fwi']:.1f}", f"as of {rec['timestamp'][11:16]}"),
        _tile("FFMC", f"{rec['ffmc']:.1f}", "fine fuels"),
        _tile("DMC", f"{rec['dmc']:.1f}", "duff layer"),
        _tile("DC", f"{rec['dc']:.1f}", "deep drought"),
        _tile("ISI", f"{rec['isi']:.1f}", "spread index"),
        _tile("BUI", f"{rec['bui']:.1f}", "build-up index"),
        _tile("Days since rain", str(rec["days_since_rain"])),
    ]), unsafe_allow_html=True)

    forecast = rec.get("forecast") or []
    if len(forecast) > 1:
        st.markdown(theme.section_html("Forecast"), unsafe_allow_html=True)
        st.markdown(theme.grid_html([
            _tile(f["day"], f"{f['fwi']:.1f}", _fire_day_note(f, units.is_metric(load_settings().units)))
            for f in forecast[1:]
        ]), unsafe_allow_html=True)
    else:
        st.caption("No forecast yet. It comes from the National Weather Service, so it covers the United States only.")
    st.caption("Approximate. It uses the latest reading instead of the usual 1 pm observation, assumes no rain in "
               "the forecast, and uses day-length values for about 30° north.")


# ---------------------------------------------------------------- main
# ---------------------------------------------------------------- Heat, wind, sun, tropics, radar
RADAR_RIDGE = "https://radar.weather.gov/ridge/standard/"


def _moving(x: dict, metric: bool) -> str:
    """Direction and speed a storm is moving, in the chosen units."""
    if x.get("move_mph") is None:
        return x["move"] or "--"
    speed = round(units.convert("windspeedmph", x["move_mph"], metric))
    return f"{x['move_dir']} at {speed} {units.speed_unit(metric)}"


def tropics_page() -> None:
    s = load_settings()
    metric = units.is_metric(s.units)
    st.markdown(theme.page_head("Tropics", "Tropical storms from the National Hurricane Center, and how far each is from you."), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        empty_card("Set your latitude and longitude in Settings, under Station to see how far each storm is from you.")
        return
    cache = tropics.refresh((s.latitude, s.longitude), storage.db_path().parent / "tropics.json")
    if not cache.get("checked"):
        st.warning(f"Couldn't reach the National Hurricane Center ({cache.get('error') or 'no answer'}). Try again later.")
        return
    if cache.get("ok"):
        st.caption(f"Checked the National Hurricane Center at {cache['checked']}.")
    else:
        st.caption(f"Couldn't reach the National Hurricane Center just now, so this is the list from {cache['checked']}.")
    storms = cache.get("storms", [])
    if not storms:
        st.success("The National Hurricane Center has no active tropical storms or hurricanes right now.")
        return
    st.dataframe([{"Storm": x["name"], "Type": x["class"], "Wind": units.format_value("windspeedmph", x["wind_mph"], metric, 0),
                   "Distance": units.format_value("miles", x["miles"], metric, 0), "From you": x["direction"], "Moving": _moving(x, metric),
                   "Updated": x["updated"]} for x in storms], hide_index=True)
    fig = go.Figure()
    fig.add_trace(go.Scattermap(lat=[s.latitude], lon=[s.longitude], mode="markers+text", marker=dict(size=14),
                                text=["You"], textposition="bottom center", name="You"))
    fig.add_trace(go.Scattermap(lat=[x["lat"] for x in storms], lon=[x["lon"] for x in storms],
                                mode="markers+text", marker=dict(size=16, color="#f59e0b"),
                                text=[x["name"] for x in storms], textposition="top center", name="Storms"))
    lats = [x["lat"] for x in storms] + [s.latitude]
    lons = [x["lon"] for x in storms] + [s.longitude]
    spread = max(max(lats) - min(lats), max(lons) - min(lons))
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=(max(lats) + min(lats)) / 2,
                                                                    lon=(max(lons) + min(lons)) / 2),
                               zoom=3 if spread > 20 else 4),
                      margin=dict(l=0, r=0, t=0, b=0), height=420, showlegend=False)
    charts.show(fig)


@st.cache_data(ttl=86400, show_spinner=False)
def _radar_station(lat: float, lon: float, contact: str) -> str:
    return nws.points(lat, lon, contact).get("radar", "")


def radar_page() -> None:
    s = load_settings()
    st.markdown(theme.page_head("Radar", "The radar and satellite picture around your station."), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        empty_card("Set your latitude and longitude in Settings, under Station to show the radar for your area.")
        return
    station = ""
    try:
        station = _radar_station(s.latitude, s.longitude, s.nws_contact)
    except nws.NwsError as exc:
        st.warning(str(exc))
    views = {"US radar": RADAR_RIDGE + "CONUS_loop.gif"}
    if station:
        views = {"Local radar": RADAR_RIDGE + f"{station}_loop.gif", **views}
    default = next(iter(views))
    choice = st.segmented_control("View", list(views), default=default, key="radar_view",
                                  label_visibility="collapsed") or default
    st.image(views[choice], caption="Green is light rain; yellow and red are heavy. Pictures come from the National Weather Service.")
    if station:
        st.link_button("Open the full local radar", f"https://radar.weather.gov/station/{station.lower()}/standard")
    else:
        st.link_button("Open the full radar", "https://radar.weather.gov/")
