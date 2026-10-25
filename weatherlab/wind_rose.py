"""Wind rose: how often the wind came from each direction, and how fast. Built from the station's readings."""

from datetime import datetime

CALM_MPH = 1.0  # readings under this count as calm
WINDY_MPH = 5.0  # readings at or above this count as windy for the monthly table

NAMES = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
# Calm (under 1 mph) is counted in the totals and the monthly table but not drawn on the rose: the rose shows the
# bands in DRAWN, 1 mph up to 5+ mph, which is what the wind rose and its legend use.
SPEED_BINS = [(0, 1, "Calm (under 1 mph)"), (1, 2, "1 mph"), (2, 3, "2 mph"), (3, 5, "3-4 mph"), (5, None, "5+ mph")]
DRAWN = list(range(1, len(SPEED_BINS)))


def label(index: int, metric: bool = False) -> str:
    """Speed range text for one bin, in mph or km/h."""
    lo, hi, us_text = SPEED_BINS[index]
    if not metric:
        return us_text
    if hi is None:
        return f"{round(lo * 1.609344)}+ km/h"
    if lo == 0:
        return f"Calm (under {round(hi * 1.609344)} km/h)"
    return f"{round(lo * 1.609344)}-{round(hi * 1.609344)} km/h"


def _bin(speed):
    for i, (lo, hi, _) in enumerate(SPEED_BINS):
        if speed >= lo and (hi is None or speed < hi):
            return i
    return None


def rose(readings):
    """Returns (counts, total): counts[speed bin][direction]. Readings without a direction or speed are skipped."""
    counts = [[0] * len(NAMES) for _ in SPEED_BINS]
    total = 0
    for r in readings:
        d, s = r.get("winddir"), r.get("windspeedmph")
        if d is None or s is None:
            continue
        b = _bin(s)
        if b is None:
            continue
        counts[b][int(((d % 360) + 11.25) // 22.5) % len(NAMES)] += 1
        total += 1
    return counts, total


def percentages(counts, total):
    if not total:
        return [[0.0] * len(NAMES) for _ in SPEED_BINS]
    return [[round(100 * c / total, 1) for c in row] for row in counts]


def dominant(counts):
    """The direction the wind most often came from, such as "SW", or "--" with no data."""
    sums = [sum(row[i] for row in counts) for i in range(len(NAMES))]
    if not any(sums):
        return "--"
    return NAMES[sums.index(max(sums))]


def patterns(items, tz) -> dict:
    """Wind for a period. items: (ts, reading) pairs in time order (see storage.readings_sampled).
    Returns the rose counts, the readings counted, and one row per month: the direction the windy readings most
    often came from, what share of them, and the average speed of all readings with a direction."""
    overall = [[0] * len(NAMES) for _ in SPEED_BINS]
    total = 0
    calm = 0
    months: dict[str, dict] = {}
    for ts, r in items:
        d, s = r.get("winddir"), r.get("windspeedmph")
        if d is None or s is None:
            continue
        b = _bin(s)
        if b is None:
            continue
        i = int(((d % 360) + 11.25) // 22.5) % len(NAMES)
        overall[b][i] += 1
        total += 1
        if s < CALM_MPH:
            calm += 1
        m = months.setdefault(datetime.fromtimestamp(ts, tz).strftime("%Y-%m"),
                              {"windy": [0] * len(NAMES), "speed_sum": 0.0, "n": 0})
        m["n"] += 1
        m["speed_sum"] += s
        if s >= WINDY_MPH:
            m["windy"][i] += 1
    rows = []
    for key in sorted(months):
        m = months[key]
        windy_total = sum(m["windy"])
        top = m["windy"].index(max(m["windy"])) if windy_total else None
        rows.append({"month": datetime.strptime(key, "%Y-%m").strftime("%b %Y"),
                     "from": NAMES[top] if top is not None else None,
                     "share": round(100 * m["windy"][top] / windy_total, 1) if top is not None else None,
                     "avg_mph": round(m["speed_sum"] / m["n"], 1)})
    return {"counts": overall, "total": total, "calm": calm, "months": rows}
