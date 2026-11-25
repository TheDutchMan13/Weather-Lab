"""Pages under Outlook: forecast, heat, wind, sun and astronomy."""

import html
import plotly.graph_objects as go
import streamlit as st
import time
from datetime import datetime, timedelta, timezone
from weatherlab import astro, astro_art, hero, line_icons, sparks, wx_icons, charts, forecast_card, forecast_check, forecast_view, heat_safety, history, nws, storage, sun_uv, theme, units, windmap, wind_rose, timefmt
from weatherlab.settings import Settings, load_settings
from weatherlab.screens.common import _alert_box, _clock, _hourly, _points, _start_of_today, _tile, _tz, empty_card, start_poller


@st.cache_data(ttl=600, show_spinner=False)
def _alerts(lat: float, lon: float, contact: str) -> list[dict]:
    return nws.alerts(lat, lon, contact)


@st.cache_data(ttl=1800, show_spinner=False)
def _daily(url: str, contact: str) -> list[dict]:
    return nws.forecast_daily(url, contact)


def _report_card(db, s: Settings) -> None:
    """The forecast report card (0.37.54): highs and lows, graded by how many days ahead the forecast was made."""
    metric = units.is_metric(s.units)
    scale, unit, margin_f = (5 / 9, "°C", 3.6) if metric else (1, "°F", 3.0)
    margin = "2 °C" if metric else "3 °F"
    st.markdown(theme.section_html("Forecast report card"), unsafe_allow_html=True)
    span = st.segmented_control("Look back", ["30 days", "90 days", "1 year"], default="30 days",
                                key="card_span", label_visibility="collapsed") or "30 days"
    days_back = {"30 days": 30, "90 days": 90, "1 year": 365}[span]
    today = datetime.now(_tz(s)).date()
    since = (today - timedelta(days=days_back)).isoformat()
    actuals = {d: (summary.get("tempf_max"), summary.get("tempf_min")) for d, summary in history.all_daily(db)}
    found = forecast_card.pairs(storage.forecast_ahead(db, since), actuals, today)
    rows = forecast_card.grade_rows(found, within_f=margin_f)
    grade = forecast_card.letter(rows)
    if not rows or grade is None:
        st.caption("The report card fills in as Weather Lab saves the forecast each day. The first grades appear "
                   "after the first full day; the 3 days ahead row needs three days.")
        return
    mark, pct, n = grade
    best = min((r for r in rows if r["high"]), key=lambda r: r["lead"], default=None)
    far = max((r for r in rows if r["high"]), key=lambda r: r["lead"], default=None)
    tiles = [_tile("Grade", mark, f"{pct}% within {margin}, next-day forecast")]
    if best and far and far["lead"] > best["lead"]:
        tiles.append(_tile(f"Highs {forecast_card.lead_name(best['lead']).lower()}", f"{best['high']['miss'] * scale:.1f} {unit}", "average miss"))
        tiles.append(_tile(f"Highs {forecast_card.lead_name(far['lead']).lower()}", f"{far['high']['miss'] * scale:.1f} {unit}", "average miss"))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)

    def cell(x: dict | None) -> str:
        if not x:
            return "--"
        sign = "+" if x["bias"] > 0 else ""
        return f"{x['miss'] * scale:.1f} {unit} off · {x['within']}% within {margin} · {sign}{x['bias'] * scale:.1f} bias"
    theme.table([{"Made": forecast_card.lead_name(r["lead"]), "Highs": cell(r["high"]), "Lows": cell(r["low"]),
                  "Days": str(max((r["high"] or {}).get("days", 0), (r["low"] or {}).get("days", 0)))} for r in rows])
    st.caption(f"Each day's forecast is the first one Weather Lab saved that day, compared with your station's high "
               f"and low. Bias above zero means the forecast ran warm. The grade is the share of next-day highs and "
               f"lows within {margin}: A is 80% or more, B 65%, C 50%, D 35%.")


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
    theme.table([{"Day": d.strftime("%a %b %d"), "Forecast high": units.format_value("tempf", f, metric, 0),
                  "Actual high": units.format_value("tempf", a, metric, 0), "Forecast minus actual": delta(diff)}
                 for d, f, a, diff in rows[:14]])


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


def _heat_tone(index) -> str | None:
    """Colour for a heat index, from the heat safety levels."""
    if index is None:
        return None
    level, _ = heat_safety.level_for(index)
    return {"Comfortable": "ok", "Caution": "info", "Extreme caution": "warn"}.get(level, "bad")


def _uv_tone(uv) -> str | None:
    """Colour for a UV index, with the same breaks as the Home page: low, moderate, high, very high."""
    if uv is None:
        return None
    return "ok" if uv < 3 else "info" if uv < 6 else "warn" if uv < 8 else "bad"


