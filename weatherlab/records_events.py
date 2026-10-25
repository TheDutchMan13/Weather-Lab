"""Extreme events for the Records page (0.37.14): pure helpers, no streamlit, so they can be tested.

days: [(date, daily summary dict)] in date order. Temperatures are in F, rain in inches, gusts in mph.
"""
from __future__ import annotations

HEAT_F = 105.0     # a heat event: daily high at or above this
COLD_F = 32.0      # a cold event: daily low at or below this
WIND_MPH = 40.0    # a wind event: daily gust at or above this
RAIN_IN = 0.25     # a rain event: daily rain at or above this

GROUPS = {
    "Records": ["Extreme events", "Records board", "Distribution"],
    "Heat": [],
    "Rain and storms": [],
    "Climate and comparisons": [],
}
GROUP_NOTES = {
    "Records": "Top values and the days that set them",
    "Heat": "Hot days by year",
    "Rain and storms": "The wettest days and rain events",
    "Climate and comparisons": "This date in earlier years, and period comparisons",
}


def _events(days, key, test, reverse):
    found = [(d, s[key]) for d, s in days if s.get(key) is not None and test(s[key])]
    found.sort(key=lambda x: (x[1], x[0]), reverse=reverse)
    return found


def events(days) -> dict:
    """{"heat","cold","wind","rain": [(date, value)]} each ordered most extreme first."""
    return {
        "heat": _events(days, "tempf_max", lambda v: v >= HEAT_F, True),
        "cold": _events(days, "tempf_min", lambda v: v <= COLD_F, False),
        "wind": _events(days, "gust_max", lambda v: v >= WIND_MPH, True),
        "rain": _events(days, "rain_in", lambda v: v >= RAIN_IN, True),
    }


def summary(days) -> dict:
    """Numbers for the top tiles."""
    highs = [(s["tempf_max"], d) for d, s in days if s.get("tempf_max") is not None]
    gusts = [(s["gust_max"], d) for d, s in days if s.get("gust_max") is not None]
    rain = [(s["rain_in"], d) for d, s in days if s.get("rain_in") is not None]
    return {
        "days_100": sum(1 for v, _ in highs if v >= 100),
        "days_110": sum(1 for v, _ in highs if v >= 110),
        "hottest": max(highs) if highs else None,
        "gust": max(gusts) if gusts else None,
        "rain_total": sum(v for v, _ in rain),
        "rain_days": sum(1 for v, _ in rain if v >= 0.01),
    }


def distribution(days, key: str = "tempf_max", width: int = 5) -> list[tuple[int, int]]:
    """Count of days per bucket: [(bucket start, count)] from the lowest to the highest bucket, empty buckets kept."""
    values = [s[key] for _, s in days if s.get(key) is not None]
    if not values:
        return []
    lo = int(min(values) // width * width)
    hi = int(max(values) // width * width)
    counts = {b: 0 for b in range(lo, hi + width, width)}
    for v in values:
        counts[int(v // width * width)] += 1
    return list(counts.items())
