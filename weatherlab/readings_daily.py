"""Daily summaries from Ecowitt readings exports that are finer than daily (every minute, 5 minutes or 4 hours).

A day runs from 5 PM to 5 PM and is stored under the date it ends on, as the daily export does. A day is only made
when the readings reach both of its ends, so a partial day is left out. Days from readings every 5 minutes or finer
match the station's own records closely. Days from longer intervals are marked estimated, because a high or a low can
happen between two readings.
"""

import re
from datetime import datetime, time, timedelta
from statistics import median

FMT = "%Y-%m-%d %H:%M"
DAY_END = time(17, 0)
EXACT_MINUTES = 5
WANTED = {  # (column group, column name) -> what it feeds
    ("Outdoor", "Temperature"): "temp",
    ("Outdoor", "Humidity"): "hum",
    ("Rainfall Piezo", "Daily"): "rain",
    ("Rainfall Piezo", "Rain Rate"): "rate",
    ("Wind", "Wind Gust"): "gust",
    ("Pressure", "Relative"): "baro",
    ("Solar and UVI", "UVI"): "uvi",
}
KEYS = {  # role -> the stored reading key
    "temp": "tempf", "hum": "humidity", "rain": "dailyrainin", "rate": "rainratein", "gust": "windgustmph",
    "baro": "baromrelin", "uvi": "uv", "feels": "feelslikef", "dew": "dewpointf", "wind": "windspeedmph",
    "dir": "winddir", "solar": "solarradiation", "tempin": "tempinf", "humin": "humidityin", "baroabs": "baromabsin",
}
EXTRA = {  # columns used for stored readings only when the file has them
    ("Outdoor", "Feels Like"): "feels", ("Outdoor", "Dew Point"): "dew", ("Wind", "Wind Speed"): "wind",
    ("Wind", "Wind Direction"): "dir", ("Solar and UVI", "Solar"): "solar", ("Indoor", "Temperature"): "tempin",
    ("Indoor", "Humidity"): "humin", ("Pressure", "Absolute"): "baroabs",
}


def _name(text) -> str:
    return re.sub(r"\(.*?\)", "", str(text or "")).strip()


def _columns(rows) -> dict:
    top, sub = rows[0], rows[1]
    group, found = None, {}
    for i in range(max(len(top), len(sub))):
        if i < len(top) and top[i]:
            group = _name(top[i])
        name = _name(sub[i]) if i < len(sub) else ""
        role = WANTED.get((group, name)) or EXTRA.get((group, name))
        if role and role not in found:
            found[role] = i
    if "temp" not in found:
        raise ValueError("This file doesn't have the temperature, humidity, rain, wind, pressure and UV readings. "
                         "Export the history from ecowitt.net.")
    return found


def _number(row, i):
    value = row[i] if i < len(row) else None
    return float(value) if isinstance(value, (int, float)) else None


def _samples(rows) -> dict:
    """{time: {role: value}} for the rows that start with a time."""
    if len(rows) < 3:
        raise ValueError("That file has no data rows.")
    cols = _columns(rows)
    samples = {}
    for row in rows[2:]:
        if not row or not isinstance(row[0], str):
            continue
        try:
            stamp = datetime.strptime(row[0].strip(), FMT)
        except ValueError:
            continue
        samples[stamp] = {role: _number(row, i) for role, i in cols.items()}
    return samples


def _interval(times):
    """Typical minutes between readings, or None when there are fewer than two."""
    gaps = [(b - a).total_seconds() / 60 for a, b in zip(times, times[1:])]
    return median(gaps) if gaps else None


def readings_from_rows(rows):
    """([(time, {stored key: value})], minutes between readings) for every row of one export, whatever span it covers."""
    samples = _samples(rows)
    out = []
    for stamp in sorted(samples):
        reading = {KEYS[role]: value for role, value in samples[stamp].items() if value is not None}
        if reading:
            out.append((stamp, reading))
    return out, _interval(sorted(samples))


def _pick(values, fn):
    return fn(values) if values else None


def _round2(value):
    return round(value, 2) if value is not None else None


def _day(times, samples, day, minutes):
    start = datetime.combine(day - timedelta(days=1), DAY_END)
    end = datetime.combine(day, DAY_END)
    gap = timedelta(minutes=2 * minutes)  # one missing reading is allowed inside a day
    edge = timedelta(minutes=minutes)  # the readings must reach both ends of the day, within one interval
    if any(role not in samples[times[0]] for role in ("temp", "hum", "rain", "rate", "gust", "baro", "uvi")):
        return None
    window = [t for t in times if start < t <= end]
    if not window or window[0] - start > edge or end - window[-1] > edge:
        return None
    if any(b - a > gap for a, b in zip(window, window[1:])):
        return None
    first = times.index(window[0])
    rain, last = 0.0, (samples[times[first - 1]].get("rain") if first > 0 else None)
    for t in window:
        now = samples[t].get("rain")
        if now is None:
            continue
        if last is not None:
            rain += (now - last) if now >= last else now  # the daily total starts again at midnight
        last = now

    def column(role):
        return [samples[t][role] for t in window if samples[t].get(role) is not None]

    temps, hums, gusts = column("temp"), column("hum"), column("gust")
    rates, baros, uvis = column("rate"), column("baro"), column("uvi")
    if not temps:
        return None
    out = {
        "tempf_max": _pick(temps, max), "tempf_min": _pick(temps, min),
        "tempf_avg": round(sum(temps) / len(temps), 1),
        "humidity_max": _pick(hums, max), "humidity_min": _pick(hums, min),
        "gust_max": _pick(gusts, max), "rainrate_max": _pick(rates, max) or 0.0,
        "baro_max": _round2(_pick(baros, max)), "baro_min": _round2(_pick(baros, min)),
        "rain_in": round(rain, 2), "uvi": _pick(uvis, max),
    }
    out = {key: value for key, value in out.items() if value is not None}
    if minutes > EXACT_MINUTES:
        out["estimated"] = True
    return out


def days_from_readings(files) -> dict:
    """{date: summary} for the days these readings cover. files: the rows of each export, as read from the file.
    When more than one export covers a day, the export with the finest readings is used."""
    groups = {}  # minutes between readings -> {time: sample}
    for rows in files:
        samples = _samples(rows)
        minutes = _interval(sorted(samples))
        if minutes:
            groups.setdefault(minutes, {}).update(samples)
    out = {}
    for minutes in sorted(groups):
        samples = groups[minutes]
        times = sorted(samples)
        day = times[0].date()
        while day <= times[-1].date() + timedelta(days=1):
            if day not in out:
                summary = _day(times, samples, day, minutes)
                if summary:
                    out[day] = summary
            day += timedelta(days=1)
    return out