def forecast_page() -> None:
    """Forecast (0.37.63, the redesign): the next 24 hours, the 7-day outlook beside how accurate past forecasts were,
    then the full temperature curve, the report card and recent days under More detail."""
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.page_head("Forecast", "National Weather Service forecast and how close past forecasts were."), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        empty_card("Set your latitude and longitude in Settings, under Station.")
        return
    contact = s.nws_contact
    try:
        alerts = _alerts(s.latitude, s.longitude, contact)
        if alerts:  # only when there are some: no alerts needs no box (0.37.63)
            st.markdown("".join(_alert_box(a) for a in alerts), unsafe_allow_html=True)
        pts = _points(s.latitude, s.longitude, contact)
        periods = _daily(pts["forecast"], contact)
        hourly = _hourly(pts["forecastHourly"], contact) if pts.get("forecastHourly") else []
    except nws.NwsError as exc:
        st.error(str(exc))
        return

    metric = units.is_metric(s.units)
    now = datetime.now(tz)
    _next_hours(hourly, s, tz, metric, now)
    left, right = st.columns([1.35, 1], gap="medium")
    with left:
        _seven_days(periods, tz, metric, now.date())
    with right:
        _accuracy_panel(storage.connect(), s)
    with st.expander("More detail: the temperature curve, the report card and recent days", icon=":material/insights:"):
        views = forecast_view.overview_html(hourly, s.latitude, s.longitude, tz, metric, len(alerts), now)
        if views:
            st.markdown(forecast_view.STYLE + views, unsafe_allow_html=True)
        _report_card(storage.connect(), s)
        _forecast_accuracy(storage.connect(), s)
        _rain_accuracy(storage.connect(), s)


def _next_hours(hourly, s: Settings, tz, metric: bool, now) -> None:
    """Every second hour for the next 24, with the sky, temperature and rain chance."""
    hours = forecast_view.overview_hours(hourly, s.latitude, s.longitude, tz, now, count=12, step=2)
    if not hours:
        return
    cells = []
    for h in hours:
        t = forecast_view.to_shown(h["temp"], h["unit"], metric)
        pop = h.get("pop") or 0
        cells.append(f'<div>{html.escape(forecast_view.clock(h["when"]).replace(":00", ""))}<br>'
                     f'{wx_icons.forecast_icon(h["short"], h["night"], 40)}<b>{"--" if t is None else f"{t:.0f}°"}</b>'
                     f'<span class="wl-pop">{line_icons.icon("drop", 14)} {pop:.0f}%</span></div>')
    st.markdown('<div class="wl-panel wl-outlook"><div style="display:flex;justify-content:space-between;align-items:baseline">'
                '<div class="wl-ptitle">Next 24 hours</div><span class="wl-note">2 hour forecast · National Weather Service</span></div>'
                f'<div class="wl-hours">{"".join(cells)}</div></div>', unsafe_allow_html=True)


def _seven_days(periods, tz, metric: bool, today) -> None:
    rows = forecast_view.days(periods, tz, today, 7)
    if not rows:
        return
    out = []
    for r in rows:
        high = forecast_view.to_shown(r["high"], r["unit"], metric)
        low = forecast_view.to_shown(r["low"], r["unit"], metric)
        date_text = f'{r["date"]:%a}, {r["date"]:%b} {r["date"].day}' if r["name"] == "Today" else f'{r["date"]:%b} {r["date"].day}'
        name = r["name"] if r["name"] == "Today" else f'{r["date"]:%a}'
        pop = "–" if r["pop"] is None else f'{round(r["pop"])}%'
        out.append(f'<div><div><b>{html.escape(name)}</b><small>{html.escape(date_text)}</small></div>'
                   f'{wx_icons.forecast_icon(r["short"], r["night_only"], 36)}<span>{html.escape(r["short"])}</span>'
                   f'<span class="wl-up">↑ {"--" if high is None else f"{high:.0f}°"}</span>'
                   f'<span class="wl-dn">↓ {"--" if low is None else f"{low:.0f}°"}</span>'
                   f'<span class="wl-pp">{line_icons.icon("drop", 15)} {pop}</span></div>')
    st.markdown('<div class="wl-panel" style="padding:16px 22px"><div style="display:flex;justify-content:space-between;'
                'align-items:baseline"><div class="wl-ptitle">7 day outlook</div><span class="wl-note">National Weather Service'
                f'</span></div><div class="wl-daysrows">{"".join(out)}</div></div>', unsafe_allow_html=True)


ACCURACY_SPANS = {"30 days": 30, "90 days": 90, "1 year": 365}


def _accuracy_panel(db, s: Settings) -> None:
    """How close past forecasts were, for the span picked: the average miss on highs and how often the rain chance was right."""
    metric = units.is_metric(s.units)
    scale, unit = (5 / 9, "°C") if metric else (1, "°F")
    with st.container(border=True, key="wl-accuracy"):
        st.markdown('<div class="wl-ptitle" style="margin-bottom:2px">Forecast accuracy</div>'
                    '<div class="wl-note">How close the past forecasts were for this location.</div>', unsafe_allow_html=True)
        span = st.segmented_control("Span", list(ACCURACY_SPANS), default="30 days", key="accuracy_span",
                                    label_visibility="collapsed") or "30 days"
        since = datetime.now(_tz(s)).date() - timedelta(days=ACCURACY_SPANS[span])
        daily = history.all_daily(db)
        actuals = {d: x["tempf_max"] for d, x in daily if x.get("tempf_max") is not None}
        rows = [r for r in forecast_check.compare(storage.forecast_highs(db), actuals) if r[0] >= since]
        stats = forecast_check.accuracy(rows)
        pops = {d: v for d, v in storage.forecast_pops(db).items() if d >= since}
        rained = {d: (x.get("rain_in") or 0.0) >= 0.01 for d, x in daily}
        hit = forecast_check.rain_hit_rate(forecast_check.rain_summary(pops, rained))
        miss = f"{stats['mae'] * scale:.1f}{unit}" if stats["days"] else "--"
        st.markdown('<div class="wl-statrows">'
                    f'<div>{line_icons.icon("thermo", 34, "#f07a5a")}<div><b>High temperature error</b>'
                    f'<span>Average difference vs. observed</span></div><span class="wl-big">{miss}</span></div>'
                    f'<div>{line_icons.icon("rain", 34, "#7cc4ff")}<div><b>Rain chance results</b>'
                    f'<span>Correctly predicted rain / no rain</span></div><span class="wl-big">{"--" if hit is None else f"{hit}%"}</span></div>'
                    '</div>', unsafe_allow_html=True)
        if stats["days"]:
            text = f"Last {span}: high temps were off by {stats['mae'] * scale:.1f}{unit} on average"
            text += f", and the forecast correctly predicted rain {hit}% of the time." if hit is not None else "."
        else:
            text = "This fills in once Weather Lab has saved a forecast and a day has finished. Forecasts are saved every three hours."
        st.markdown(f'<div class="wl-note-line">{line_icons.icon("info", 22)}<span>{html.escape(text)}</span></div>',
                    unsafe_allow_html=True)


