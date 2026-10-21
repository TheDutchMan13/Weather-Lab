"""The Forecast page's overview and 7-day views, drawn to match the design the owner made.

Both views read the forecast the page already downloads from the National Weather Service, so nothing new is fetched.
The overview shows every second hour for the next 24 hours. Rain streaks fall over the hours with a rain chance of 40%
or more, and they stop when the device asks for less motion.
"""

import html
import re
from datetime import datetime, timedelta, timezone

from weatherlab import astro, wx_icons

STYLE = """<style>
.wl-fc{box-sizing:border-box;background:#202c40;color:#e9eef6;border-radius:16px;padding:20px;margin:12px 0;font-family:system-ui,sans-serif;overflow-x:auto}
.wl-fc *{box-sizing:border-box}
.wl-fc-head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:10px}
.wl-fc-title{font-size:16px;font-weight:700}
.wl-fc-cap{font-size:12px;color:#98a6bd}
.wl-fc-inner{min-width:720px}
.wl-fc-inner-days{min-width:760px}
.wl-fc-chart{position:relative;height:260px;margin-top:4px}
.wl-fc-drops{position:absolute;left:0;right:0;top:0;bottom:0;overflow:hidden;pointer-events:none}
.wl-fc-drop{position:absolute;top:-16px;width:1.5px;border-radius:2px;background:linear-gradient(to bottom,rgba(150,205,255,0),rgba(175,220,255,.95));animation-name:wl-fc-fall;animation-timing-function:linear;animation-iteration-count:infinite}
@keyframes wl-fc-fall{0%{transform:translateY(0);opacity:0}10%{opacity:1}85%{opacity:.85}100%{transform:translateY(300px);opacity:0}}
@media (prefers-reduced-motion: reduce){.wl-fc-drop{animation:none;opacity:.35}}
.wl-fc-sun{position:absolute;bottom:6px;font-size:12px;color:#cfe0f2;white-space:nowrap}
.wl-fc-pill{height:26px;border-radius:8px;background:#2b5f98;color:#e6f1ff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center}
.wl-fc-foot{display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;font-size:12px;color:#c9d4e4;border-top:1px solid #33425a;padding-top:12px;margin-top:8px}
.wl-fc-day{display:grid;grid-template-columns:90px minmax(170px,1.2fr) 70px 56px minmax(160px,2fr) 56px 150px;gap:12px;align-items:center;padding:12px 0;border-top:1px solid #33425a;font-size:15px}
.wl-fc-track{position:relative;height:6px;background:#2c3a50;border-radius:99px}
.wl-fc-bar{position:absolute;top:0;bottom:0;border-radius:99px;background:linear-gradient(90deg,#4aa3e6,#f5c04a,#f08a3c)}
</style>"""

DEGREE = "°"


def to_shown(value, unit, metric):
    """A temperature in the user's units, rounded to a whole number. None when there is no value."""
    if value is None:
        return None
    if unit == "F" and metric:
        return round((value - 32) * 5 / 9)
    if unit == "C" and not metric:
        return round(value * 9 / 5 + 32)
    return round(value)


def degree_sign(metric):
    return "°C" if metric else "°F"


def wind_text(text, metric):
    """NWS wind wording such as '5 to 15 mph', in km/h when the user chose metric."""
    text = str(text or "")
    if not metric or "mph" not in text:
        return text
    text = re.sub(r"\d+(?:\.\d+)?", lambda m: str(round(float(m.group(0)) * 1.609344)), text)
    return text.replace("mph", "km/h")


def clock(t):
    return f"{t.hour % 12 or 12}:{t.minute:02d} {'AM' if t.hour < 12 else 'PM'}"


def hour_label(t, first):
    if first:
        return "Now"
    return f"{t.hour % 12 or 12} {'AM' if t.hour < 12 else 'PM'}"


def _when(period, tz):
    return datetime.fromisoformat(period["start"]).astimezone(tz)


def _night(when, lat, lon, tz):
    """True when the sun is down at this time. Places where the sun doesn't set that day count as day."""
    if lat is None or lon is None:
        return False
    rise, set_ = astro.sun_times(lat, lon, when.date())
    if rise is None or set_ is None:
        return False
    return when < rise.astimezone(tz) or when > set_.astimezone(tz)


def _sun_events(first, last, lat, lon, tz):
    """(local time, "Sunrise" or "Sunset") for each sun event between two local times."""
    if lat is None or lon is None:
        return []
    out = []
    day = first.date()
    while day <= last.date():
        rise, set_ = astro.sun_times(lat, lon, day)
        for label, t in (("Sunrise", rise), ("Sunset", set_)):
            if t is not None:
                local = t.astimezone(tz)
                if first <= local <= last:
                    out.append((local, label))
        day += timedelta(days=1)
    return out


