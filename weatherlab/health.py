"""Sensor health from the stored readings: how complete the data is, where the gaps are,
and when each sensor last reported. Written for Weather Lab; it uses the same readings table as the
rest of the app. Expected interval comes from the poller (POLL_SECONDS)."""

from datetime import datetime

from weatherlab.poller import POLL_SECONDS

GAP_SECONDS = 300  # a gap longer than this is reported

# (label, reading key) for each sensor, in the order the Sensors page shows them
SENSORS = [
    ("Outdoor temp", "tempf"),
    ("Dew point", "dewpointf"),
    ("Humidity", "humidity"),
    ("Pressure", "baromrelin"),
    ("Wind", "windspeedmph"),
    ("Gust", "windgustmph"),
    ("Rain today", "dailyrainin"),
    ("Solar", "solarradiation"),
    ("UV index", "uv"),
    ("Indoor temp", "tempinf"),
    ("Indoor humidity", "humidityin"),
]


def window(db, since_ts: float, until_ts: float) -> list[tuple[int, dict]]:
    import json
    rows = db.execute("SELECT ts, data FROM readings WHERE ts >= ? AND ts <= ? ORDER BY ts",
                      (int(since_ts), int(until_ts))).fetchall()
    out = []
    for ts, data in rows:
        try:
            out.append((ts, json.loads(data)))
        except (TypeError, ValueError):
            continue
    return out


def completeness(rows, hours: float) -> float:
    """Share of the expected readings that were stored, as a percentage (capped at 100)."""
    expected = hours * 3600 / POLL_SECONDS
    return round(min(100.0, 100.0 * len(rows) / expected), 1) if expected else 0.0


def gaps(rows, threshold_s: int = GAP_SECONDS) -> list[tuple[int, int]]:
    """(start_ts, end_ts) for each pause longer than threshold_s between stored readings."""
    out = []
    for (a, _), (b, _) in zip(rows, rows[1:]):
        if b - a > threshold_s:
            out.append((a, b))
    return out


def sensors(rows) -> list[dict]:
    """For each sensor: share of readings that include it, and when it was last seen."""
    total = len(rows) or 1
    out = []
    for label, key in SENSORS:
        seen = [ts for ts, r in rows if r.get(key) is not None]
        out.append({
            "label": label,
            "key": key,
            "present_pct": round(100.0 * len(seen) / total, 1),
            "last_seen": seen[-1] if seen else None,
        })
    return out


def age_status(last_ts: float | None, now_ts: float) -> tuple[str, str]:
    """('ok' | 'slow' | 'silent' | 'none', text) for a status dot."""
    if last_ts is None:
        return "none", "No readings yet"
    age = now_ts - last_ts
    minutes = int(age // 60)
    text = "just now" if minutes < 1 else f"{minutes} min ago"
    if age <= 5 * 60:
        return "ok", text
    if age <= 15 * 60:
        return "slow", text
    return "silent", text


def clock(ts: float, tz) -> str:
    from weatherlab import timefmt
    return timefmt.stamp(datetime.fromtimestamp(ts, tz), sep=" ")