WIND_PERIODS = {"Last 24 hours": 1, "Last 7 days": 7, "Last 30 days": 30}


def _level_ladder_html(current: str | None, metric: bool) -> str:
    """All five heat safety levels with the current one marked."""
    rows = []
    for low, name, advice in heat_safety.LEVELS:
        start = "under " + units.format_value("heat_index", 80, metric, 0) if low <= -999 else units.format_value("heat_index", low, metric, 0) + " and up"
        on = name == current
        bg = "background:rgba(232,131,58,0.14);border:1px solid rgba(232,131,58,0.5);" if on else "border:1px solid transparent;"
        rows.append(
            f'<div style="display:flex;gap:10px;align-items:center;padding:8px 10px;border-radius:8px;{bg}">'
            f'<span style="width:12px;height:12px;border-radius:50%;background:{heat_safety.LEVEL_COLOURS[name]};flex:none"></span>'
            f'<span style="width:130px;font-weight:600">{html.escape(name)}</span>'
            f'<span style="flex:1;font-size:13px;opacity:0.8">{html.escape(advice.split(".")[0])}'
            f'{" · <b>you are here</b>" if on else ""}</span>'
            f'<span style="font-size:13px;opacity:0.8;white-space:nowrap">{html.escape(start)}</span></div>')
    return "".join(rows)


def heat_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    metric = units.is_metric(s.units)
    db = storage.connect()
    st.markdown(theme.page_head("Heat safety", "Heat index now and today's peak, against the heat safety levels."), unsafe_allow_html=True)
    latest = storage.latest(db)
    if latest is None:
        empty_card("No readings yet", "Heat safety fills in once the station has reported.")
        return
    _, data = latest
    now = heat_safety.status(data.get("tempf"), data.get("humidity"))
    today = storage.readings_between(db, _start_of_today(s), time.time() + 1)
    series = [(ts, r.get("tempf"), heat_safety.heat_index(r.get("tempf"), r.get("humidity"))) for ts, r in today]
    peak = max((x for x in series if x[2] is not None), key=lambda x: x[2], default=None)
    hours = heat_safety.hours_by_level([(ts, hi) for ts, _, hi in series])
    st.markdown(theme.grid_html([
        theme.strip_tile_html("Heat index now", units.format_value("heat_index", now["heat_index"], metric, 0),
                              now["level"], _heat_tone(now["heat_index"]), word=""),
        theme.strip_tile_html("Air temperature", units.format_value("tempf", data.get("tempf"), metric, 0), "right now"),
        theme.strip_tile_html("Highest heat index today", units.format_value("heat_index", peak[2] if peak else None, metric, 0),
                              _clock(peak[0]) if peak else "no data yet", _heat_tone(peak[2] if peak else None)),
        theme.strip_tile_html("Hours at Danger or worse", f"{heat_safety.danger_hours(hours):.1f} h", "today so far",
                              "bad" if heat_safety.danger_hours(hours) > 0 else "ok"),
    ]), unsafe_allow_html=True)
    if now["advice"]:
        show = st.warning if now["level"] in ("Extreme caution", "Danger", "Extreme danger") else st.info
        show(now["advice"])
    fig = charts.figure(dark)
    xs = [datetime.fromtimestamp(ts, _tz(s)) for ts, _, _ in series]
    fig.add_scatter(x=xs, y=[units.convert("tempf", t, metric) for _, t, _ in series], name="Air temperature", mode="lines",
                    line=dict(color=charts.MEASURE["temp"]))
    fig.add_scatter(x=xs, y=[units.convert("heat_index", h, metric) for _, _, h in series], name="Heat index", mode="lines",
                    line=dict(color=charts.CHART_COLORS[1]))
    for low, name, _ in heat_safety.LEVELS:
        if low >= 91:   # shade the caution levels that matter outdoors: Extreme caution and above
            fig.add_hline(y=units.convert("heat_index", low, metric), line_dash="dot", line_width=1,
                          line_color=heat_safety.LEVEL_COLOURS[name], annotation_text=name, annotation_position="top left")
    charts.show(fig)
    st.caption("Heat index combines air temperature and humidity. Dotted lines mark where each heat safety level starts.")

    left, right = st.columns(2)
    with left:
        st.markdown(theme.section_html("Heat safety levels"), unsafe_allow_html=True)
        st.markdown(_level_ladder_html(now["level"] if now["heat_index"] is not None else None, metric), unsafe_allow_html=True)
    with right:
        st.markdown(theme.section_html("Time in each level today"), unsafe_allow_html=True)
        theme.table([{"Level": name, "Hours": f"{hours[name]:.1f} h"} for name in heat_safety.LEVEL_NAMES])

    bad = heat_safety.dangerous_days(history.all_daily(db))
    st.markdown(theme.section_html("Dangerous heat days", f"days with a heat index of {units.format_value('heat_index', heat_safety.DANGER_INDEX, metric, 0)} or more"),
                unsafe_allow_html=True)
    if bad:
        theme.table([{"Day": f"{d:%b} {d.day}, {d.year}", "Highest heat index": units.format_value("heat_index", hi, metric, 0), "Level": lvl}
                     for d, hi, lvl in bad[:15]])
        if len(bad) > 15:
            st.caption(f"Showing the worst 15 of {len(bad)}.")
    else:
        st.caption("None recorded yet.")
    st.caption("This is general guidance, not medical advice.")


