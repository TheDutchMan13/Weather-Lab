"""The data behind the Android app's pages: rankings, rain, wind, lightning, sun and UV, heat safety, station health,
What's New and the forecast. Read-only, in the units chosen in Settings. api.py routes to these."""

import calendar
import json
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from statistics import mean, pstdev

from weatherlab import (airquality, astro, forecast_check, gateway_sensors, health, heat_safety, history,
                        history_compare, lightning_history, nws, push, rain_events, storage, sun_uv, tropics, units,
                        whats_new, wind_rose, yearly)
from weatherlab import secrets as keystore

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
            "bins": [wind_rose.label(i, metric) for i in wind_rose.DRAWN],
            "directions": [{"name": name, "bins": [pct[b][i] for b in wind_rose.DRAWN],
                            "percent": round(sum(pct[b][i] for b in wind_rose.DRAWN), 1)}
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
    hours = heat_safety.hours_by_level(series)
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
            "unit": units.unit("heat_index", metric), "metric": metric,
            # Added in 0.37.21 for the Android Heat safety page.
            "hours": [{"level": name, "hours": round(hours[name], 1)} for name in heat_safety.LEVEL_NAMES],
            "danger_hours": round(heat_safety.danger_hours(hours), 1),
            "danger_limit": _show("heat_index", heat_safety.DANGER_INDEX, metric, 0),
            "danger_days": [{"date": d.isoformat(), "value": _show("heat_index", hi, metric, 0), "level": lvl}
                            for d, hi, lvl in heat_safety.dangerous_days(history.all_daily(db))[:15]],
            "series": _heat_series(today, metric)}


