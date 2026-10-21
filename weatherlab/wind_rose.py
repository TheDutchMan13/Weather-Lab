"""Wind rose: how often the wind came from each direction, and how fast. Built from the station's readings."""

NAMES = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
SPEED_BINS = [(0, 5, "0-5 mph"), (5, 10, "5-10 mph"), (10, 15, "10-15 mph"), (15, 20, "15-20 mph"), (20, None, "20+ mph")]


def label(index: int, metric: bool = False) -> str:
    """Speed range text for one bin, in mph or km/h."""
    lo, hi, us_text = SPEED_BINS[index]
    if not metric:
        return us_text
    lo_k = round(lo * 1.609344)
    return f"{lo_k}+ km/h" if hi is None else f"{lo_k}-{round(hi * 1.609344)} km/h"


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
