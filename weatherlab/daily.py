"""Daily summaries built from stored readings.

Copied from the dashboard's collectors/gw2000_collector.py: _solar_max, summarize_day,
and rollup_daily (see SOURCES.md). Changes for a generic app:
- location, timezone, and elevation come from settings instead of being hardcoded
- the solar calculation uses UTC plus longitude, so it works anywhere (the dashboard's
  Arizona-only standard meridian gives the same result for Phoenix)
"""

import json
import math
from datetime import date, datetime, timedelta, timezone, tzinfo

MIN_ROWS_FOR_DAY = 20  # fewer readings than this and the day is not summarized


def _solar_max(ts: float, lat: float, lon: float, elev_m: float, tz: tzinfo) -> float:
    """Rough clear-sky solar radiation (W/m2); used only to decide whether the sun was 'out'."""
    dt = datetime.fromtimestamp(ts, tz)
    doy = dt.timetuple().tm_yday
    utc = datetime.fromtimestamp(ts, timezone.utc)
    hour_utc = utc.hour + utc.minute / 60 + utc.second / 3600
    decl = math.radians(23.45) * math.sin(2 * math.pi * (284 + doy) / 365)
    b = 2 * math.pi * (doy - 81) / 364
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    ha = math.radians(15 * (hour_utc + lon / 15 + eot / 60 - 12))
    la = math.radians(lat)
    sin_alt = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    if sin_alt <= 0.05:
        return 0.0
    air_mass = 1 / (sin_alt + 0.50572 * (6.07995 + math.degrees(math.asin(sin_alt))) ** -1.6364)
    return 1367 * (1 + 0.033 * math.cos(2 * math.pi * doy / 365)) * sin_alt * 0.76 ** (air_mass * math.exp(-elev_m / 8434.5))


def summarize_day(rows, lat: float, lon: float, elev_m: float, tz: tzinfo):
    """rows: [(ts, reading dict)] for one local day in time order -> (summary dict, hours covered).
    summary is None when the day has too few readings."""
    def vals(key):
        return [r[key] for _, r in rows if r.get(key) is not None]

    temps = vals("tempf")
    if len(rows) < MIN_ROWS_FOR_DAY or not temps:
        return None, 0.0
    steps = sorted(rows[i + 1][0] - rows[i][0] for i in range(len(rows) - 1))
    cap = max(120, 1.5 * steps[len(steps) // 2]) if steps else 120  # the usual gap between readings, capped
    weights = [min(rows[i + 1][0] - rows[i][0], cap) for i in range(len(rows) - 1)] + [0]
    wsum = sum(weights) or 1
    avg = sum(r.get("tempf", temps[0]) * w for (_, r), w in zip(rows, weights)) / wsum
    run = sum((r.get("windspeedmph") or 0) * w / 3600 for (_, r), w in zip(rows, weights))
    sun = sum(w for (t, r), w in zip(rows, weights)
              if (r.get("solarradiation") or 0) > 0.9 * _solar_max(t, lat, lon, elev_m, tz) > 0) / 3600
    baro, hum, gust, wind = vals("baromrelin"), vals("humidity"), vals("windgustmph"), vals("windspeedmph")
    out = {"gust_max": max(gust) if gust else None, "tempf_min": min(temps), "tempf_max": max(temps),
           "baro_min": min(baro) if baro else None, "baro_max": max(baro) if baro else None,
           "rainrate_max": max(vals("rainratein") or [0.0]), "rain_in": max(vals("dailyrainin") or [0.0]),
           "tempf_avg": round(avg, 1), "wind_run_mi": round(run, 1), "wind_max": max(wind) if wind else None,
           "humidity_min": min(hum) if hum else None, "humidity_max": max(hum) if hum else None,
           "sun_hours": round(sun, 1), "solar_rad": max(vals("solarradiation") or [0.0]),
           "uvi": max(vals("uv") or [0.0])}
    tin, hin = vals("tempinf"), vals("humidityin")
    if tin:
        out.update(indoor_tempf_max=max(tin), indoor_tempf_min=min(tin), indoor_tempf_avg=round(sum(tin) / len(tin), 1))
    if hin:
        out.update(indoor_humidity_max=max(hin), indoor_humidity_min=min(hin))
    return {k: v for k, v in out.items() if v is not None}, round(wsum / 3600, 1)


def day_rows(db, day: date, tz: tzinfo):
    """Stored readings for one local day, as [(ts, reading)]."""
    start = int(datetime(day.year, day.month, day.day, tzinfo=tz).timestamp())
    nxt = day + timedelta(days=1)
    end = int(datetime(nxt.year, nxt.month, nxt.day, tzinfo=tz).timestamp())
    rows = []
    for ts, data in db.execute("SELECT ts, data FROM readings WHERE ts >= ? AND ts < ? ORDER BY ts", (start, end)):
        try:
            rows.append((ts, json.loads(data)))
        except (TypeError, ValueError):
            continue
    return rows


def _imported(data: str) -> bool:
    try:
        return json.loads(data).get("source") == "ecowitt"
    except (TypeError, ValueError, AttributeError):
        return False


def rollup_days(db, days, lat: float, lon: float, elev_m: float, tz: tzinfo, today: date) -> list[str]:
    """Build and store summaries for finished days. Today is skipped (it is summarized live).
    Returns the dates written."""
    written = []
    for day in days:
        if day >= today:
            continue
        held = db.execute("SELECT data FROM daily WHERE date = ?", (day.isoformat(),)).fetchone()
        if held and _imported(held[0]):
            continue  # days imported from an Ecowitt export are never replaced
        summary, _hours = summarize_day(day_rows(db, day, tz), lat, lon, elev_m, tz)
        if not summary:
            continue
        with db:
            db.execute("INSERT OR REPLACE INTO daily (date, data) VALUES (?, ?)",
                       (day.isoformat(), json.dumps(summary)))
        written.append(day.isoformat())
    return written
