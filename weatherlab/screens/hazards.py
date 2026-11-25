"""Pages under Hazards: air quality, fire weather, lightning, tropics and radar."""

import html
import time
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta
from weatherlab import airquality, charts, hero, stations, lightning_history, line_icons, nws, secrets, sparks, storage, theme, tropics, units, timefmt
from weatherlab.config import RISK_COLORS
from weatherlab.settings import load_settings
from weatherlab.screens.common import _clock, _tile, _tz, empty_card, start_poller


# ---------------------------------------------------------------- Air
# What each AirNow category means, in a sentence (the EPA's wording, shortened).
AQI_ADVICE = {
    "Good": "Air quality is good. Enjoy being outside.",
    "Moderate": "Air quality is acceptable. Unusually sensitive people may feel minor effects.",
    "Unhealthy for Sensitive Groups": "People with heart or lung conditions, older adults and children should take it easier outside.",
    "Unhealthy": "Everyone may begin to feel effects. Sensitive groups should limit time outside.",
    "Very Unhealthy": "Health alert: everyone may feel more serious effects. Keep outdoor effort short.",
    "Hazardous": "Emergency conditions. Everyone should stay indoors where possible.",
}
POLLUTANT_NOTES = {"PM2.5": "Fine particles", "PM10": "Coarse particles", "OZONE": "Ground-level ozone",
                   "NO2": "Nitrogen dioxide", "SO2": "Sulfur dioxide", "CO": "Carbon monoxide"}


def air_page() -> None:
    """Air quality (0.37.64, the redesign): the AQI in a coloured box with what it means, each pollutant, and the last
    24 hours as a line."""
    s = load_settings()
    st.markdown(theme.page_head("Air quality", "Air quality for your area from AirNow, with the pollutant levels."), unsafe_allow_html=True)
    if not secrets.get_key("airnow"):
        empty_card("Add a free AirNow API key in Settings, under Station to see air quality.")
        return
    if s.latitude is None or s.longitude is None:
        empty_card("Set your latitude and longitude in Settings, under Station.")
        return

    poller = start_poller()
    db = storage.connect()
    row = storage.latest_aqi(db)
    if row is None:
        empty_card("No air quality reading yet", "Weather Lab checks AirNow about every 30 minutes, and AirNow updates about once an hour.")
        if poller.status.aqi_error:
            st.warning(poller.status.aqi_error)
        return

    ts, data = row
    category = str(data.get("category", ""))
    color = RISK_COLORS.get(data.get("risk", ""), "#6b7280")
    where = f' · {html.escape(str(data["station"]))}' if data.get("station") else ""
    st.markdown(f'<div class="wl-panel wl-bignum"><div><div class="wl-note" style="margin-bottom:10px">'
                f'<b style="font-size:17px">Air Quality Index (AQI)</b> &nbsp;from AirNow{where}</div>'
                f'<div style="display:flex;align-items:center;gap:24px"><div class="wl-aqibox" style="background:{color}">'
                f'<span>AQI</span><b>{html.escape(str(data.get("aqi", "--")))}</b></div><i class="wl-div"></i>'
                f'<div><div class="wl-bw">{html.escape(category)}</div>'
                f'<div class="wl-bd">{html.escape(AQI_ADVICE.get(category, ""))}</div>'
                f'<div class="wl-note" style="margin-top:6px">Updated {_clock(ts)}</div></div></div></div></div>',
                unsafe_allow_html=True)
    cards = []
    for name, key in airquality.POLLUTANTS.items():
        if data.get(key) is not None:
            cards.append(hero.metric_html(line_icons.icon("drop" if name.startswith("PM") else "wind", 26, "#7cc4ff"),
                                          name, f"{data[key]:g}", "", f"{POLLUTANT_NOTES.get(name, '')} · AQI subindex", ""))
    if cards:
        st.markdown(f'<div class="wl-metrics">{"".join(cards)}</div>', unsafe_allow_html=True)

    now = time.time()
    trend = storage.aqi_between(db, now - 86400, now + 1)
    if len(trend) >= 2:
        tz = _tz(s)
        fig = charts.figure(theme.is_dark(), height=280)
        fig.add_trace(go.Scatter(x=[datetime.fromtimestamp(t, tz) for t, _ in trend], y=[d.get("aqi") for _, d in trend],
                                 mode="lines", line=dict(color="#f6c445", width=2.4), fill="tozeroy",
                                 fillcolor="rgba(246,196,69,.15)", name="AQI"))
        fig.update_layout(title=dict(text="24-hour AQI trend", x=0, xanchor="left", font=dict(size=16)), showlegend=False)
        fig.update_yaxes(rangemode="tozero")
        with st.container(border=True):
            charts.show(fig)
    st.caption("Pollutant numbers are AQI subindexes, the scale AirNow reports. The AQI is the highest of them.")
    if poller.status.aqi_error:
        st.warning(poller.status.aqi_error)