def overview_hours(hourly, lat, lon, tz, now, count=12, step=2):
    """Every second hour from the current hour, for 24 hours: the columns the overview shows."""
    first = now.replace(minute=0, second=0, microsecond=0)
    upcoming = []
    for h in hourly:
        if not h.get("start"):
            continue
        when = _when(h, tz)
        if when >= first:
            upcoming.append({"when": when, "temp": h.get("temperature"), "unit": h.get("unit") or "F",
                             "short": h.get("short") or "", "pop": h.get("pop")})
    picks = upcoming[::step][:count]
    for p in picks:
        p["night"] = _night(p["when"], lat, lon, tz)
    return picks


def days(periods, tz, today, count=7):
    """Each calendar day: its high from the daytime period and its low from the night period."""
    by_day = {}
    for p in periods:
        if not p.get("start"):
            continue
        when = _when(p, tz)
        row = by_day.setdefault(when.date(), {"date": when.date(), "high": None, "low": None, "unit": "F",
                                              "pop": None, "short": None, "wind": "", "night_only": True})
        row["unit"] = p.get("unit") or row["unit"]
        if p.get("pop") is not None:
            row["pop"] = p["pop"] if row["pop"] is None else max(row["pop"], p["pop"])
        if p.get("isDaytime"):
            row["high"] = p.get("temperature")
            row["short"] = p.get("short") or row["short"]
            row["wind"] = p.get("wind") or row["wind"]
            row["night_only"] = False
        else:
            row["low"] = p.get("temperature")
            if row["short"] is None:
                row["short"] = p.get("short") or ""
                row["wind"] = row["wind"] or p.get("wind") or ""
    rows = [by_day[d] for d in sorted(by_day)][:count]
    for row in rows:
        row["name"] = "Today" if row["date"] == today else row["date"].strftime("%a")
        row["short"] = row["short"] or ""
    return rows


def overview_html(hourly, lat, lon, tz, metric, alert_count, now):
    """The next 24 hours as one card: sky, temperature curve, rain chance, sun times and the moon."""
    picks = overview_hours(hourly, lat, lon, tz, now)
    if not picks:
        return ""
    n = len(picks)
    shown = [to_shown(p["temp"], p["unit"], metric) for p in picks]
    known = [v for v in shown if v is not None]
    hi, lo = (max(known), min(known)) if known else (1, 0)
    span = max(hi - lo, 1)
    width, height, top, bottom = 1100, 260, 20, 192.5
    col = width / n

    def y_of(v):
        return top + (hi - v) / span * (bottom - top)

    shading = [f'<rect x="{i * col:.1f}" y="0" width="{col:.1f}" height="{height}" fill="#2a4f73" fill-opacity=".55"/>'
               for i, p in enumerate(picks) if p["night"]]
    grid, labels = [], []
    for k in range(4):
        v = hi - span * k / 3
        yy = y_of(v)
        grid.append(f'<line x1="0" x2="{width}" y1="{yy:.1f}" y2="{yy:.1f}"/>')
        labels.append(f'<span style="position:absolute;left:0;top:{yy / height * 100:.2f}%;transform:translateY(-50%);'
                      f'font-size:11px;color:#98a6bd">{round(v)}{DEGREE}</span>')

    pts = [((i + 0.5) * col, y_of(v)) for i, v in enumerate(shown) if v is not None]
    line = " ".join(("M" if k == 0 else "L") + f"{x:.1f},{y:.1f}" for k, (x, y) in enumerate(pts))
    area = (line + f" L{pts[-1][0]:.1f},{height} L{pts[0][0]:.1f},{height} Z") if pts else ""
    curve = ""
    if pts:
        curve = (f'<path d="{area}" fill="url(#wl-fc-fill)"/>'
                 f'<path d="{line}" fill="none" stroke="#f0f4fa" stroke-width="2.2" vector-effect="non-scaling-stroke"/>')
    svg = (f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true" '
           f'style="position:absolute;inset:0;width:100%;height:100%">'
           f'<defs><linearGradient id="wl-fc-fill" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="#d0604f" stop-opacity=".75"/>'
           f'<stop offset=".55" stop-color="#b9785a" stop-opacity=".35"/>'
           f'<stop offset="1" stop-color="#d9c9a0" stop-opacity="0"/></linearGradient></defs>'
           + "".join(shading)
           + f'<g stroke="#55647c" stroke-dasharray="3 5" stroke-width="1">{"".join(grid)}</g>'
           + curve + '</svg>')

    rain_cols = [i for i, p in enumerate(picks) if (p["pop"] or 0) >= 40]
    drops = []
    for k in range(18 if rain_cols else 0):
        i = rain_cols[k % len(rain_cols)]
        left = (i + (k * 37 % 100) / 100) / n * 100
        drops.append(f'<span class="wl-fc-drop" style="left:{left:.2f}%;height:{9 + k * 5 % 7}px;'
                     f'animation-duration:{1.1 + (k * 3 % 8) / 10:.1f}s;animation-delay:-{(k * 7 % 16) / 10:.1f}s"></span>')

    start = picks[0]["when"]
    end = start + timedelta(hours=2 * n)
    suns = []
    for when, label in _sun_events(start, end, lat, lon, tz):
        frac = (when - start).total_seconds() / (end - start).total_seconds()
        suns.append(f'<span class="wl-fc-sun" style="left:{frac * 100:.2f}%">{label} {clock(when)}</span>')
    chart = (f'<div class="wl-fc-chart">{svg}{"".join(labels)}'
             f'<div class="wl-fc-drops">{"".join(drops)}</div>{"".join(suns)}</div>')

    cols = f"display:grid;grid-template-columns:repeat({n},minmax(0,1fr));text-align:center"
    time_cells = "".join(f'<div style="font-size:12px;color:#c9d4e4;{"font-weight:700" if i == 0 else ""}">'
                         f'{html.escape(hour_label(p["when"], i == 0))}</div>' for i, p in enumerate(picks))
    icon_cells = "".join(f'<div style="display:flex;justify-content:center;margin:4px 0">'
                         f'{wx_icons.forecast_icon(p["short"], p["night"], 26)}</div>' for p in picks)
    temp_cells = "".join(f'<div style="font-size:14px;font-weight:700">'
                         f'{"--" if t is None else str(t) + DEGREE}</div>' for t in shown)
    pill_cells = "".join(f'<div class="wl-fc-pill">{"–" if p["pop"] is None else str(round(p["pop"])) + "%"}</div>'
                         for p in picks)
    alert = ""
    if alert_count:
        alert = ('<div style="margin-top:8px;height:26px;border-radius:8px;background:#6a3b25;color:#ffd9bd;'
                 'font-size:12px;font-weight:600;display:flex;align-items:center;padding-left:10px">'
                 f'Severe weather alerts: {alert_count}. Details are above.</div>')
    moon = astro.moon_phase(datetime.now(timezone.utc))
    foot = ('<div class="wl-fc-foot"><span><span style="display:inline-block;width:10px;height:10px;border-radius:50%;'
            'background:linear-gradient(90deg,#4aa3e6,#f5c04a,#f08a3c);margin-right:6px"></span>Temperature</span>'
            f'<span>Severe weather alerts: {alert_count}</span>'
            f'<span>Moon phase: <strong style="color:#e9eef6">{html.escape(moon["name"])}</strong></span></div>')
    return ('<section class="wl-fc"><div class="wl-fc-head"><span class="wl-fc-title">Overview</span>'
            f'<span class="wl-fc-cap">Next 24 hours, every 2 hours · {degree_sign(metric)}</span></div>'
            '<div class="wl-fc-inner">'
            f'<div style="{cols}">{time_cells}</div>'
            f'<div style="{cols}">{icon_cells}</div>'
            f'<div style="{cols}">{temp_cells}</div>'
            f'{chart}'
            f'<div style="{cols};margin-top:10px;gap:6px">{pill_cells}</div>'
            f'{alert}</div>{foot}</section>')


