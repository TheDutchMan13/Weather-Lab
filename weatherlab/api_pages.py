"""The data behind the Android app's pages: rankings, rain, wind, lightning, sun and UV, heat safety, station health,
What's New and the forecast. Read-only, in the units chosen in Settings. api.py routes to these."""

import calendar
import json
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from weatherlab import (astro, gateway_sensors, health, heat_safety, history, lightning_history, nws, rain_events,
                        storage, sun_uv, units, whats_new, wind_rose, yearly)

FORECAST_CACHE_SECONDS = 900
_forecast_cache: dict = {}

RANKS = [  # (label, summary key, "max" or "min", units key or None, unit text, digits)
    ("Warmest days", "tempf_max", "max", "tempf", "", 0),
    ("Coolest days", "tempf_max", "min", "tempf", "", 0),
    ("Coldest nights", "tempf_min", "min", "tempf", "", 0),
    ("Wettest days", "rain_in", "max", "dailyrainin", "", 2),
    ("Windiest days", "gust_max", "max", "windgustmph", "", 0),
    ("Highest UV", "uvi", "max", None, "UV", 1),
    ("Sunniest days", "sun_hours", "max", None, "h", 1),
]


def _tz(s) -> ZoneInfo:
    try:
        return ZoneInfo(s.timezone)
    except Exception:
        return ZoneInfo("UTC")


def _show(key, value, metric, digits=1):
    if value is None:
        return None
    return round(units.convert(key, value, metric) if key else value, digits)