def _heat_series(today: list, metric: bool) -> list:
    """Today's [timestamp, air temperature, heat index] about every few minutes, at most 150 points."""
    rows = [(ts, r.get("tempf"), heat_safety.heat_index(r.get("tempf"), r.get("humidity"))) for ts, r in today]
    rows = [x for x in rows if x[1] is not None and x[2] is not None]
    step = -(-len(rows) // 150) if len(rows) > 150 else 1
    return [[ts, _show("tempf", t_, metric, 1), _show("heat_index", hi, metric, 1)] for ts, t_, hi in rows[::step]]


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


# ------------------------------------------------------------------ history pages

def _day(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def on_this_day(db, s, now: float, which: str) -> dict:
    """The same calendar day in every year with data. which: 'today' or a month and day such as 10-23."""
    metric = units.is_metric(s.units)
    if which == "today":
        d = datetime.fromtimestamp(now, _tz(s)).date()
        month, day = d.month, d.day
    else:
        try:
            parsed = datetime.strptime("2000-" + which, "%Y-%m-%d")  # 2000 is a leap year, so 02-29 works
        except ValueError:
            return {"error": "Use a date like 10-23, or today."}
        month, day = parsed.month, parsed.day
    rows = yearly.on_this_day(history.all_daily(db), month, day)
    years = [{"year": d.year, "high": _show("tempf", x.get("tempf_max"), metric),
              "low": _show("tempf", x.get("tempf_min"), metric), "rain": _show("dailyrainin", x.get("rain_in"), metric, 2)}
             for d, x in reversed(rows)]
    highs = [x["tempf_max"] for _, x in rows if x.get("tempf_max") is not None]
    lows = [x["tempf_min"] for _, x in rows if x.get("tempf_min") is not None]
    return {"month": month, "day": day, "years": years,
            "record_high": _show("tempf", max(highs), metric) if highs else None,
            "record_low": _show("tempf", min(lows), metric) if lows else None,
            "temp_unit": units.unit("tempf", metric), "rain_unit": units.unit("dailyrainin", metric), "metric": metric}


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def compare(db, s, now: float) -> dict:
    """Average temperature and rain for each month of the last three years, rain so far this year against the same
    dates in earlier years, and hot days by year."""
    metric = units.is_metric(s.units)
    tz = _tz(s)
    today = datetime.fromtimestamp(now, tz).date()
    days = history.all_daily(db)
    monthly = yearly.monthly(days)
    years = sorted(monthly, reverse=True)[:3]
    months = []
    for m in range(1, 13):
        values = {}
        for y in years:
            cell = monthly.get(y, {}).get(m)
            if cell:
                values[str(y)] = {"temp": _show("tempf", cell["temp"], metric), "rain": _show("dailyrainin", cell["rain"], metric, 2)}
        months.append({"month": m, "label": MONTHS[m - 1], "values": values})
    to_date = []
    for y in sorted({d.year for d, _ in days}, reverse=True)[:5]:
        end = date(y, today.month, min(today.day, calendar.monthrange(y, today.month)[1]))
        total = sum(x.get("rain_in") or 0.0 for d, x in days if d.year == y and d <= end)
        to_date.append({"year": y, "rain": _show("dailyrainin", total, metric, 2)})
    heat = [{"year": y, "days_100": c[100], "days_110": c[110]}
            for y, c in sorted(history_compare.heat_days_by_year(days).items(), reverse=True)]
    return {"years": years, "months": months, "rain_to_date": to_date, "heat_days": heat,
            "temp_unit": units.unit("tempf", metric), "rain_unit": units.unit("dailyrainin", metric), "metric": metric}


def month_card(db, s, now: float, month: str) -> dict:
    metric = units.is_metric(s.units)
    try:
        first = datetime.strptime(month, "%Y-%m").date()
    except ValueError:
        return {"error": "Use a month like 2026-10."}
    last = first.replace(day=calendar.monthrange(first.year, first.month)[1])
    rows = history.daily_between(db, first, last)
    if not rows:
        return {"month": month, "found": False}

    def pick(key, fn):
        found = [(x[key], d) for d, x in rows if x.get(key) is not None]
        return fn(found) if found else None

    def best(key, fn, ukey, digits=1):
        hit = pick(key, fn)
        return None if hit is None else {"value": _show(ukey, hit[0], metric, digits), "date": hit[1].isoformat()}
    highs = [x["tempf_max"] for _, x in rows if x.get("tempf_max") is not None]
    lows = [x["tempf_min"] for _, x in rows if x.get("tempf_min") is not None]
    rain = [x["rain_in"] for _, x in rows if x.get("rain_in") is not None]
    return {"month": month, "found": True, "days_with_data": len(rows),
            "average_high": _show("tempf", mean(highs), metric) if highs else None,
            "average_low": _show("tempf", mean(lows), metric) if lows else None,
            "hottest": best("tempf_max", max, "tempf"), "coldest": best("tempf_min", min, "tempf"),
            "wettest": best("rain_in", max, "dailyrainin", 2), "windiest": best("gust_max", max, "windgustmph"),
            "rain_total": _show("dailyrainin", sum(rain), metric, 2), "rainy_days": sum(1 for r in rain if r >= 0.01),
            "daily": [{"date": d.isoformat(), "high": _show("tempf", x.get("tempf_max"), metric),
                       "low": _show("tempf", x.get("tempf_min"), metric),
                       "rain": _show("dailyrainin", x.get("rain_in"), metric, 2)} for d, x in rows],
            "temp_unit": units.unit("tempf", metric), "rain_unit": units.unit("dailyrainin", metric),
            "wind_unit": units.unit("windgustmph", metric), "metric": metric}


def _longest_run(rows, wet: bool):
    """(length, first day, last day) of the longest run of consecutive days wet or dry."""
    best, cur = (0, None, None), None
    prev = None
    for d, x in rows:
        r = x.get("rain_in")
        ok = r is not None and ((r >= 0.01) if wet else (r < 0.01))
        if ok and cur is not None and prev is not None and (d - prev).days == 1:
            cur = (cur[0] + 1, cur[1], d)
        elif ok:
            cur = (1, d, d)
        else:
            cur = None
        prev = d
        if cur and cur[0] > best[0]:
            best = cur
    return best


def year_card(db, s, now: float, year: int) -> dict:
    metric = units.is_metric(s.units)
    days = history.all_daily(db)
    sm = yearly.year_summary(days, year)
    if sm is None:
        return {"year": year, "found": False}
    rows = [(d, x) for d, x in days if d.year == year]

    def at(hit, ukey, digits=1):
        return None if hit is None else {"date": hit[0].isoformat(), "value": _show(ukey, hit[1], metric, digits)}

    def run(wet):
        n, a, b = _longest_run(rows, wet)
        return None if not n else {"days": n, "from": a.isoformat(), "to": b.isoformat()}
    highs = [x["tempf_max"] for _, x in rows if x.get("tempf_max") is not None]
    return {"year": year, "found": True, "days_with_data": sm["days"], "rain": _show("dailyrainin", sm["rain"], metric, 2),
            "rainy_days": sm["rainy_days"], "hottest": at(sm["hottest"], "tempf"), "coldest": at(sm["coldest"], "tempf"),
            "windiest": at(sm["windiest"], "windgustmph"), "days_90": sum(1 for h in highs if h >= 90),
            "days_100": sm["hot_days"], "freezing_nights": sm["freezing"], "longest_dry": run(False),
            "longest_wet": run(True), "years": sorted({d.year for d, _ in days}, reverse=True),
            "temp_unit": units.unit("tempf", metric), "rain_unit": units.unit("dailyrainin", metric),
            "wind_unit": units.unit("windgustmph", metric), "metric": metric}


MILESTONES = [  # (key, label key, daily field, "min" or "max", threshold in °F)
    ("freeze", "tempf_min", "le", 32.0), ("90", "tempf_max", "ge", 90.0), ("100", "tempf_max", "ge", 100.0),
]


def milestones(db, s, now: float) -> dict:
    """First and last day of each year at or below freezing and at or above 90 and 100 degrees."""
    metric = units.is_metric(s.units)
    days = history.all_daily(db)
    out = []
    for key, field, op, limit in MILESTONES:
        by_year = {}
        for d, x in days:
            v = x.get(field)
            if v is None or not ((v <= limit) if op == "le" else (v >= limit)):
                continue
            e = by_year.setdefault(d.year, {"first": d, "last": d, "count": 0})
            e["first"], e["last"], e["count"] = min(e["first"], d), max(e["last"], d), e["count"] + 1
        shown = round(units.convert("tempf", limit, metric))
        label = {"freeze": f"Freezing nights ({shown}{units.unit('tempf', metric)} or colder)"}.get(
            key, f"Days at {shown}{units.unit('tempf', metric)} or hotter")
        out.append({"key": key, "label": label,
                    "years": [{"year": y, "first": by_year[y]["first"].isoformat(), "last": by_year[y]["last"].isoformat(),
                               "count": by_year[y]["count"]} for y in sorted(by_year, reverse=True)]})
    return {"milestones": out, "metric": metric}


def anomalies(db, s, now: float) -> dict:
    """Readings from the last 24 hours that sit far outside the previous 30 days (more than 3 standard deviations)."""
    metric = units.is_metric(s.units)
    tz = _tz(s)
    older = storage.readings_sampled(db, now - 31 * 86400, now - 86400, every_s=1800)
    recent = storage.readings_sampled(db, now - 86400, now + 1, every_s=300)
    found = []
    for key, label in (("tempf", "Temperature"), ("humidity", "Humidity"), ("windgustmph", "Gust"), ("baromrelin", "Pressure")):
        base = [r[key] for _, r in older if r.get(key) is not None]
        if len(base) < 200:
            continue
        mu, sd = mean(base), pstdev(base)
        if sd <= 0:
            continue
        latest = [(ts, r[key]) for ts, r in recent if r.get(key) is not None]
        if not latest:
            continue
        hi = max(latest, key=lambda x: x[1])
        lo = min(latest, key=lambda x: x[1])
        for kind, (ts, v) in (("high", hi), ("low", lo)):
            if abs(v - mu) > 3 * sd and (kind == "high") == (v > mu):
                digits = 2 if key == "baromrelin" else 1
                found.append({"label": label, "kind": kind, "value": _show(key, v, metric, digits),
                              "usual": _show(key, mu, metric, digits), "unit": units.unit(key, metric) if units.converts(key) else "%",
                              "time": datetime.fromtimestamp(ts, tz).strftime("%a %H:%M")})
    return {"anomalies": found, "checked": ["Temperature", "Humidity", "Gust", "Pressure"], "metric": metric}


def alert_history(db, s, now: float) -> dict:
    rows = [(ts, text) for ts, text in storage.recent_alerts(db, limit=300) if ts >= now - 14 * 86400]
    return {"alerts": [{"ts": ts, "text": text} for ts, text in rows]}


def forecast_accuracy(db, s, now: float) -> dict:
    metric = units.is_metric(s.units)
    forecasts = storage.forecast_highs(db)
    actuals = {d: x["tempf_max"] for d, x in history.all_daily(db) if x.get("tempf_max") is not None}
    rows = forecast_check.compare(forecasts, actuals)[:60]
    stats = forecast_check.accuracy(rows)

    def delta(v):
        return None if v is None else round(units.convert_change("tempf", v, metric), 1)
    return {"days": stats["days"], "average_miss": delta(stats["mae"]), "bias": delta(stats["bias"]),
            "rows": [{"date": d.isoformat(), "forecast": _show("tempf", f, metric, 0), "actual": _show("tempf", a, metric, 0),
                      "miss": delta(diff)} for d, f, a, diff in rows[:30]],
            "unit": units.unit("tempf", metric), "metric": metric}


def export_daily(db, s, now: float) -> dict:
    """Every daily summary as a CSV, in US units (like the exports from the PC)."""
    return {"filename": "weatherlab-daily.csv", "csv": history.daily_csv(history.all_daily(db))}


def rewind(db, s, now: float, which: str) -> dict:
    """One past day, minute by minute thinned to every 10 minutes, for the phone's touch charts."""
    metric = units.is_metric(s.units)
    tz = _tz(s)
    try:
        day = _day(which)
    except ValueError:
        return {"error": "Use a date like 2026-10-20."}
    start = datetime.combine(day, datetime.min.time(), tzinfo=tz).timestamp()
    rows = storage.readings_sampled(db, start, start + 86400, every_s=600)
    series = []
    for key, label, digits in (("tempf", "Temperature", 1), ("humidity", "Humidity", 0), ("windspeedmph", "Wind", 1),
                               ("windgustmph", "Gust", 1), ("dailyrainin", "Rain so far", 2), ("baromrelin", "Pressure", 2)):
        pts = [[ts, _show(key, r[key], metric, digits)] for ts, r in rows if r.get(key) is not None]
        if pts:
            series.append({"key": key, "label": label, "unit": units.unit(key, metric) if units.converts(key) else "%", "points": pts})
    return {"date": day.isoformat(), "found": bool(series), "series": series, "metric": metric}


# ------------------------------------------------------------------ public sources (US National Weather Service, NHC, AirNow)

_cache: dict = {}


def _cached(key, now, seconds, make):
    held = _cache.get(key)
    if held and now - held[0] < seconds:
        return held[1]
    value = make()
    _cache[key] = (now, value)
    return value


def airport(db, s, now: float) -> dict:
    """Your station next to the nearest airport (or weather station) reporting to the National Weather Service."""
    if s.latitude is None or s.longitude is None:
        return {"available": False, "reason": "Set the station's latitude and longitude in Weather Lab's Setup page."}
    metric = units.is_metric(s.units)
    try:
        def lookup():
            url = nws.points(s.latitude, s.longitude, s.nws_contact).get("stations", "")
            return nws.nearest_airport_station(url, s.latitude, s.longitude, s.nws_contact) if url else None
        station = _cached(("airport", s.latitude, s.longitude), now, 86400, lookup)
        if not station:
            return {"available": False, "reason": "No weather station was found near this location."}
        obs = _cached(("obs", station["id"]), now, 600, lambda: nws.latest_observation(station["id"], s.nws_contact))
    except Exception as exc:
        return {"available": False, "reason": f"The National Weather Service didn't answer: {exc}"}
    latest = storage.latest(db)
    mine = latest[1] if latest else {}
    km = station.get("km", 0)

    def row(label, key, mine_v, theirs_v, digits=0):
        return {"label": label, "station": _show(key, mine_v, metric, digits) if key else mine_v,
                "airport": _show(key, theirs_v, metric, digits) if key else theirs_v,
                "unit": units.unit(key, metric) if key else "%"}
    return {"available": True, "name": station.get("name", ""), "airport": bool(station.get("airport")),
            "distance": round(units.convert("miles", km / 1.609344, metric), 1), "distance_unit": units.unit("miles", metric),
            "time": obs.get("time", ""), "text": obs.get("text", ""),
            "visibility": None if obs.get("visibility_mi") is None else
            {"value": round(units.convert("miles", obs["visibility_mi"], metric), 1), "unit": units.unit("miles", metric)},
            "present": [w for w in obs.get("present", []) if w],
            "rows": [row("Temperature", "tempf", mine.get("tempf"), obs.get("temp_f")),
                     row("Humidity", None, mine.get("humidity"), obs.get("humidity")),
                     row("Wind", "windspeedmph", mine.get("windspeedmph"), obs.get("wind_mph")),
                     row("Gust", "windgustmph", mine.get("windgustmph"), obs.get("gust_mph"))], "metric": metric}


def tropics_list(db, s, now: float) -> dict:
    if s.latitude is None or s.longitude is None:
        return {"available": False, "reason": "Set the station's latitude and longitude in Weather Lab's Setup page."}
    metric = units.is_metric(s.units)
    cache = tropics.refresh((s.latitude, s.longitude), storage.db_path().parent / "tropics.json")
    return {"available": True, "ok": bool(cache.get("ok", True)), "checked": cache.get("checked", ""),
            "storms": [{"name": x["name"], "class": x["class"], "wind": _show("windspeedmph", x["wind_mph"], metric, 0),
                        "distance": _show("miles", x["miles"], metric, 0), "direction": x["direction"], "move": x["move"]}
                       for x in cache.get("storms", [])],
            "wind_unit": units.unit("windspeedmph", metric), "distance_unit": units.unit("miles", metric)}


RADAR_RIDGE = "https://radar.weather.gov/ridge/standard/"


def radar(db, s, now: float) -> dict:
    if s.latitude is None or s.longitude is None:
        return {"available": False, "reason": "Set the station's latitude and longitude in Weather Lab's Setup page."}
    try:
        station = _cached(("radar", s.latitude, s.longitude), now, 86400,
                          lambda: nws.points(s.latitude, s.longitude, s.nws_contact).get("radar", ""))
    except Exception as exc:
        station = ""
    out = {"available": True, "us_image": RADAR_RIDGE + "CONUS_0.gif", "us_page": "https://radar.weather.gov/"}
    if station:
        out.update(local_image=RADAR_RIDGE + f"{station}_0.gif", local_loop=RADAR_RIDGE + f"{station}_loop.gif",
                   local_page=f"https://radar.weather.gov/station/{station.lower()}/standard", station=station)
    return out


def air(db, s, now: float) -> dict:
    key = keystore.get_key("airnow")
    if not key:
        return {"available": False, "reason": "Add a free AirNow key in Weather Lab's Setup page to show air quality."}
    if s.latitude is None or s.longitude is None:
        return {"available": False, "reason": "Set the station's latitude and longitude in Weather Lab's Setup page."}
    try:
        data = _cached(("air", s.latitude, s.longitude), now, 600, lambda: airquality.fetch(s.latitude, s.longitude, key))
    except Exception as exc:
        return {"available": False, "reason": str(exc)}
    if not data:
        return {"available": False, "reason": "AirNow has no reading for this location right now."}
    return {"available": True, "aqi": data["aqi"], "category": data["category"], "area": data.get("station", ""),
            "pollutants": [{"label": label, "aqi": data[k]} for label, k in
                           (("PM2.5", "pm25_aqi"), ("PM10", "pm10_aqi"), ("Ozone", "ozone_aqi")) if k in data]}


def push_info(db, s, now: float) -> dict:
    """Where the PC sends phone alerts, so the phone can subscribe to the same ntfy topic."""
    return {"server": s.ntfy_server.strip() or push.DEFAULT_SERVER, "topic": keystore.get_key(push.topic_key()) or ""}