def days_html(periods, tz, metric, today, count=7):
    """The next seven days as rows, each with its rain chance and a bar for its temperature range."""
    rows = days(periods, tz, today, count)
    if not rows:
        return ""
    highs = [to_shown(r["high"], r["unit"], metric) for r in rows]
    lows = [to_shown(r["low"], r["unit"], metric) for r in rows]
    known = [v for v in highs + lows if v is not None]
    lo, hi = (min(known), max(known)) if known else (0, 1)
    span = max(hi - lo, 1)
    out = []
    for r, high, low in zip(rows, highs, lows):
        bar = ""
        if high is not None and low is not None:
            left = (low - lo) / span * 100
            width = max((high - low) / span * 100, 4)
            bar = f'<div class="wl-fc-bar" style="left:{left:.1f}%;width:{width:.1f}%"></div>'
        icon = wx_icons.forecast_icon(r["short"], r["night_only"], 26)
        pop = "–" if r["pop"] is None else str(round(r["pop"])) + "%"
        low_text = "--" if low is None else str(low) + DEGREE
        high_text = "--" if high is None else str(high) + DEGREE
        out.append(f'<div class="wl-fc-day"><div style="font-weight:700">{html.escape(r["name"])}</div>'
                   f'<div style="display:flex;align-items:center;gap:8px">{icon}<span>{html.escape(r["short"])}</span></div>'
                   f'<div style="color:#8fc8ff">{pop}</div>'
                   f'<div style="color:#98a6bd;text-align:right">{low_text}</div>'
                   f'<div class="wl-fc-track">{bar}</div>'
                   f'<div style="font-weight:700;text-align:right">{high_text}</div>'
                   f'<div style="color:#c9d4e4;font-size:13px">{html.escape(wind_text(r["wind"], metric))}</div></div>')
    return ('<section class="wl-fc"><div class="wl-fc-head"><span class="wl-fc-title">Next 7 days</span>'
            '<span class="wl-fc-cap">Rain chance is the higher of day and night</span></div>'
            '<div class="wl-fc-inner wl-fc-inner-days">' + "".join(out) + '</div></section>')