def _midnight(now: float, tz) -> float:
    return datetime.fromtimestamp(now, tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


# ------------------------------------------------------------------ rankings

def rankings(db, s, now: float) -> dict:
    metric = units.is_metric(s.units)
    days = history.all_daily(db)
    out = []
    for label, key, kind, ukey, text, digits in RANKS:
        top = yearly.ranking(days, key, kind, 10)
        if not top:
            continue
        out.append({"label": label, "unit": units.unit(ukey, metric) if ukey else text,
                    "items": [{"date": d.isoformat(), "value": _show(ukey, v, metric, digits)} for d, v in top]})
    return {"rankings": out, "metric": metric}


# ------------------------------------------------------------------ rain

def rain_calendar(db, s, now: float, month: str) -> dict:
    """One month of daily rain, plus the totals for every year."""
    metric = units.is_metric(s.units)
    try:
        first = datetime.strptime(month, "%Y-%m").date()
    except ValueError:
        return {"error": "Use a month like 2026-10."}
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    held = {d: data.get("rain_in") for d, data in history.daily_between(db, first, last)}
    latest = storage.latest(db)
    today = datetime.fromtimestamp(now, _tz(s)).date()
    if latest and first <= today <= last and latest[1].get("dailyrainin") is not None:
        held[today] = latest[1]["dailyrainin"]
    days = []
    for n in range(last.day):
        d = first + timedelta(days=n)
        days.append({"date": d.isoformat(), "rain": _show("dailyrainin", held.get(d), metric, 2)})
    values = [v for v in held.values() if v is not None]
    years, rainy = {}, {}
    for d, data in history.all_daily(db):
        v = data.get("rain_in")
        if v is None:
            continue
        years[d.year] = years.get(d.year, 0.0) + v
        if v >= 0.01:
            rainy[d.year] = rainy.get(d.year, 0) + 1
    return {"month": month, "days": days, "total": _show("dailyrainin", sum(values), metric, 2),
            "rainy_days": sum(1 for v in values if v >= 0.01), "unit": units.unit("dailyrainin", metric),
            "years": [{"year": y, "total": _show("dailyrainin", years[y], metric, 2), "rainy_days": rainy.get(y, 0)}
                      for y in sorted(years, reverse=True)],
            "metric": metric}


def rain_event_list(db, s, now: float) -> dict:
    """Wet spells in the last 60 days, newest first. Readings are looked at every 5 minutes."""
    metric = units.is_metric(s.units)
    rows = storage.readings_sampled(db, now - 60 * 86400, now + 1, every_s=300)
    found = [e for e in rain_events.events(rows) if e["inches"] > 0]
    found.sort(key=lambda e: e["start"], reverse=True)
    return {"events": [{"start": e["start"], "end": e["end"], "minutes": max(1, round((e["end"] - e["start"]) / 60)),
                        "rain": _show("dailyrainin", e["inches"], metric, 2),
                        "peak_rate": _show("rainratein", e["peak_rate"], metric, 2)} for e in found[:25]],
            "rain_unit": units.unit("dailyrainin", metric), "rate_unit": units.unit("rainratein", metric), "metric": metric}


# ------------------------------------------------------------------ wind and lightning

def wind_rose_data(db, s, now: float, days: int) -> dict:
    metric = units.is_metric(s.units)
    items = storage.readings_sampled(db, now - days * 86400, now + 1, every_s=120 if days == 1 else 600)
    rows = [r for _, r in items]
    counts, total = wind_rose.rose(rows)
    pct = wind_rose.percentages(counts, total)
    speeds = [r["windspeedmph"] for r in rows if r.get("windspeedmph") is not None]
    gusts = [r["windgustmph"] for r in rows if r.get("windgustmph") is not None]
    return {"days": days, "total": total, "dominant": wind_rose.dominant(counts) if total else None,
            "bins": [wind_rose.label(i, metric) for i in range(len(wind_rose.SPEED_BINS))],
            "directions": [{"name": name, "bins": [pct[b][i] for b in range(len(wind_rose.SPEED_BINS))],
                            "percent": round(sum(pct[b][i] for b in range(len(wind_rose.SPEED_BINS))), 1)}
                           for i, name in enumerate(wind_rose.NAMES)],
            "average": _show("windspeedmph", sum(speeds) / len(speeds), metric) if speeds else None,
            "strongest_gust": _show("windgustmph", max(gusts), metric) if gusts else None,
            "unit": units.unit("windspeedmph", metric), "metric": metric}


def lightning_days(db, s, now: float) -> dict:
    metric = units.is_metric(s.units)
    strikes = storage.strikes_between(db, now - 30 * 86400, now + 1)
    rows = lightning_history.per_day(strikes, _tz(s))
    return {"days": [{"date": d.isoformat(), "strikes": n, "closest": _show("miles", miles, metric, 1)}
                     for d, n, miles in reversed(rows)],
            "unit": units.unit("miles", metric), "metric": metric}


# ------------------------------------------------------------------ sun, heat, station

def sun(db, s, now: float) -> dict:
    tz = _tz(s)
    metric = units.is_metric(s.units)
    latest = storage.latest(db)
    week = storage.readings_between(db, now - 7 * 86400, now + 1)
    start = _midnight(now, tz)
    today = [(ts, r) for ts, r in week if ts >= start]
    uv_now = latest[1].get("uv") if latest else None
    peaks = [r["uv"] for _, r in today if r.get("uv") is not None]
    uv_peak = max(peaks) if peaks else None
    rise = set_ = None
    if s.latitude is not None and s.longitude is not None:
        r, st = astro.sun_times(s.latitude, s.longitude, datetime.fromtimestamp(now, tz).date())
        rise = r.astimezone(tz).strftime("%H:%M") if r else None
        set_ = st.astimezone(tz).strftime("%H:%M") if st else None

    def burn(uvi):
        return [{"skin": k, "minutes": None if sun_uv.burn_minutes(uvi, k) is None else round(sun_uv.burn_minutes(uvi, k))}
                for k in sun_uv.MED_J_M2]
    return {"uv_now": None if uv_now is None else round(uv_now, 1), "uv_now_word": None if uv_now is None else sun_uv.uv_word(uv_now),
            "uv_peak": None if uv_peak is None else round(uv_peak, 1),
            "uv_peak_word": None if uv_peak is None else sun_uv.uv_word(uv_peak),
            "sunshine_today_hours": round(sun_uv.sunshine_hours([(ts, r.get("solarradiation")) for ts, r in today]), 1),
            "sunshine_week_hours": round(sun_uv.sunshine_hours([(ts, r.get("solarradiation")) for ts, r in week]), 1),
            "sunrise": rise, "sunset": set_, "burn_now": burn(uv_now), "burn_peak": burn(uv_peak), "metric": metric}


def heat(db, s, now: float) -> dict:
    tz = _tz(s)
    metric = units.is_metric(s.units)
    latest = storage.latest(db)
    data = latest[1] if latest else {}
    status = heat_safety.status(data.get("tempf"), data.get("humidity"))
    today = storage.readings_between(db, _midnight(now, tz), now + 1)
    series = [(ts, heat_safety.heat_index(r.get("tempf"), r.get("humidity"))) for ts, r in today]
    series = [(ts, hi) for ts, hi in series if hi is not None]
    peak = max(series, key=lambda x: x[1], default=None)
    year = datetime.fromtimestamp(now, tz).year
    highs = [d.get("tempf_max") for day, d in history.all_daily(db) if day.year == year and d.get("tempf_max") is not None]
    return {"heat_index": _show("heat_index", status["heat_index"], metric, 0), "level": status["level"],
            "advice": status["advice"], "temp": _show("tempf", data.get("tempf"), metric, 0),
            "peak_today": _show("heat_index", peak[1], metric, 0) if peak else None,
            "peak_time": datetime.fromtimestamp(peak[0], tz).strftime("%H:%M") if peak else None,
            "days_100": sum(1 for h in highs if h >= 100), "days_105": sum(1 for h in highs if h >= 105),
            "days_110": sum(1 for h in highs if h >= 110), "year": year,
            "levels": [{"level": name, "from": _show("heat_index", low, metric, 0) if low > -900 else None, "advice": advice}
                       for low, name, advice in reversed(heat_safety.LEVELS)],
            "unit": units.unit("heat_index", metric), "metric": metric}


def station(db, s, now: float) -> dict:
    tz = _tz(s)
    rows = health.window(db, now - 24 * 3600, now)
    latest = storage.latest(db)
    state, text = health.age_status(latest[0] if latest else None, now)
    gaps = health.gaps(rows)
    out_gaps = [{"start": a, "end": b, "minutes": round((b - a) / 60)} for a, b in gaps[-5:]]
    sensors = [{"label": x["label"], "present_percent": x["present_pct"],
                "age_seconds": None if x["last_seen"] is None else int(now - x["last_seen"])}
               for x in health.sensors(rows)]
    radios, warnings = None, []
    if s.station_ip.strip():
        try:
            raw = gateway_sensors.read(s.station_ip.strip())
            radios = []
            for r in raw:
                _, batt = gateway_sensors.battery_state(r.get("batt"))
                bstate, _ = gateway_sensors.battery_state(r.get("batt"))
                sstate, signal = gateway_sensors.signal_state(r.get("signal"), r.get("rssi"))
                radios.append({"name": r["name"], "battery": batt or "unknown", "battery_state": bstate,
                               "signal": signal or "unknown", "signal_state": sstate})
            warnings = gateway_sensors.warnings(raw)
        except Exception:
            radios = None
    return {"status": state, "status_text": text, "completeness_percent": health.completeness(rows, 24),
            "gap_count": len(gaps), "longest_gap_minutes": round(max(((b - a) for a, b in gaps), default=0) / 60),
            "gaps": out_gaps, "sensors": sensors, "radios": radios, "warnings": warnings,
            "readings_24h": len(rows)}


# ------------------------------------------------------------------ What's New and the forecast

def whats_new_list(db, s, now: float) -> dict:
    return {"entries": [{"version": e["version"], "date": e["date"], "items": list(e["items"])} for e in whats_new.ENTRIES]}


def _temp(value, unit, metric):
    if value is None:
        return None
    f = value if unit == "F" else value * 9 / 5 + 32
    return round(units.convert("tempf", f, metric))


def forecast(db, s, now: float) -> dict:
    """The National Weather Service forecast for the station's location, kept for 15 minutes."""
    if s.latitude is None or s.longitude is None:
        return {"available": False, "reason": "Set the station's latitude and longitude in Weather Lab's Setup page."}
    metric = units.is_metric(s.units)
    key = (s.latitude, s.longitude, metric)
    held = _forecast_cache.get(key)
    if held and now - held[0] < FORECAST_CACHE_SECONDS:
        return held[1]
    try:
        pts = nws.points(s.latitude, s.longitude, s.nws_contact)
        daily = nws.forecast_daily(pts["forecast"], s.nws_contact)
        hourly = nws.forecast_hourly(pts["forecastHourly"], s.nws_contact, 24) if pts.get("forecastHourly") else []
        try:
            alert_list = nws.alerts(s.latitude, s.longitude, s.nws_contact)
        except Exception:
            alert_list = []
    except Exception as exc:  # NwsError, no internet, a bad reply
        return {"available": False, "reason": f"The National Weather Service didn't answer: {exc}"}
    data = {"available": True, "metric": metric, "unit": units.unit("tempf", metric),
            "periods": [{"name": p["name"], "is_day": p["isDaytime"], "temp": _temp(p["temperature"], p["unit"], metric),
                         "short": p["short"], "detail": p["detail"], "rain_chance": p["pop"], "wind": p["wind"]}
                        for p in daily],
            "hours": [{"start": h["start"], "temp": _temp(h["temperature"], h["unit"], metric), "short": h["short"],
                       "rain_chance": h["pop"]} for h in hourly],
            "alerts": [{"event": a["event"], "severity": a["severity"], "headline": a["headline"]} for a in alert_list]}
    _forecast_cache[key] = (now, data)
    return data