# ---------------------------------------------------------------- Lightning
def _storm_sky() -> str:
    """A dark stormy strip for the right of a big card: deep blue-purple with soft cloud."""
    return f"{hero._clouds_svg(True)} center/cover no-repeat, {hero.sky_bg('storm', hero.GRADS['storm'])}"


def _sky_strip(background: str, start: str = "50%") -> str:
    return (f'<div style="position:absolute;inset:0 0 0 {start};background:{background};'
            '-webkit-mask-image:linear-gradient(90deg,transparent,#000 55%);mask-image:linear-gradient(90deg,transparent,#000 55%);opacity:.85"></div>')


def lightning_page() -> None:
    """Lightning (0.37.64, the redesign): strikes today, the closest and the last in one card, then each day's count
    and closest strike for 30 days or a year."""
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    now = datetime.now(tz)
    metric = units.is_metric(s.units)
    st.markdown(theme.page_head("Lightning", "Strikes the app saw while it was running, today and over time."), unsafe_allow_html=True)
    start_of_day = datetime.combine(now.date(), datetime.min.time(), tzinfo=tz).timestamp()
    today = storage.strikes_between(db, start_of_day, now.timestamp())
    last = storage.latest_strike(db)
    closest = min((d for _, d in today), default=None)
    last_when = "--"
    if last is not None:
        lt = datetime.fromtimestamp(last[0], tz)
        last_when = timefmt.time_text(lt) if lt.date() == now.date() else timefmt.stamp(lt)
    stat = lambda icon, label, value: (f'<div style="display:flex;align-items:center;gap:14px">{icon}<div>'
                                       f'<div style="font-size:16px">{label}</div><div style="font-size:34px;font-weight:800">{value}</div></div></div>')
    st.markdown(f'<div class="wl-panel wl-bignum">{_sky_strip(_storm_sky(), "55%")}<div style="position:relative;z-index:1;display:flex;'
                f'align-items:center;gap:30px;flex-wrap:wrap">{line_icons.icon("bolt", 70, "#f6c445", 1.6)}<i class="wl-div"></i>'
                f'{stat("", "Strikes today", len(today))}<i class="wl-div"></i>'
                f'{stat(line_icons.icon("pin", 30, "#7cc4ff"), "Closest strike today", units.format_value("miles", closest, metric, 1) if closest is not None else "--")}'
                f'<i class="wl-div"></i>{stat(line_icons.icon("clock", 30, "#f6c445"), "Last strike", html.escape(last_when))}</div></div>',
                unsafe_allow_html=True)

    span_choice = st.segmented_control("Range", ["30 days", "1 year"], default="30 days", key="lightning_range",
                                       label_visibility="collapsed") or "30 days"
    span = 30 if span_choice == "30 days" else 365
    since = datetime.combine(now.date() - timedelta(days=span - 1), datetime.min.time(), tzinfo=tz).timestamp()
    by_day = lightning_history.per_day(storage.strikes_between(db, since, now.timestamp()), tz)
    if not by_day:
        empty_card("No strikes in this range", "Strikes appear here when the station reports them.")
    else:
        dark = theme.is_dark()
        days = [d for d, _, _ in by_day]
        total = sum(c for _, c, _ in by_day)
        with st.container(border=True):
            fig = charts.figure(dark, height=260)
            fig.add_trace(go.Bar(x=days, y=[c for _, c, _ in by_day], name="Strikes", marker_color="#38c6ec"))
            fig.update_layout(title=dict(text=f"Daily strike count · total {total:,} in {span_choice}", x=0, xanchor="left",
                                         font=dict(size=16)), showlegend=False)
            charts.show(fig)
        with st.container(border=True):
            nearest = min(m for _, _, m in by_day)
            fig = charts.figure(dark, height=260)
            fig.add_trace(go.Scatter(x=days, y=[units.convert("miles", m, metric) for _, _, m in by_day], mode="markers+lines",
                                     line=dict(color="#38c6ec", width=2), marker=dict(size=7, color="#f6c445"),
                                     fill="tozeroy", fillcolor="rgba(56,198,236,.12)", name="Closest"))
            fig.update_layout(title=dict(text=f"Closest strike each day · nearest {units.format_value('miles', nearest, metric, 1)} "
                                              "(lower is closer)", x=0, xanchor="left", font=dict(size=16)), showlegend=False)
            fig.update_yaxes(title_text=units.unit("miles", metric), rangemode="tozero")
            charts.show(fig)
    if today:
        with st.expander(f"Today's strikes ({len(today)})"):
            theme.table([{"Time": timefmt.time_text(datetime.fromtimestamp(ts, tz)),
                          f"Distance ({units.unit('miles', metric)})": round(units.convert("miles", d, metric), 1)}
                         for ts, d in reversed(today[-50:])])
    reach = "about 40 km" if metric else "about 25 miles"
    st.markdown(f'<div class="wl-panel wl-health">{line_icons.icon("station", 24, "#3ddc84")}<span><b style="color:#3ddc84">'
                f'Station-detected lightning</b> · your lightning sensor hears strikes up to {reach} away. Weather Lab counts the '
                'strikes it saw while it was running.</span></div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Fire
def _fire_day_note(f: dict, metric: bool) -> str:
    from weatherlab import fire
    return fire.day_note(f, metric)


def _fire_gauge(share: float, colour: str, level: str) -> str:
    """A half-circle gauge from Low (green) to Extreme (purple), with a needle at the FWI."""
    import math
    cx, cy, r = 110, 104, 84
    segs = [("#3ddc84", 0, .104), ("#f6c445", .104, .224), ("#f08a3c", .224, .426), ("#ef5b4c", .426, .76), ("#b06cff", .76, 1)]

    def p(t, rr=r):
        a = math.pi * (1 - t)
        return cx + rr * math.cos(a), cy - rr * math.sin(a)
    arcs = ""
    for c, a0, a1 in segs:
        x0, y0 = p(a0)
        x1, y1 = p(a1)
        arcs += f'<path d="M{x0:.1f},{y0:.1f} A{r},{r} 0 0 1 {x1:.1f},{y1:.1f}" stroke="{c}" stroke-width="16" fill="none"/>'
    nx, ny = p(share, r - 14)
    return (f'<svg viewBox="0 0 220 140" width="220" height="140" aria-label="Fire danger {html.escape(level)}">{arcs}'
            f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#eaf2fb" stroke-width="4" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="7" fill="#eaf2fb"/>'
            f'<text x="20" y="128" font-size="12" fill="#9db0c4">Low</text><text x="200" y="128" font-size="12" fill="#9db0c4" text-anchor="end">Extreme</text>'
            f'<text x="{cx}" y="134" font-size="15" font-weight="700" fill="{colour}" text-anchor="middle">{html.escape(level)}</text></svg>')


def fire_page() -> None:
    """Fire weather (0.37.64, the redesign): the danger level with a gauge and what it means, the readings behind it,
    the National Weather Service forecast text and the next days' danger."""
    from weatherlab import fire
    s = load_settings()
    metric = units.is_metric(s.units)
    tz = _tz(s)
    db = storage.connect()
    st.markdown(theme.page_head("Fire weather", "Fire danger from your station's readings and the National Weather Service forecast."), unsafe_allow_html=True)
    rec = storage.latest_fire(db)
    if rec is None:
        empty_card("Fire weather appears once the station has sent readings for an hour.", "It updates every hour.")
        return
    d = fire.danger(rec.get("fwi"))
    sky = f"{hero._clouds_svg(False)} center/cover no-repeat, {hero.sky_bg('dusk', hero.GRADS['dusk'])}"
    advice = "".join(f'<div style="display:flex;gap:8px;margin:4px 0">{line_icons.icon("check", 18, "#9db0c4")}<span>{html.escape(a)}</span></div>'
                     for a in d["advice"])
    st.markdown(f'<div class="wl-panel wl-bignum">{_sky_strip(sky, "55%")}<div style="position:relative;z-index:1;display:flex;'
                f'align-items:center;gap:26px;flex-wrap:wrap;width:100%">'
                f'<svg viewBox="0 0 24 24" width="74" height="74" fill="none" stroke="#f08a3c" stroke-width="1.6" stroke-linecap="round" '
                f'stroke-linejoin="round" aria-hidden="true"><path d="M12 21c-4 0-6.5-2.7-6.5-6.2 0-3.8 3-5.6 3.6-9.3 2.4 1.6 3.7 3.7 3.9 6 '
                f'.8-.9 1.3-2 1.4-3.3 2.4 2 4.1 4.5 4.1 7.3 0 3-2.5 5.5-6.5 5.5z"/><path d="M12 21c-1.8 0-3-1.2-3-2.9 0-1.8 1.4-2.8 2-4.4 '
                f'1.9 1.3 4 2.6 4 4.6 0 1.6-1.3 2.7-3 2.7z"/></svg><i class="wl-div"></i>'
                f'<div><div class="wl-bw" style="font-size:30px">Fire danger</div><div class="wl-note">Fire Weather Index {rec["fwi"]:.1f}'
                f' · as of {html.escape(rec["timestamp"][11:16])}</div><div class="wl-bw" style="color:{d["colour"]};margin-top:6px">'
                f'{html.escape(d["level"])}</div></div>{_fire_gauge(d["share"], d["colour"], d["level"])}'
                f'<div style="font-size:15px;max-width:330px">{advice}</div></div></div>', unsafe_allow_html=True)

    now = time.time()
    day = storage.readings_between(db, now - 86400, now + 1)
    latest = day[-1][1] if day else {}

    def line(key, colour):
        hours: dict = {}
        for t, r in day:
            if r.get(key) is not None:
                hours.setdefault(int(t // 3600), []).append(r[key])
        return sparks.spark_svg([units.convert(key, sum(v) / len(v), metric) for _, v in sorted(hours.items())], colour, h=34)
    temps = [r["tempf"] for _, r in day if r.get("tempf") is not None]
    cards = []
    if latest.get("tempf") is not None:
        t = units.format_value("tempf", latest["tempf"], metric, 0).split(" ", 1)
        note = f"High {units.convert('tempf', max(temps), metric):.0f}° / Low {units.convert('tempf', min(temps), metric):.0f}°" if temps else ""
        cards.append(hero.metric_html(line_icons.icon("thermo", 24, "#f6c445"), "Temperature", t[0], t[1] if len(t) > 1 else "", note, line("tempf", "#f6c445")))
    if latest.get("humidity") is not None:
        dew = f"Dew point {units.format_value('dewpointf', latest['dewpointf'], metric, 0)}" if latest.get("dewpointf") is not None else ""
        cards.append(hero.metric_html(line_icons.icon("drop", 24, "#7cc4ff"), "Humidity", f"{latest['humidity']:.0f}%", "", dew, line("humidity", "#5b9df0")))
    if latest.get("windspeedmph") is not None:
        w = units.format_value("windspeedmph", latest["windspeedmph"], metric, 0).split(" ", 1)
        gust = max((r["windgustmph"] for _, r in day if r.get("windgustmph") is not None), default=None)
        cards.append(hero.metric_html(line_icons.icon("wind", 24, "#7cc4ff"), "Wind", w[0], w[1] if len(w) > 1 else "",
                                      f"Gusts {units.format_value('windgustmph', gust, metric, 0)} today" if gust is not None else "",
                                      line("windspeedmph", "#38c6ec")))
    rain_vals = [r.get("dailyrainin") or 0 for _, r in day]
    rain = units.format_value("dailyrainin", rec.get("rain_in") or 0, metric, 2).split(" ", 1)
    cards.append(hero.metric_html(line_icons.icon("rain", 24, "#7cc4ff"), "Recent rain", rain[0], rain[1] if len(rain) > 1 else "",
                                  f"{rec['days_since_rain']} days since rain", sparks.spark_svg(rain_vals, "#38c6ec", h=34)))
    st.markdown(f'<div class="wl-metrics">{"".join(cards)}</div>', unsafe_allow_html=True)

    text = ""
    if s.latitude is not None and s.longitude is not None:
        try:
            from weatherlab.screens.common import _points
            from weatherlab.screens.outlook import _daily
            periods = _daily(_points(s.latitude, s.longitude, s.nws_contact)["forecast"], s.nws_contact)
            text = next((p["detail"] for p in periods if p.get("detail")), "")
        except Exception:
            text = ""
    if text:
        st.markdown(f'<div class="wl-panel wl-health" style="align-items:flex-start;padding:16px 20px">'
                    f'{line_icons.icon("info", 34, "#38c6ec")}<div><b style="font-size:18px">NWS forecast</b>'
                    f'<div class="wl-note">From the National Weather Service</div></div>'
                    f'<span style="margin-left:18px;padding-left:18px;border-left:1px solid rgba(157,176,196,.35)">{html.escape(text)}</span></div>',
                    unsafe_allow_html=True)
    forecast = rec.get("forecast") or []
    if len(forecast) > 1:
        cells = []
        for f in forecast[1:4]:
            fd = fire.danger(f["fwi"])
            when = f["day"]
            try:
                when = f'{datetime.fromisoformat(f["date"]):%a, %b} {datetime.fromisoformat(f["date"]).day}'
            except Exception:
                pass
            cells.append(f'<div style="flex:1;min-width:180px;padding:0 16px;border-left:1px solid rgba(157,176,196,.3)">'
                         f'<div style="display:flex;justify-content:space-between;align-items:center"><b>{html.escape(when)}</b>'
                         f'<span class="wl-badge" style="color:{fd["colour"]};background:{fd["colour"]}22">{fd["level"]}</span></div>'
                         f'<div style="font-size:15px;margin-top:6px">FWI {f["fwi"]:.1f}</div>'
                         f'<div class="wl-note">{html.escape(_fire_day_note(f, metric))}</div></div>')
        st.markdown('<div class="wl-panel" style="display:flex;align-items:center;gap:6px;padding:16px 20px;margin-bottom:14px;flex-wrap:wrap">'
                    '<div style="min-width:150px"><div class="wl-ptitle" style="margin:0">Next 3 days</div><div class="wl-note">Fire weather outlook</div></div>'
                    + "".join(cells) + "</div>", unsafe_allow_html=True)
    else:
        st.caption("No forecast yet. It comes from the National Weather Service, so it covers the United States only.")
    with st.expander("The index and its parts"):
        st.markdown(theme.grid_html([
            _tile("Fire Weather Index", f"{rec['fwi']:.1f}", d["level"]), _tile("FFMC", f"{rec['ffmc']:.1f}", "fine fuels"),
            _tile("DMC", f"{rec['dmc']:.1f}", "duff layer"), _tile("DC", f"{rec['dc']:.1f}", "deep drought"),
            _tile("ISI", f"{rec['isi']:.1f}", "spread index"), _tile("BUI", f"{rec['bui']:.1f}", "build-up index"),
        ]), unsafe_allow_html=True)
    st.caption("Approximate. It uses the latest reading instead of the usual 1 pm observation, assumes no rain in the forecast, "
               "and uses day-length values for about 30° north. Danger levels use the usual Canadian Fire Weather Index breaks.")


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
    """Tropics (0.37.64, the redesign): a map of the active storms and your station beside a card for each storm, with
    a legend and the source."""
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
    storms = cache.get("storms", [])
    map_col, list_col = st.columns([1.6, 1], gap="medium")
    with map_col, st.container(border=True):
        fig = go.Figure()
        fig.add_trace(go.Scattermap(lat=[s.latitude], lon=[s.longitude], mode="markers+text", marker=dict(size=14, color="#38c6ec"),
                                    text=["Your station"], textposition="bottom center", textfont=dict(color="#ffffff"), name="You"))
        if storms:
            colours = ["#ef5b4c" if "hurricane" in x["class"].lower() or x["class"].upper() in ("HU", "MH") else "#f6c445" for x in storms]
            fig.add_trace(go.Scattermap(lat=[x["lat"] for x in storms], lon=[x["lon"] for x in storms], mode="markers+text",
                                        marker=dict(size=18, color=colours), text=[x["name"] for x in storms],
                                        textposition="top center", textfont=dict(color="#ffffff"), name="Storms"))
            lats = [x["lat"] for x in storms] + [s.latitude]
            lons = [x["lon"] for x in storms] + [s.longitude]
            spread = max(max(lats) - min(lats), max(lons) - min(lons))
            centre, zoom = dict(lat=(max(lats) + min(lats)) / 2, lon=(max(lons) + min(lons)) / 2), (2 if spread > 40 else 3 if spread > 20 else 4)
        else:
            centre, zoom = dict(lat=s.latitude - 8, lon=s.longitude + 20), 2
        fig.update_layout(map=dict(style="carto-darkmatter" if theme.is_dark() else "open-street-map", center=centre, zoom=zoom),
                          margin=dict(l=0, r=0, t=0, b=0), height=430, showlegend=False)
        charts.show(fig)
    with list_col:
        st.markdown(f'<div class="wl-ptitle">Current systems <span class="wl-note">({len(storms)} active)</span></div>', unsafe_allow_html=True)
        if not storms:
            st.markdown(f'<div class="wl-panel wl-health">{line_icons.icon("check", 26, "#3ddc84", 2.2)}<span>The National Hurricane '
                        'Center has no active tropical storms or hurricanes right now.</span></div>', unsafe_allow_html=True)
        for x in storms:
            hurricane = "hurricane" in x["class"].lower() or x["class"].upper() in ("HU", "MH")
            colour = "#ef5b4c" if hurricane else "#f6c445"
            kind = {"TS": "Tropical storm", "HU": "Hurricane", "MH": "Major hurricane", "TD": "Tropical depression",
                    "STS": "Subtropical storm", "PTC": "Potential tropical cyclone"}.get(x["class"].upper(), x["class"] or "Storm")
            st.markdown(f'<div class="wl-panel wl-kvp" style="border-color:{colour}99;margin-bottom:12px">'
                        f'<div style="display:flex;align-items:center;gap:10px;font-size:19px;font-weight:750">'
                        f'<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="{colour}" stroke-width="2" stroke-linecap="round" aria-hidden="true">'
                        f'<path d="M12 9a3 3 0 1 0 0 6 3 3 0 1 0 0-6z"/><path d="M9 4.5C5 6 3.5 10 4.5 13M15 19.5c4-1.5 5.5-5.5 4.5-8.5"/></svg>'
                        f'{html.escape(kind)} {html.escape(x["name"])}</div>'
                        f'<div class="wl-kv" style="margin-top:8px">'
                        f'<div><span>Winds</span><b>{units.format_value("windspeedmph", x["wind_mph"], metric, 0)}</b></div>'
                        f'<div><span>Moving</span><b>{html.escape(_moving(x, metric))}</b></div>'
                        f'<div><span>Distance from station</span><b>{units.format_value("miles", x["miles"], metric, 0)} {html.escape(x["direction"])}</b></div>'
                        f'<div><span>Updated</span><b>{html.escape(x["updated"][11:16] or x["updated"])}</b></div></div></div>',
                        unsafe_allow_html=True)
    st.markdown('<div class="wl-panel wl-stats"><div><div><b style="font-size:19px">Legend</b></div></div>'
                '<div><b style="color:#38c6ec;font-size:22px">●</b><span>Your station</span></div>'
                '<div><b style="color:#f6c445;font-size:22px">●</b><span>Tropical storm or depression</span></div>'
                '<div><b style="color:#ef5b4c;font-size:22px">●</b><span>Hurricane (74 mph and up)</span></div></div>',
                unsafe_allow_html=True)
    note = (f"Checked at {cache['checked']}." if cache.get("ok") else
            f"Couldn't reach the center just now, so this is the list from {cache['checked']}.")
    st.markdown(f'<div class="wl-panel wl-health">{line_icons.icon("info", 24, "#38c6ec")}<span><b>Source:</b> National Hurricane Center. '
                f'{html.escape(note)}</span></div>', unsafe_allow_html=True)


@st.cache_data(ttl=86400, show_spinner=False)
def _radar_station(lat: float, lon: float, contact: str) -> str:
    return nws.points(lat, lon, contact).get("radar", "")


def radar_page() -> None:
    """Radar (0.37.64, the redesign): the radar loop with your station's readings and the colour scale beside it."""
    s = load_settings()
    metric = units.is_metric(s.units)
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
    choice = st.segmented_control("View", list(views), default=default, key="radar_view", label_visibility="collapsed",
                                  format_func=lambda v: (":material/radar: " if v == "Local radar" else ":material/public: ") + v) or default
    left, right = st.columns([2.2, 1], gap="medium")
    with left, st.container(border=True):
        st.image(views[choice])
        st.caption(f"Radar loop from the National Weather Service{f', station {station}' if station else ''}. It plays on its own.")
    with right:
        row = storage.latest(storage.connect())
        if row:
            r = row[1]
            temp = f"{units.convert('tempf', r['tempf'], metric):.0f}" if r.get("tempf") is not None else "--"
            name = stations.name_of(stations.current())
            wind = units.format_value("windspeedmph", r.get("windspeedmph"), metric, 0) if r.get("windspeedmph") is not None else "--"
            if r.get("winddir") is not None and (r.get("windspeedmph") or 0) >= 1:
                from weatherlab import wind_rose
                wind += " " + wind_rose.NAMES[round(r["winddir"] / 22.5) % 16]
            humidity = "--" if r.get("humidity") is None else f"{r['humidity']:.0f}%"
            st.markdown(f'<div class="wl-panel wl-kvp" style="margin-bottom:14px"><div class="wl-ptitle" style="font-size:19px">Weather Lab station</div>'
                        f'<div class="wl-note">{html.escape(name)}</div>'
                        f'<div style="font-size:56px;font-weight:800;letter-spacing:-1.5px;margin:6px 0">{temp}<span style="font-size:26px">{units.unit("tempf", metric)}</span></div>'
                        f'<div class="wl-kv">'
                        f'<div><span>{line_icons.icon("wind", 18, "#7cc4ff")} Wind</span><b>{html.escape(wind)}</b></div>'
                        f'<div><span>{line_icons.icon("drop", 18, "#7cc4ff")} Humidity</span><b>{humidity}</b></div>'
                        f'<div><span>{line_icons.icon("gauge", 18, "#7cc4ff")} Pressure</span><b>{units.format_value("baromrelin", r.get("baromrelin"), metric, 2)}</b></div>'
                        f'<div><span>{line_icons.icon("rain", 18, "#7cc4ff")} Rain today</span><b>{units.format_value("dailyrainin", r.get("dailyrainin"), metric, 2)}</b></div>'
                        f'</div></div>', unsafe_allow_html=True)
        st.markdown('<div class="wl-panel wl-kvp"><div class="wl-ptitle" style="font-size:17px">Radar colours (rain)</div>'
                    '<div style="height:14px;border-radius:7px;background:linear-gradient(90deg,#3ddc84,#1fa64a,#f6e445,#f08a3c,#ef3b2c,#c0287f,#b06cff);margin:8px 0"></div>'
                    '<div style="display:flex;justify-content:space-between" class="wl-note"><span>Light</span><span>Moderate</span><span>Heavy</span></div></div>',
                    unsafe_allow_html=True)
        st.markdown("")
        if station:
            st.link_button("Open the full local radar", f"https://radar.weather.gov/station/{station.lower()}/standard",
                           icon=":material/open_in_new:", use_container_width=True)
        else:
            st.link_button("Open the full radar", "https://radar.weather.gov/", icon=":material/open_in_new:", use_container_width=True)