def wind_page() -> None:
    """Wind (0.37.64, the redesign): the wind now, four figures for the period, the wind rose beside them, and the
    hourly speed and gust."""
    s = load_settings()
    dark = theme.is_dark()
    metric = units.is_metric(s.units)
    tz = _tz(s)
    db = storage.connect()
    st.markdown(theme.page_head("Wind", "Where the wind came from and how strong it was."), unsafe_allow_html=True)
    period = st.segmented_control("Period", list(WIND_PERIODS), default="Last 24 hours",
                                  key="wind_period", label_visibility="collapsed") or "Last 24 hours"
    end = time.time()
    timed = storage.readings_between(db, end - WIND_PERIODS[period] * 86400, end + 1)
    rows = [r for _, r in timed]
    counts, total = wind_rose.rose(rows)
    if total == 0:
        empty_card("No wind readings yet", "Wind readings appear once the station has reported for this period.")
        return
    speeds = [r["windspeedmph"] for r in rows if r.get("windspeedmph") is not None]
    gusts = [(ts, r["windgustmph"]) for ts, r in timed if r.get("windgustmph") is not None]
    latest = timed[-1][1]
    now_speed, now_dir = latest.get("windspeedmph"), latest.get("winddir")
    direction = wind_rose.NAMES[round(now_dir / 22.5) % 16] if now_dir is not None and (now_speed or 0) >= 1 else ""
    today_gust = max((g for t, g in gusts if t >= _start_of_today(s)), default=None)
    speed_text = units.format_value("windspeedmph", now_speed, metric, 0)
    number, _, unit_text = speed_text.partition(" ")
    gust_line = f"Gust {units.format_value('windgustmph', latest.get('windgustmph'), metric, 0)}" if latest.get("windgustmph") is not None else ""
    if today_gust is not None:
        gust_line += f" · today's top {units.format_value('windgustmph', today_gust, metric, 0)}"
    sky = f"{hero._clouds_svg(False)} center/cover no-repeat, {hero.sky_bg('clear_day', hero.GRADS['clear_day'])}"

    left, right = st.columns([1.15, 1], gap="medium")
    with left:
        st.markdown(f'<div class="wl-panel wl-bignum" style="min-height:150px"><div class="wl-hx-sky" style="position:absolute;'
                    f'inset:0 0 0 50%;background:{sky};-webkit-mask-image:linear-gradient(90deg,transparent,#000 55%);'
                    f'mask-image:linear-gradient(90deg,transparent,#000 55%);opacity:.8"></div>'
                    f'<div style="position:relative;z-index:1;display:flex;align-items:center;gap:22px">'
                    f'{line_icons.icon("wind", 70, "#7cc4ff", 1.6)}<i class="wl-div"></i><div><div class="wl-bn">{html.escape(number)}'
                    f'<small>{html.escape(unit_text)} {direction}</small></div><div class="wl-bd" style="font-size:20px">'
                    f'{html.escape(gust_line)}</div></div></div></div>', unsafe_allow_html=True)
        calm = sum(1 for v in speeds if v < wind_rose.CALM_MPH)
        top_gust = max(gusts, key=lambda x: x[1]) if gusts else None
        hours: dict = {}
        for ts, r in timed:
            if r.get("windspeedmph") is not None:
                hours.setdefault(int(ts // 3600), []).append(r["windspeedmph"])
        hourly = [units.convert("windspeedmph", sum(v) / len(v), metric) for _, v in sorted(hours.items())]
        prevailing = wind_rose.dominant(counts)
        deg = {n: i * 22.5 for i, n in enumerate(wind_rose.NAMES)}.get(prevailing)
        cards = [
            hero.metric_html(line_icons.icon("wind", 24, "#7cc4ff"), f"Average ({period.replace('Last ', '')})",
                             *units.format_value("windspeedmph", sum(speeds) / len(speeds), metric, 1).split(" ", 1), "",
                             sparks.spark_svg(hourly, "#38c6ec", h=30)),
            hero.metric_html(line_icons.icon("wind", 24, "#f6c445"), "Max gust",
                             *(units.format_value("windgustmph", top_gust[1], metric, 0).split(" ", 1) if top_gust else ("--", "")),
                             f"at {timefmt.time_text(datetime.fromtimestamp(top_gust[0], tz))}" if top_gust else "", ""),
            hero.metric_html(line_icons.icon("wind", 24, "#9db0c4"), f"Calms (under {'2 km/h' if metric else '1 mph'})",
                             f"{100 * calm / len(speeds):.1f}%" if speeds else "--", "", "share of readings", ""),
            hero.metric_html(line_icons.icon("pin", 24, "#7cc4ff"), "Prevailing direction", prevailing,
                             f"({deg:.0f}°)" if deg is not None else "", "most common", ""),
        ]
        st.markdown('<div class="wl-metrics" style="grid-template-columns:repeat(2,minmax(0,1fr))">' + "".join(cards) + "</div>",
                    unsafe_allow_html=True)
    with right, st.container(border=True):
        pct = wind_rose.percentages(counts, total)
        fig = charts.figure(dark, height=420)
        from weatherlab.screens.history import ROSE_BLUES_DARK, ROSE_BLUES_LIGHT  # the same blues as History's rose
        ramp = ["#2a8fb0", "#38c6ec", "#f6c445", "#f08a3c"] if dark else ROSE_BLUES_LIGHT
        for n, i in enumerate(wind_rose.DRAWN):
            fig.add_barpolar(r=pct[i], theta=wind_rose.NAMES, name=wind_rose.label(i, metric),
                             marker_color=ramp[n % len(ramp)], marker_line_width=0)
        fig.update_layout(title=dict(text=f"Wind rose · {period.lower()}", x=0, xanchor="left", font=dict(size=16)),
                          polar=dict(barmode="stack", angularaxis=dict(direction="clockwise", rotation=90),
                                     radialaxis=dict(ticksuffix="%")))
        charts.show(fig)
    with st.container(border=True):
        buckets: dict = {}
        for ts, r in timed:
            buckets.setdefault(int(ts // 3600), []).append(r)
        xs, sp, gu = [], [], []
        for hour, rs in sorted(buckets.items()):
            xs.append(datetime.fromtimestamp(hour * 3600, tz))
            v = [r["windspeedmph"] for r in rs if r.get("windspeedmph") is not None]
            g = [r["windgustmph"] for r in rs if r.get("windgustmph") is not None]
            sp.append(units.convert("windspeedmph", sum(v) / len(v), metric) if v else None)
            gu.append(units.convert("windgustmph", max(g), metric) if g else None)
        fig = charts.figure(dark, height=300)
        fig.add_trace(go.Scatter(x=xs, y=gu, name=f"Gust ({units.speed_unit(metric)})", mode="lines",
                                 line=dict(color="#f6c445", width=2), fill="tozeroy", fillcolor="rgba(246,196,69,.18)"))
        fig.add_trace(go.Scatter(x=xs, y=sp, name=f"Wind speed ({units.speed_unit(metric)})", mode="lines",
                                 line=dict(color="#38c6ec", width=2.2), fill="tozeroy", fillcolor="rgba(56,198,236,.15)"))
        fig.update_layout(title=dict(text="Hourly wind speed and gust", x=0, xanchor="left", font=dict(size=16)),
                          legend=dict(orientation="h", y=1.14, x=1, xanchor="right"))
        charts.show(fig)
    st.caption("Wedges show how often the wind came from each direction, coloured by speed. The hourly line is each hour's "
               "average speed and its strongest gust.")


UV_COLOURS = [(3, "#3ddc84"), (6, "#f6c445"), (8, "#f08a3c"), (11, "#ef5b4c"), (99, "#b06cff")]


def _uv_colour(uv: float) -> str:
    return next(c for limit, c in UV_COLOURS if uv < limit)


def _daylight_svg(progress, rise_text: str, set_text: str, length_text: str, now_text: str) -> str:
    """Today's daylight as an arch from sunrise to sunset, with the sun where it is now (when it's up)."""
    import math
    w, base, half, tall = 560, 170, 215, 135
    cx = w / 2

    def pt(t):
        return cx - half * math.cos(math.pi * t), base - tall * math.sin(math.pi * t)
    path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in (pt(i / 60) for i in range(61)))
    sun = ""
    if progress is not None:
        sx, sy = pt(min(max(progress, 0.0), 1.0))
        sun = (f'<text x="{sx:.1f}" y="{sy - 20:.1f}" text-anchor="middle" font-size="14" fill="#eaf2fb">{html.escape(now_text)}</text>'
               f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="13" fill="#f6c445" fill-opacity=".25"/>'
               f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="7" fill="#f6c445"/>')
    left, right = cx - half, cx + half
    return (f'<svg viewBox="0 0 {w} {base + 50}" width="100%" style="display:block;max-height:240px" aria-label="Daylight today">'
            '<defs><linearGradient id="wl-day" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f6c445" stop-opacity=".28"/>'
            '<stop offset="1" stop-color="#f6c445" stop-opacity="0"/></linearGradient></defs>'
            f'<path d="{path} Z" fill="url(#wl-day)"/>'
            f'<path d="{path}" fill="none" stroke="#f6c445" stroke-width="2.5"/>'
            f'<line x1="10" y1="{base}" x2="{w - 10}" y2="{base}" stroke="#9db0c4" stroke-opacity=".35"/>'
            f'<text x="{cx}" y="{base - 62}" text-anchor="middle" font-size="15" fill="#c9d6e6">Daylight duration</text>'
            f'<text x="{cx}" y="{base - 28}" text-anchor="middle" font-size="30" font-weight="800" fill="#eaf2fb">{html.escape(length_text)}</text>'
            f'<text x="{left}" y="{base + 22}" text-anchor="middle" font-size="13" fill="#c9d6e6">Sunrise</text>'
            f'<text x="{left}" y="{base + 42}" text-anchor="middle" font-size="16" font-weight="700" fill="#eaf2fb">{html.escape(rise_text)}</text>'
            f'<text x="{right}" y="{base + 22}" text-anchor="middle" font-size="13" fill="#c9d6e6">Sunset</text>'
            f'<text x="{right}" y="{base + 42}" text-anchor="middle" font-size="16" font-weight="700" fill="#eaf2fb">{html.escape(set_text)}</text>'
            f'{sun}</svg>')


def sun_page() -> None:
    """Sun (0.37.64, the redesign): the UV index now, today's daylight, sunshine and solar radiation, UV by hour and the
    time to sunburn."""
    s = load_settings()
    dark = theme.is_dark()
    tz = _tz(s)
    db = storage.connect()
    st.markdown(theme.page_head("Sun and UV", "Solar conditions, UV and daylight for your station."), unsafe_allow_html=True)
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
    uv_now = data.get("uv")
    solar_now = data.get("solarradiation")
    word = "" if uv_now is None else sun_uv.uv_word(uv_now).capitalize()
    sky_word, sky_note = (("Sunny", "Bright sunshine.") if (solar_now or 0) >= 500 else
                          ("Some sun", "Sunshine through some cloud.") if (solar_now or 0) >= 120 else
                          ("Dim", "Cloudy, or the sun is low.") if (solar_now or 0) > 5 else ("Dark", "The sun is down."))
    sky = f"{hero._clouds_svg(False)} center/cover no-repeat, {hero.sky_bg('dawn' if (solar_now or 0) < 200 else 'clear_day', hero.GRADS['clear_day'])}"
    st.markdown(f'<div class="wl-panel wl-bignum"><div class="wl-hx-sky" style="position:absolute;inset:0 0 0 45%;background:{sky};'
                f'-webkit-mask-image:linear-gradient(90deg,transparent,#000 50%);mask-image:linear-gradient(90deg,transparent,#000 50%);opacity:.85"></div>'
                f'<div style="position:relative;z-index:1;display:flex;align-items:center;gap:24px">'
                f'{line_icons.icon("sun", 78, "#f6c445", 1.6)}<i class="wl-div"></i>'
                f'<div><div class="wl-note">UV index</div><div class="wl-bn">{"--" if uv_now is None else f"{uv_now:.0f}"}</div>'
                f'<div style="font-size:18px">{html.escape(word)}</div></div><i class="wl-div"></i>'
                f'<div><div class="wl-bw" style="font-size:26px">{sky_word}</div><div class="wl-bd">{sky_note}</div></div></div></div>',
                unsafe_allow_html=True)

    left, right = st.columns([1.5, 1], gap="medium")
    o = None
    if s.latitude is not None and s.longitude is not None:
        o = astro.overview(s.latitude, s.longitude, tz, datetime.now(timezone.utc), days=1)
    with left:
        if o:
            arc = _daylight_svg(o["progress"], _local_time(o["sunrise"], tz), _local_time(o["sunset"], tz),
                                astro.length_text(o["length"], short=True), timefmt.time_text(datetime.now(tz)))
            st.markdown(f'<div class="wl-panel" style="padding:16px 20px"><div class="wl-ptitle">Today\'s daylight</div>{arc}</div>',
                        unsafe_allow_html=True)
        else:
            empty_card("Set your location in Settings, under Station to see today's daylight.")
    with right:
        hours = sun_uv.sunshine_hours(sun_today)
        possible = f"{min(100, 100 * hours * 3600 / o['length']):.0f}% of possible" if o and o.get("length") else ""
        peak_solar = max((v for _, v in sun_today if v is not None), default=None)
        st.markdown('<div class="wl-panel wl-kvp" style="margin-bottom:14px"><div class="wl-statrows" style="border:none;background:transparent;margin:0">'
                    f'<div>{line_icons.icon("sun", 34, "#f6c445")}<div><b>Sunshine today</b><span>{possible}</span></div>'
                    f'<span class="wl-big">{hours:.1f} h</span></div>'
                    f'<div>{line_icons.icon("gauge", 34, "#7cc4ff")}<div><b>Solar radiation</b><span>Today\'s max '
                    f'{"--" if peak_solar is None else f"{peak_solar:.0f} W/m²"}</span></div>'
                    f'<span class="wl-big">{"--" if solar_now is None else f"{solar_now:.0f}"}<span style="font-size:15px"> W/m²</span></span></div>'
                    f'<div>{line_icons.icon("clock", 34, "#9db0c4")}<div><b>Sunshine, last 7 days</b><span>hours of sun</span></div>'
                    f'<span class="wl-big">{sun_uv.sunshine_hours(sun_week):.0f} h</span></div></div></div>', unsafe_allow_html=True)

    chart_col, burn_col = st.columns([1.5, 1], gap="medium")
    with chart_col, st.container(border=True):
        hourly: dict = {}
        for ts, u in uv_today:
            if u is not None:
                hourly.setdefault(datetime.fromtimestamp(ts, tz).replace(minute=0, second=0, microsecond=0), []).append(u)
        xs = sorted(hourly)
        ys = [max(hourly[x]) for x in xs]
        lit = [i for i, v in enumerate(ys) if v > 0]  # only the daylight hours, with an hour either side
        if lit:
            lo, hi = max(lit[0] - 1, 0), min(lit[-1] + 2, len(xs))
            xs, ys = xs[lo:hi], ys[lo:hi]
        fig = charts.figure(dark, height=290)
        fig.add_trace(go.Bar(x=xs, y=ys, marker_color=[_uv_colour(v) for v in ys], text=[f"{v:.0f}" for v in ys],
                             textposition="outside", cliponaxis=False, name="UV"))
        if xs and uv_now is not None:
            fig.add_annotation(x=xs[-1], y=ys[-1], text=f"Now: UV {uv_now:.0f}", showarrow=True, arrowhead=2, ay=-38,
                               bgcolor="rgba(0,0,0,.4)", bordercolor="#f6c445", font=dict(color="#f6c445"))
        fig.update_layout(title=dict(text="UV by hour, today", x=0, xanchor="left", font=dict(size=16)), showlegend=False)
        fig.update_yaxes(rangemode="tozero")
        charts.show(fig)
    with burn_col:
        fair = sun_uv.burn_minutes(uv_now, "Type II (burns easily)")
        big = "--" if fair is None else f"~{fair:.0f} minutes"
        note = (f"Approximate time for fair skin to begin to burn at the current UV index ({uv_now:.0f})." if fair is not None
                else "No sunburn risk while the UV index is 0.")
        st.markdown(f'<div class="wl-panel" style="padding:18px 22px;margin-bottom:10px"><div style="display:flex;gap:12px;align-items:center;'
                    f'font-size:17px;font-weight:700">{line_icons.icon("alert", 28, "#f6c445")}Estimated sunburn time</div>'
                    f'<div style="font-size:34px;font-weight:800;text-align:center;margin:14px 0 6px">{big}</div>'
                    f'<div class="wl-note" style="text-align:center">{html.escape(note)}</div></div>', unsafe_allow_html=True)
        with st.expander("Every skin type"):
            theme.table([{"Skin type": k, "Minutes until sunburn": "--" if m is None else f"{m:.0f}"}
                         for k in sun_uv.MED_J_M2 for m in [sun_uv.burn_minutes(uv_now, k)]])
    page = st.session_state.get("wl_pages", {}).get("Sun and sky")
    if page is not None:
        st.page_link(page, label="Moon phase, moonrise and tonight's sky: go to Astronomy", icon=":material/dark_mode:",
                     query_params={"tab": "Astronomy"})
    st.caption("Estimates from the station's UV reading. They assume full sun with no shade and no sunscreen.")


# ---------------------------------------------------------------- Astronomy
def _local_time(dt, tz) -> str:
    return "--" if dt is None else timefmt.time_text(dt.astimezone(tz))


def astronomy_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.page_head("Astronomy", "The sun and moon for your location: sunrise, sunset, golden hour, twilight, moonrise, moonset and phases."), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        empty_card("Set your location in Settings, under Station to see sunrise, sunset and the moon.")
        return

    now = datetime.now(timezone.utc)
    o = astro.overview(s.latitude, s.longitude, tz, now, days=14)
    moon = o["moon"]
    rise_text, set_text = _local_time(o["sunrise"], tz), _local_time(o["sunset"], tz)

    sun_col, moon_col = st.columns(2)
    with sun_col:
        st.markdown(theme.section_html("Sun today"), unsafe_allow_html=True)
        st.markdown(astro_art.sun_arc_svg(o["progress"], rise_text, set_text), unsafe_allow_html=True)
        change = astro.change_text(o["change"])
        st.markdown(f"**{astro.length_text(o['length'])}** of daylight" + (f", {change}" if change else ""))
    with moon_col:
        st.markdown(theme.section_html("Moon"), unsafe_allow_html=True)
        st.markdown(f'<div style="display:flex;gap:14px;align-items:center">{astro_art.moon_svg(moon["illumination"], moon["waxing"])}'
                    f'<div><div style="font-size:1.15rem;font-weight:600">{html.escape(moon["name"])}</div>'
                    f'<div style="opacity:.7">{moon["illumination"]:.0f}% lit, day {moon["age"]:.0f} of 29</div></div></div>',
                    unsafe_allow_html=True)
        st.markdown(f"Moonrise {_local_time(moon['rise'], tz)}, moonset {_local_time(moon['set'], tz)}")

    st.markdown(theme.grid_html([
        _tile("Sunrise", rise_text),
        _tile("Sunset", set_text),
        _tile("Day length", astro.length_text(o["length"], short=True)),
        _tile("Solar noon", _local_time(o["noon"], tz), f"Sun {o['noon_altitude']:.0f}° up"),
        _tile("Golden hour", _local_time(o["golden_hour"], tz), "Evening light starts"),
        _tile("Twilight ends", _local_time(o["twilight_end"], tz), "Properly dark after"),
        _tile("Next new moon", f"{moon['next_new']:%b} {moon['next_new'].day}"),
        _tile("Next full moon", f"{moon['next_full']:%b} {moon['next_full'].day}"),
    ]), unsafe_allow_html=True)

    st.markdown(theme.section_html("Next 14 days"), unsafe_allow_html=True)
    theme.table([{"Date": f"{d['date']:%a} {d['date']:%b} {d['date'].day}", "Sunrise": _local_time(d["sunrise"], tz),
                  "Sunset": _local_time(d["sunset"], tz), "Daylight": astro.length_text(d["length"]),
                  "Moon": d["moon"]} for d in o["days"]])
    st.caption(f"Times are in {s.timezone}. Sun times use the standard NOAA method, accurate to about a minute. "
               "Moonrise and moonset are estimates, good to a few minutes. Moon phase dates can be off by about a day.")


# ---------------------------------------------------------------- Wind map
def _band_label(i: int, metric: bool) -> str:
    return windmap.band_label(i, metric)


def _wind_grid_html(frame: list, plate: str = "#dfe7ef") -> str:
    """The arrows as one block of HTML: a grid of points with the station in the middle."""
    cells = "".join(f'<div style="display:flex;align-items:center;justify-content:center">'
                    f'{windmap.arrow_html(speed, direction)}</div>' for speed, direction in frame)
    marker = ('<div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:16px;height:16px;'
              'border-radius:50%;background:#1c2330;border:3px solid #fff;box-shadow:0 0 0 2px #1c2330"></div>')
    return (f'<div role="img" aria-label="Wind map: arrows show where the wind goes, colour shows the speed" '
            f'style="position:relative;width:100%;max-width:820px;margin:0 auto;aspect-ratio:7 / 5;'
            f'background:{plate};border:1px solid #c9d1db;border-radius:14px;overflow:hidden">'
            f'<div style="position:absolute;inset:10px;display:grid;grid-template-columns:repeat({windmap.COLS},'
            f'minmax(0,1fr));grid-template-rows:repeat({windmap.ROWS},minmax(0,1fr))">{cells}</div>'
            f'{marker}</div>')


def _wind_summary(frame: list, metric: bool, choice: str) -> None:
    """The station's own wind now, and the strongest wind in the area for the chosen time."""
    latest = storage.latest(storage.connect())
    reading = latest[1] if latest else {}

    def shown(speed: float) -> str:
        return f"{units.convert('windspeedmph', speed, metric):.0f}{units.suffix('windspeedmph', metric)}"

    speed, gust, direction = reading.get("windspeedmph"), reading.get("windgustmph"), reading.get("winddir")
    usable = [(sp, d) for sp, d in frame if sp is not None]
    top = max(usable, key=lambda p: p[0]) if usable else None
    st.markdown(theme.section_html("Your station", "now" if choice == "Now" else choice.lower()), unsafe_allow_html=True)
    if speed is None:
        st.markdown("No wind reading from the station yet.")
    else:
        from_dir = nws.compass(direction)
        st.markdown(f"**{shown(speed)}**" + (f" from the {from_dir}" if from_dir else ""))
    details = []
    if gust is not None:
        details.append(f"Gusts {shown(gust)}")
    if top is not None:
        top_dir = nws.compass(top[1])
        details.append(f"Strongest in the area {shown(top[0])}" + (f", from the {top_dir}" if top_dir else ""))
    if details:
        st.caption(". ".join(details) + ".")


def wind_map_page() -> None:
    """Wind across the area around the station, now and later, as arrows coloured by speed."""
    s = load_settings()
    metric = units.is_metric(s.units)
    st.markdown(theme.page_head("Wind map", "Wind across the area around the station, now and later, as arrows coloured by speed."), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        empty_card("Set your location first", "The wind map is centred on your latitude and longitude, in Settings, under Station.")
        return
    choice = st.segmented_control("Time", list(windmap.TIMES), default="Now", key="windmap_time",
                                  label_visibility="collapsed") or "Now"
    try:
        grid = windmap.load(s.latitude, s.longitude, time.time(), _tz(s))
    except windmap.WindError as exc:
        empty_card("The wind map isn't available right now", str(exc))
        return
    frame = grid["frames"].get(str(windmap.TIMES[choice]), [])
    if not frame:
        empty_card("No wind forecast for that time yet")
        return
    st.markdown(_wind_grid_html(frame), unsafe_allow_html=True)
    keys = "".join(f'<span style="display:inline-flex;align-items:center;gap:6px;margin:4px 14px 4px 0">'
                   f'<span style="display:inline-block;width:18px;height:11px;border-radius:3px;background:{colour};'
                   f'border:1px solid #1b4f7a"></span>{_band_label(i, metric)}</span>'
                   for i, (_, colour, _) in enumerate(windmap.BANDS))
    st.markdown(f'<div style="font-size:14px;margin-top:10px">Speed ({units.unit("windspeedmph", metric)}): {keys}</div>',
                unsafe_allow_html=True)
    _wind_summary(frame, metric, choice)
    st.caption("Each arrow points the way the wind blows. Colour shows the speed. The middle point is your station. "
               "Data from Open-Meteo, saved for an hour.")
