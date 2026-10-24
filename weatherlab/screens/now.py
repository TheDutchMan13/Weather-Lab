"""Pages under Now: live readings, sensors and the alert history."""

import html
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime, timedelta
from weatherlab import alert_map, astro, charts, comfort, dew, dials, gauges, gateway_sensors, health, health_check, hero, history_compare, motion, nws, sparks, stations, storage, sun_uv, theme, units, wind_rose, wx_icons
from weatherlab.config import CARD_LABELS
from weatherlab.screens import live_history
from weatherlab.settings import Settings, load_settings
from weatherlab.screens.common import _alert_box, _clock, _hourly, _points, _start_of_today, _tile, _tz, empty_card, freshness_line, start_poller, term_help


REFRESH_SECONDS = 30


def _comfort_tiles(data: dict) -> list[str]:
    """Heat index, wind chill and humidex, shown only when they apply."""
    metric = units.is_metric(load_settings().units)
    t, rh, wind, dew = data.get("tempf"), data.get("humidity"), data.get("windspeedmph"), data.get("dewpointf")
    tiles = []
    if t is not None and rh is not None and t >= 80:
        tiles.append(_tile("Heat index", units.format_value("heat_index", comfort.heat_index_f(t, rh), metric, 0), "feels hotter than air"))
    if t is not None and wind is not None and t <= 50 and wind > 3:
        tiles.append(_tile("Wind chill", units.format_value("tempf", comfort.wind_chill_f(t, wind), metric, 0), "feels colder than air"))
    if t is not None and dew is not None:
        tiles.append(_tile("Humidex", f"{comfort.humidex_c(t, dew):.0f}°C", "humid-heat index"))
    return tiles


def _now_sky(s: Settings, data: dict) -> tuple[str, bool]:
    """The NWS wording for the current hour (empty if unavailable) and whether it is night."""
    short = ""
    if s.latitude is not None and s.longitude is not None:
        try:
            pts = _points(s.latitude, s.longitude, s.nws_contact)
            if pts.get("forecastHourly"):
                hours = _hourly(pts["forecastHourly"], s.nws_contact)
                if hours:
                    short = hours[0]["short"]
        except nws.NwsError:
            short = ""
    solar = data.get("solarradiation")
    hour = datetime.now(_tz(s)).hour
    night = solar < 5 if solar is not None else (hour < 6 or hour >= 19)
    return short, night


@st.cache_data(ttl=600, show_spinner=False)
def _live_alerts(lat: float, lon: float, contact: str) -> list[dict]:
    """Active NWS warnings. A failure is remembered for 10 minutes, so an offline network can't slow Live down."""
    try:
        return nws.alerts(lat, lon, contact)
    except nws.NwsError:
        return []


def _warnings(s: Settings) -> None:
    """Recent rule alerts and active NWS warnings, shown at the top of Live."""
    now = time.time()
    for ts, text in [(t, m) for t, m in start_poller().status.recent_alerts if now - t < 6 * 3600][:3]:
        st.warning(f"{_clock(ts)}  {text}")
    if s.latitude is None or s.longitude is None:
        return
    active = _live_alerts(s.latitude, s.longitude, s.nws_contact)
    if active:
        st.markdown('<div class="wl-status">Active warnings</div>', unsafe_allow_html=True)
        st.markdown("".join(_alert_box(a) for a in active[:3]), unsafe_allow_html=True)
        if len(active) > 3:
            st.caption(f"{len(active) - 3} more on the Forecast page.")


def _naive(dt, tz):
    """A timezone-aware time as a naive local time (None stays None)."""
    return dt.astimezone(tz).replace(tzinfo=None) if dt is not None else None


def _span(delta) -> str:
    minutes = max(0, int(delta.total_seconds() // 60))
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if h else f"{m} min"


def _uv_word(uv: float) -> str:
    return sun_uv.uv_word(uv)


def _press_word(now_value, old_value) -> str:
    if now_value is None or old_value is None:
        return ""
    ch = now_value - old_value
    return ("rising fast" if ch > 0.06 else "rising" if ch > 0.02 else
            "falling fast" if ch < -0.06 else "falling" if ch < -0.02 else "steady")


def _hero(s: Settings, row: tuple, short: str, night: bool, alerts: list[dict]) -> None:
    """The 'right now' panel: sky, temperature, alert, today's range, the last-hour trend and the main readings."""
    ts, data = row
    temp = data.get("tempf")
    if temp is None:
        return
    db = storage.connect()
    tz = _tz(s)
    metric = units.is_metric(s.units)
    wall = time.time()
    now_dt = datetime.now(tz)
    rise, sset = (None, None)
    if s.latitude is not None and s.longitude is not None:
        rise, sset = astro.sun_times(s.latitude, s.longitude, now_dt.date())
    now_n, rise_n, set_n = now_dt.replace(tzinfo=None), _naive(rise, tz), _naive(sset, tz)
    strike = storage.latest_strike(db)
    storm = strike is not None and wall - strike[0] < 1800
    raining = (data.get("rainratein") or 0) > 0
    cloudy = "cloud" in short.lower() or "overcast" in short.lower()
    kind = hero.sky_phase(hero.pick_kind(night, storm, raining, cloudy), now_n, rise_n, set_n)

    alert, tone = "", "warn"
    if alerts:
        top = alerts[0]  # nws.alerts puts the most severe first
        until = top["expires"][:16].replace("T", " ") if top["expires"] else ""
        alert = f"{top['event']} until {until}" if until else top["event"]
        if len(alerts) > 1:
            alert = f"{len(alerts)} alerts · {top['severity']} · {alert}"
        tone = "bad" if top["severity"] in ("Extreme", "Severe") else "warn"

    state, age_text = health.age_status(ts, wall)
    live_text = {"ok": f"Live · updated {age_text}", "slow": f"Late · last reading {age_text}",
                 "silent": f"No data for {age_text} · check the station",
                 "none": "Waiting for first reading"}[state]

    today = storage.readings_between(db, _start_of_today(s), wall + 1)
    today_temps = [r["tempf"] for _, r in today if r.get("tempf") is not None]
    gusts = [r["windgustmph"] for _, r in today if r.get("windgustmph") is not None]
    lo, hi = (min(today_temps), max(today_temps)) if today_temps else (None, None)

    prior = [r["tempf"] for _, r in storage.readings_between(db, wall - 3900, wall - 3300)
             if r.get("tempf") is not None]
    trend, trend_col = "", "#c3cbd8"
    if prior:
        delta = units.convert("tempf", temp, metric) - units.convert("tempf", prior[-1], metric)
        if abs(delta) >= 0.5:
            trend = f"{'▲' if delta > 0 else '▼'} {abs(delta):.0f}° in the last hour"
            trend_col = "#fdba74" if delta > 0 else "#93c5fd"
        else:
            trend = "– steady over the last hour"

    press = data.get("baromrelin")
    old_press = [r["baromrelin"] for _, r in storage.readings_between(db, wall - 3 * 3600 - 300, wall - 3 * 3600 + 300)
                 if r.get("baromrelin") is not None]
    press_word = _press_word(press, old_press[-1] if old_press else None)

    sun = ""
    if rise_n and now_n < rise_n:
        sun = f"Sunrise in {_span(rise_n - now_n)}"
    elif set_n and now_n < set_n:
        sun = f"Sunset in {_span(set_n - now_n)}"

    tiles = []
    ws, wd = data.get("windspeedmph"), data.get("winddir")
    if ws is not None:
        prefix = wind_rose.NAMES[round(wd / 22.5) % 16] + " " if wd is not None and ws >= 1 else ""
        gust_note = f"gusts {units.format_value('windgustmph', max(gusts), metric, 0)} today" if gusts else ""
        tiles.append(("Wind", prefix + units.format_value("windspeedmph", ws, metric, 0), gust_note))
    hum, dew = data.get("humidity"), data.get("dewpointf")
    if hum is not None:
        dew_note = f"dew point {units.format_value('dewpointf', dew, metric, 0)}" if dew is not None else ""
        tiles.append(("Humidity", f"{hum:.0f}%", dew_note))
    if press is not None:
        tiles.append(("Pressure", units.format_value("baromrelin", press, metric, 2), press_word))
    uv = data.get("uv")
    if uv is not None:
        tiles.append(("UV index", f"{uv:.0f}", _uv_word(uv)))
    rain = data.get("dailyrainin")
    if rain is not None:
        tiles.append(("Rain today", units.format_value("dailyrainin", rain, metric, 2), ""))

    parts = []
    if hi is not None:
        parts.append(f"high {units.convert('tempf', hi, metric):.0f}° · low {units.convert('tempf', lo, metric):.0f}°")
    if rain is not None:
        parts.append(f"rain {units.format_value('dailyrainin', rain, metric, 2)}")
    if gusts:
        parts.append(f"peak gust {units.format_value('windgustmph', max(gusts), metric, 0)}")

    feels = data.get("feelslikef")
    html_out, height = hero.hero_html({
        "temp_text": f"{units.convert('tempf', temp, metric):.0f}°",
        "kind": kind, "icon": wx_icons.now_icon(kind, 84),
        "feels": units.format_value("feelslikef", feels, metric, 0) if feels is not None else "",
        "label": short, "place": "",
        "live_state": state, "live_text": live_text,
        "alert": alert, "alert_tone": tone,
        "lo": units.convert("tempf", lo, metric) if lo is not None else None,
        "hi": units.convert("tempf", hi, metric) if hi is not None else None,
        "now": units.convert("tempf", temp, metric),
        "lo_text": units.format_value("tempf", lo, metric, 0) if lo is not None else "",
        "hi_text": units.format_value("tempf", hi, metric, 0) if hi is not None else "",
        "tiles": tiles, "trend": trend, "trend_col": trend_col, "sun_note": sun,
        "today_line": " · ".join(parts),
    })
    components.html(motion.add(html_out, s.animate), height=height)


def _temp_ring(s: Settings, data: dict) -> None:
    """The temperature ring with today's high and low, feels like, dew point and humidity."""
    temp = data.get("tempf")
    if temp is None:
        return
    today = storage.readings_between(storage.connect(), _start_of_today(s), time.time() + 1)
    temps = [r["tempf"] for _, r in today if r.get("tempf") is not None]
    html_out, height = gauges.temp_ring_html(
        temp, high=max(temps) if temps else None, low=min(temps) if temps else None,
        feels=data.get("feelslikef"), dew=data.get("dewpointf"), hum=data.get("humidity"),
        dark=theme.is_dark(), metric=units.is_metric(s.units))
    components.html(motion.add(html_out, s.animate), height=height)


SPARK_KEYS = ("tempf", "humidity", "windspeedmph", "baromrelin")


ALERT_ZONE_LIMIT = 25  # zones outlined at most, so a statewide warning can't stall the page


@st.cache_data(ttl=3600, show_spinner=False)
def _zone_rings(zone: str, contact: str) -> list:
    """Outline of one NWS warning zone, remembered for an hour. Failures are not remembered."""
    return nws.zone_rings(zone, contact)


def _alert_map(s: Settings, alerts: list[dict]) -> None:
    """Warnings drawn on their zones around the station, using NWS zone outlines fetched at run time."""
    zoned, budget = [], ALERT_ZONE_LIMIT
    for a in alerts:
        zones = []
        for zone in a.get("ugc", []):
            if budget <= 0:
                break
            budget -= 1
            try:
                zones.append((zone, _zone_rings(zone, s.nws_contact)))
            except nws.NwsError:
                continue
        zoned.append(dict(a, zones=zones))
    names = [f"{a['event']} ({a['severity']})" for a in zoned]
    choice = st.selectbox("Highlight an alert", names, index=None, placeholder="All alerts", key="alert_highlight")
    highlight = names.index(choice) if choice in names else None
    dark = theme.is_dark()
    fig = charts.figure(dark, height=360)
    for t in alert_map.traces(zoned, highlight):
        fig.add_trace(go.Scatter(x=t["xs"], y=t["ys"], mode="lines", fill="toself", fillcolor=t["color"],
                                 line=dict(color=t["color"], width=1.5), opacity=t["opacity"],
                                 name=t["name"], hoverinfo="name", showlegend=False))
    fig.add_trace(go.Scatter(x=[s.longitude], y=[s.latitude], mode="markers", name="Your location",
                             marker=dict(size=12, symbol="star", color=theme.palette(dark)["text"]),
                             hoverinfo="name", showlegend=False))
    x0, x1, y0, y1 = alert_map.view_box(s.latitude, s.longitude, span=1.0)
    fig.update_xaxes(range=[x0, x1], visible=False)
    fig.update_yaxes(range=[y0, y1], visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=8, b=0), hovermode="closest")
    charts.show(fig)
    if sum(len(a.get("ugc", [])) for a in alerts) > ALERT_ZONE_LIMIT:
        st.caption(f"Only the first {ALERT_ZONE_LIMIT} zones are outlined.")


def _pressure_change(now_inhg: float) -> float | None:
    """Pressure change over the last three hours, in inHg. None until there is a reading from about then."""
    now = time.time()
    old = [r["baromrelin"] for _, r in storage.readings_between(storage.connect(), now - 3 * 3600 - 300,
                                                               now - 3 * 3600 + 300)
           if r.get("baromrelin") is not None]
    return now_inhg - sum(old) / len(old) if old else None


def _clickable_dial(key: str, help_key: str | None, draw, where: str = "") -> None:
    """A dial or tile that opens that reading's history when clicked. The ? help, when there is one, stays in the corner."""
    with st.container(key=f"wcard-{where}{key}"):
        draw()
        if st.button("History", key=f"hist-{where}{key}"):
            live_history.request(key)
        if help_key:
            term_help(help_key)


def _feels_dial(s: Settings, data: dict) -> None:
    feels = data.get("feelslikef")
    if feels is None:
        return
    html_out, height = dials.feels_dial_html(feels, actual_f=data.get("tempf"), humidity=data.get("humidity"),
                                             dark=theme.is_dark(), metric=units.is_metric(s.units))
    components.html(motion.add(html_out, s.animate), height=height)


def _pressure_dial(s: Settings, data: dict) -> None:
    now_inhg = data.get("baromrelin")
    if now_inhg is None:
        return
    change = _pressure_change(now_inhg)
    if change is None:
        st.caption("The pressure trend appears after three hours of readings.")
        return
    html_out, height = dials.pressure_dial_html(now_inhg, change, dark=theme.is_dark(),
                                                metric=units.is_metric(s.units))
    components.html(motion.add(html_out, s.animate), height=height)


@st.cache_data(ttl=600, show_spinner=False)
def _recent_thinned(stamp: int, station: str) -> list:
    """One reading per ten minutes for the last 31 days, with only the measures the Live cards use. The stamp
    changes every ten minutes, which is what refreshes this cache."""
    now = time.time()
    out, last = [], None
    for ts, r in storage.readings_between(storage.connect(), now - 31 * 86400, now + 1):
        bucket = int(ts // 600)
        kept = (ts, {k: r.get(k) for k in SPARK_KEYS})
        if bucket == last:
            out[-1] = kept  # the latest reading in each ten-minute slot wins
        else:
            out.append(kept)
            last = bucket
    return out


# Above usual: amber for heat and wind, neutral grey for humidity (more muggy, not a warning). Below usual is blue.
ABOVE_USUAL = {"tempf": theme.HEALTH_DOT["warn"], "humidity": theme.STRIP_NEUTRAL, "windspeedmph": theme.HEALTH_DOT["warn"]}
BELOW_USUAL = theme.HEALTH_DOT["info"]


def _glance(s: Settings, data: dict, updated: float) -> None:
    """Temperature, humidity and wind over the last 24 hours, each compared with usual for this hour."""
    metric = units.is_metric(s.units)
    now = time.time()
    rows = _recent_thinned(int(now // 600), stations.current())
    day = [(ts, r) for ts, r in rows if ts >= now - 86400]
    specs = [("tempf", "Temperature", units.unit("tempf", metric), 1.5 if metric else 3.0, charts.MEASURE["temp"]),
             ("humidity", "Humidity", "%", 5.0, charts.MEASURE["humidity"]),
             ("windspeedmph", "Wind", units.speed_unit(metric), 5.0 if metric else 3.0, charts.MEASURE["wind"])]
    keys, tile_html = [], []
    for key, label, unit_text, neutral, color in specs:
        if data.get(key) is None:
            continue
        keys.append(key)
        cur = units.convert(key, data[key], metric)
        series = [units.convert(key, r[key], metric) for _, r in day if r.get(key) is not None]
        found = sparks.hourly_usual(rows + [(now, data)], key, _tz(s), now)
        if found:
            note, direction = sparks.compare_text(cur, units.convert(key, found[1], metric), unit_text, neutral)
        else:
            so_far = min(sparks.usual_days(rows + [(now, data)], key, _tz(s), now), sparks.USUAL_DAYS)
            dots = "●" * so_far + "○" * (sparks.USUAL_DAYS - so_far)
            note, direction = f"Usual for this hour: {so_far} of {sparks.USUAL_DAYS} days {dots}", None
        # Colour says what the number means. Near usual stays grey, and red is kept for real problems.
        above = ABOVE_USUAL[key]
        edge = {"up": above, "down": BELOW_USUAL}.get(direction, theme.STRIP_NEUTRAL)
        tile_html.append(sparks.tile_html({"label": label, "value": f"{cur:.0f}", "unit": unit_text, "series": series,
                                       "color": color, "compare": note, "direction": direction, "edge": edge,
                                       "up_color": above, "down_color": BELOW_USUAL}))
    if tile_html:
        st.markdown(theme.section_html("Last 24 hours", updated=updated), unsafe_allow_html=True)
        for col, key, html_out in zip(st.columns(len(keys)), keys, tile_html):
            with col:
                _clickable_dial(key, None, lambda h=html_out: st.markdown(h, unsafe_allow_html=True), "tile-")


def _trend_card(s: Settings, key: str, label: str, unit: str, data: dict, day: list,
                color: str) -> tuple[str, str] | None:
    """Option B: a reading with its last 24 hours as a trend line and its low and high. Clicking opens its history."""
    if data.get(key) is None:
        return None
    metric = units.is_metric(s.units)
    series = [units.convert(key, r[key], metric) for _, r in day if r.get(key) is not None]
    cur = units.convert(key, data[key], metric)
    sub = f"low {min(series):.0f} · high {max(series):.0f}" if len(series) >= 2 else ""
    if key == "uv":
        sub = "scale 0 to 11"
    return key, ('<div class="wl-tile" style="text-align:left">'
                 f'<div class="wl-label">{html.escape(label)}</div>'
                 f'<div class="wl-value">{cur:.0f}<span style="font-size:13px;font-weight:400;opacity:.7"> {html.escape(unit)}</span></div>'
                 f'{sparks.spark_svg(series, color, h=56)}'
                 f'<div class="wl-label" style="margin-top:4px">{html.escape(sub)}</div></div>')


def _tile_rows(items: list) -> None:
    """Readings in rows of up to three. A reading with a history opens it when clicked; others stay still."""
    for start in range(0, len(items), 3):
        row = items[start:start + 3]
        for col, (key, html_out) in zip(st.columns(len(row)), row):
            with col:
                if key in live_history.MEASURES:
                    _clickable_dial(key, None, lambda h=html_out: st.markdown(h, unsafe_allow_html=True), "card-")
                else:
                    st.markdown(html_out, unsafe_allow_html=True)


def _pill(text: str) -> str:
    return (f'<span style="display:inline-block;padding:4px 11px;margin:0 6px 6px 0;border-radius:999px;'
            f'background:rgba(127,127,127,.14)">{text}</span>')


@st.fragment(run_every=REFRESH_SECONDS)
def live_readings() -> None:
    """Cards and status line. Streamlit re-runs just this part every REFRESH_SECONDS."""
    s = load_settings()
    poller = start_poller()
    status = poller.status

    if not poller.is_alive():
        st.error("The background reader has stopped. Restart the app.")
    elif status.last_error:
        st.warning(status.last_error)
    _warnings(s)

    row = storage.latest(storage.connect())
    if row is None:
        empty_card("Waiting for the first reading from the station.", "If this doesn't change within a minute, check the station IP on Setup and that the station is on the same network.")
    else:
        _, data = row
        dark = theme.is_dark()
        short, night = _now_sky(s, data)
        alerts = _live_alerts(s.latitude, s.longitude, s.nws_contact) if s.latitude is not None and s.longitude is not None else []
        _hero(s, row, short, night, alerts)
        if alerts and s.latitude is not None and s.longitude is not None:
            with st.expander("Alert map", expanded=True):
                _alert_map(s, alerts)
        _glance(s, data, row[0])
        metric = units.is_metric(s.units)
        p = theme.DARK if dark else theme.LIGHT
        now = time.time()
        day = [(ts, r) for ts, r in _recent_thinned(int(now // 600), stations.current()) if ts >= now - 86400]
        trends = [_trend_card(s, key, label, unit, data, day, color) for key, label, unit, color in [
            ("humidity", "Humidity", "%", charts.MEASURE["humidity"]),
            ("windspeedmph", f"Wind {units.speed_unit(metric)}", "", charts.MEASURE["wind"]),
            ("uv", "UV index", "", p["accent"])]]
        trends = [c for c in trends if c]  # (key, html) pairs for the readings that exist
        air, wind = [], []
        for key in s.live_cards:
            if key in data:
                label, unit = CARD_LABELS[key]
                text = units.format_value(key, data[key], metric) if units.converts(key) else f"{data[key]:g} {unit}".strip()
                (wind if any(w in label.lower() for w in ("wind", "gust", "rain")) else air).append((key, _tile(label, text)))
        for comfort_tile in _comfort_tiles(data):
            (wind if "Wind" in comfort_tile or "Rain" in comfort_tile else air).append((None, comfort_tile))
        compact = st.toggle("Compact sections", key="live_compact", value=False)
        with st.expander("Details", expanded=not compact):
            _clickable_dial("tempf", None, lambda: _temp_ring(s, data))
            left, right = st.columns(2)
            with left:
                _clickable_dial("feelslikef", "feels_like", lambda: _feels_dial(s, data))
            with right:
                _clickable_dial("baromrelin", "pressure", lambda: _pressure_dial(s, data))
            if trends:
                for col, (key, html_out) in zip(st.columns(len(trends)), trends):
                    with col:
                        _clickable_dial(key, None, lambda h=html_out: st.markdown(h, unsafe_allow_html=True), "gauge-")
            if air:
                st.markdown(theme.section_html("Air"), unsafe_allow_html=True)
                _tile_rows(air)
            if wind:
                st.markdown(theme.section_html("Wind and rain"), unsafe_allow_html=True)
                _tile_rows(wind)

    live_history.show_pending()
    dot = _status_dot(row[0]) if row else ""
    pills = []
    if status.last_ok:
        pills.append(_pill(f"{dot}Last reading {_clock(status.last_ok)}"))
    if status.last_attempt:
        pills.append(_pill(f"Last attempt {_clock(status.last_attempt)}"))
    if status.started:
        pills.append(_pill(f"Reader started {_clock(status.started)}"))
    if pills:
        st.markdown(f'<div class="wl-status">{"".join(pills)}</div>', unsafe_allow_html=True)


def _status_dot(ts: float) -> str:
    state, _ = health.age_status(ts, time.time())
    return theme.status_dot(state)


def _today_vs_yesterday(s: Settings) -> None:
    """Today so far against yesterday over the same hours."""
    tz, metric = _tz(s), units.is_metric(s.units)
    db = storage.connect()
    now = datetime.now(tz)
    start = datetime.combine(now.date(), datetime.min.time(), tzinfo=tz)
    today = storage.readings_between(db, start.timestamp(), now.timestamp() + 1)
    earlier = storage.readings_between(db, (start - timedelta(days=1)).timestamp(),
                                       (now - timedelta(days=1)).timestamp() + 1)
    if not today or not earlier:
        return
    compared = history_compare.by_this_time([r for _, r in today], [r for _, r in earlier])

    def pair(key: str, label: str, decimals: int):
        t, y = compared[key]
        if t is None:
            return None
        text = f"{label} {units.format_value(key, t, metric, decimals)}"
        if y is not None:
            text += f" (yesterday by this time: {units.format_value(key, y, metric, decimals)})"
        return text

    parts = [p for p in (pair("tempf", "High so far", 0), pair("dailyrainin", "Rain today", 2),
                         pair("windgustmph", "Gust so far", 0)) if p]
    if parts:
        st.caption(" · ".join(parts))


def _dew_line(s: Settings) -> None:
    """Dew point in plain words: how muggy it feels right now."""
    latest = storage.latest(storage.connect())
    if not latest or latest[1].get("dewpointf") is None:
        return
    dew_point = latest[1]["dewpointf"]
    shown = units.format_value("dewpointf", dew_point, units.is_metric(s.units), 0)
    st.caption(f"Dew point {shown}: {dew.text(dew_point)}.")
    left, right = st.columns([0.85, 0.15], vertical_alignment="center")
    with left:
        if st.button("Dew point history", key="hist-dewpointf"):
            live_history.request("dewpointf")
    with right:
        term_help("dew_point")


@st.cache_data(ttl=86400, show_spinner=False)
def _nearby_station(lat: float, lon: float, contact: str) -> dict:
    """The station to read for this point, looked up once a day. Errors are kept so they aren't retried on every load."""
    try:
        url = nws.points(lat, lon, contact).get("stations", "")
        found = nws.nearest_airport_station(url, lat, lon, contact) if url else None
        return found or {"error": "No weather station was found near this location."}
    except nws.NwsError as exc:
        return {"error": str(exc)}


@st.cache_data(ttl=900, show_spinner=False)
def _station_reading(station_id: str, contact: str) -> dict:
    try:
        return nws.latest_observation(station_id, contact)
    except nws.NwsError as exc:
        return {"error": str(exc)}


def airport_card(s: Settings) -> None:
    """The latest reading from the nearest airport (or weather station), from the National Weather Service. US only."""
    if s.latitude is None or s.longitude is None:
        return
    station = _nearby_station(s.latitude, s.longitude, s.nws_contact)
    if "error" in station:
        st.caption(f"Nearby airport weather: {station['error']}")
        return
    reading = _station_reading(station["id"], s.nws_contact)
    if "error" in reading:
        st.caption(f"Nearby airport weather: {reading['error']}")
        return
    metric = units.is_metric(s.units)
    label = "Airport" if station["airport"] else "Nearest weather station"
    tiles = []
    if reading["temp_f"] is not None:
        tiles.append(theme.tile_html("Temperature", f"{units.convert('tempf', reading['temp_f'], metric):.0f}{units.suffix('tempf', metric)}"))
    if reading["wind_mph"] is not None:
        direction = nws.compass(reading["direction"])
        speed = f"{units.convert('windspeedmph', reading['wind_mph'], metric):.0f}{units.suffix('windspeedmph', metric)}"
        tiles.append(theme.tile_html("Wind", speed + (f" {direction}" if direction else "")))
    if reading["gust_mph"] is not None:
        tiles.append(theme.tile_html("Gusts", f"{units.convert('windgustmph', reading['gust_mph'], metric):.0f}{units.suffix('windgustmph', metric)}"))
    if reading["humidity"] is not None:
        tiles.append(theme.tile_html("Humidity", f"{reading['humidity']:.0f}%"))
    try:
        age = health_check.age_text(time.time() - datetime.fromisoformat(reading["time"]).timestamp())
    except (TypeError, ValueError):
        age = ""
    st.markdown(theme.section_html(f"{label} nearby", f"{station['name']}, {station['km']:.0f} km away"),
                unsafe_allow_html=True)
    if tiles:
        st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    else:
        st.caption("No readings from this station yet.")
    notes = [reading["text"]] if reading["text"] else []
    if age:
        notes.append(f"Read from the National Weather Service, {age}")
    if notes:
        st.caption(". ".join(notes) + ".")


def _welcome(s: Settings) -> None:
    """First run: the three steps to a working app, with a tick for each one already done."""
    has_readings = bool(storage.connect().execute("SELECT 1 FROM readings LIMIT 1").fetchone())
    steps = [
        (bool(s.station_ip), "Point Weather Lab at your station", "Setup, Station tab: enter the station's IP address."),
        (has_readings, "Wait for the first reading", "It arrives within a minute of the address being saved."),
        (False, "Choose your phone alerts (optional)",
         "Settings: rain, lightning, stuck sensors and app problems."),
    ]
    with st.container(border=True):
        st.markdown("**Welcome. Three steps and Live fills in.**")
        for done, title, detail in steps:
            mark = "✓" if done else "○"
            st.markdown(f"{mark} **{title}**  \n<span style='opacity:.7'>{detail}</span>", unsafe_allow_html=True)


def live_page() -> None:
    s = load_settings()
    st.markdown(theme.page_head("Live", "Right now at your station, with the last 24 hours and any active alerts."), unsafe_allow_html=True)
    if not s.station_ip:
        _welcome(s)
        return
    freshness_line()
    _today_vs_yesterday(s)
    _dew_line(s)
    airport_card(s)
    live_readings()


def alerts_log_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.page_head("Alert history", "Every alert Weather Lab has sent, newest first. Search to filter them."), unsafe_allow_html=True)
    rows = storage.recent_alerts(storage.connect(), limit=300)
    if not rows:
        empty_card("Alerts appear here once Weather Lab sends its first notification.")
        return
    query = st.text_input("Search alerts", key="alert_search").strip().lower()
    body = [{"When": datetime.fromtimestamp(ts, tz).strftime("%a %b %d, %I:%M %p"), "Alert": text}
            for ts, text in rows if not query or query in text.lower()]
    if not body:
        empty_card("No alerts match that search")
        return
    theme.table(body)


# ---------------------------------------------------------------- Sensors
SENSOR_KEY_BY_LABEL = {label: key for label, key in health.SENSORS}
BATT_WORD = {"good": "Good", "ok": "OK", "watch": "Getting low", "low": "Low", "dc": "Mains", "unknown": "Unknown"}
BATT_TONE = {"good": "ok", "ok": "ok", "watch": "warn", "low": "bad", "dc": "ok", "unknown": "info"}
SIG_WORD = {"good": "Strong", "fair": "Fair", "weak": "Weak", "none": "None", "unknown": "Unknown"}
SIG_TONE = {"good": "ok", "fair": "ok", "weak": "warn", "none": "bad", "unknown": "info"}
def _strip_tile(label: str, value: str, note: str, tone: str, word: str | None = None) -> str:
    return theme.strip_tile_html(label, value, note, tone, word)


@st.cache_data(ttl=300, show_spinner=False)
def _sensor_batteries(ip: str) -> list[dict] | None:
    """Battery and signal for each paired sensor, or None when the station can't be read."""
    try:
        return gateway_sensors.read(ip)
    except (OSError, ValueError):
        return None


def _pick_sensor() -> None:
    """A sensor chip was tapped: ask live_history for its window, which sensors_page then draws."""
    choice = st.session_state.get("sensor_pick")
    st.session_state["sensor_pick"] = None
    if choice in SENSOR_KEY_BY_LABEL:
        live_history.request(SENSOR_KEY_BY_LABEL[choice])


def sensors_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    st.markdown(theme.page_head("Sensors", "How fresh and complete the station's data is, sensor by sensor."), unsafe_allow_html=True)
    now = time.time()
    rows = health.window(db, now - 24 * 3600, now)
    if not rows:
        empty_card("No readings in the last 24 hours yet", "Check the station's connection on the Live page.")
        return

    last_ts, latest = rows[-1][0], rows[-1][1]
    status, age_text = health.age_status(last_ts, now)
    age_min = max(0.0, (now - last_ts) / 60)
    fresh, ftone = (("Fresh", "ok") if age_min < 1 else ("Recent", "ok") if age_min < 5
                    else ("Stale", "warn") if age_min < 10 else ("Old", "bad"))
    completeness = health.completeness(rows, 24)
    sensors = health.sensors(rows)
    seen_now = [latest.get(x["key"]) is not None for x in sensors]
    online, offline = sum(seen_now), len(sensors) - sum(seen_now)
    gap_list = health.gaps(rows)

    st.markdown(theme.grid_html([
        _strip_tile("Data freshness", fresh, f"{age_min:.1f} min old", ftone, word=""),
        _strip_tile("Completeness", f"{completeness:.1f}%", "last 24 hours",
                    "ok" if completeness >= 95 else "warn" if completeness >= 80 else "bad"),
        _strip_tile("Sensors online", f"{online}/{len(sensors)}",
                    f"{offline} offline" if offline else "all reporting", "warn" if offline else "ok"),
        _strip_tile("Readings", f"{len(rows):,} readings", "last 24 hours", "info"),
    ]), unsafe_allow_html=True)

    st.markdown(theme.section_html("Sensor status"), unsafe_allow_html=True)
    theme.table([{"Sensor": x["label"], "Status": "✓" if on else "✗",
                  "Completeness": f"{x['present_pct']:.1f}%" if x["last_seen"] is not None else "—",
                  "State": theme.state_html("ok", "Online") if on else theme.state_html("fail", "Offline")}
                 for x, on in zip(sensors, seen_now)], html_cols=("State",))

    st.pills("See a sensor's history", list(SENSOR_KEY_BY_LABEL), selection_mode="single",
             key="sensor_pick", on_change=_pick_sensor)
    live_history.show_pending()

    ip = s.station_ip.strip()
    batteries = _sensor_batteries(ip) if ip else []
    st.markdown(theme.section_html("Batteries and radio signal"), unsafe_allow_html=True)
    if not ip:
        empty_card("Set the station IP on the Setup page to see sensor battery and signal.")
    elif batteries is None:
        st.caption("Battery and signal aren't available right now. The station may be off or offline.")
    elif not batteries:
        st.caption("No paired sensors were found.")
    else:
        tiles = []
        for b in batteries:
            bs, bt = gateway_sensors.battery_state(b["batt"])
            ss, sg = gateway_sensors.signal_state(b["signal"], b["rssi"])
            tiles.append(_strip_tile(f"{b['name']}: battery", BATT_WORD.get(bs, "?"), bt, BATT_TONE.get(bs, "info"), word=""))
            tiles.append(_strip_tile(f"{b['name']}: radio signal", SIG_WORD.get(ss, "?"), sg, SIG_TONE.get(ss, "info"), word=""))
        st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    st.caption("Battery level runs 0 to 5 (5 full, 0 empty). Battery and signal refresh about every five minutes.")

    left, right = st.columns(2)
    with left:
        st.markdown(theme.section_html("Completeness by sensor"), unsafe_allow_html=True)
        theme.table([{"Sensor": x["label"], "Completeness": f"{x['present_pct']:.1f}%"}
                     for x in sorted(sensors, key=lambda x: x["present_pct"], reverse=True)])
    with right:
        st.markdown(theme.section_html("Gaps in the data"), unsafe_allow_html=True)
        if gap_list:
            theme.table([{"From": health.clock(a, tz), "To": health.clock(b, tz),
                          "Minutes": round((b - a) / 60)} for a, b in gap_list[-10:]])
        else:
            st.success("No data gaps detected!")

    st.markdown(theme.section_html("Data quality alerts"), unsafe_allow_html=True)
    issues = []
    if status in ("silent", "slow"):
        issues.append(("error" if status == "silent" else "warning", "Station not reporting" if status == "silent"
                       else "Readings are delayed", f"Last reading {age_text}."))
    if completeness < 95:
        issues.append(("warning", "Completeness is low", f"{completeness:.1f}% of expected readings over 24 hours."))
    for x in sensors:
        if x["last_seen"] is None or latest.get(x["key"]) is None:
            issues.append(("warning", f"{x['label']} is not reporting", "It was missing from the latest reading."))
    for text in gateway_sensors.warnings(batteries or []):
        issues.append(("warning", "Sensor warning", text))
    if issues:
        for kind, title, message in issues:
            (st.error if kind == "error" else st.warning)(f"**{title}** {message}")
    else:
        st.success("✅ All data quality checks passed!")

    st.markdown(theme.section_html("Sensor activity"), unsafe_allow_html=True)
    st.caption("When each sensor last reported, and how many readings in the last 24 hours included it.")
    theme.table([{"Sensor": x["label"],
                  "Readings": f"{sum(1 for _, r in rows if r.get(x['key']) is not None):,}",
                  "Last reading": health.clock(x["last_seen"], tz) if x["last_seen"] is not None else "never"}
                 for x in sensors])
