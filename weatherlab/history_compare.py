"""Totals and averages for a range of daily summaries, used to compare two periods."""

from datetime import date
from statistics import mean


def period_stats(rows: list[tuple]) -> dict:
    """rows: [(date, daily summary)]. Values are None when a period has no data for them."""
    highs = [d["tempf_max"] for _, d in rows if d.get("tempf_max") is not None]
    lows = [d["tempf_min"] for _, d in rows if d.get("tempf_min") is not None]
    rain = [d.get("rain_in") or 0.0 for _, d in rows]
    return {
        "days": len(rows),
        "avg_high": round(mean(highs), 1) if highs else None,
        "avg_low": round(mean(lows), 1) if lows else None,
        "max_high": max(highs) if highs else None,
        "min_low": min(lows) if lows else None,
        "rain_total": round(sum(rain), 2),
        "rain_days": sum(1 for r in rain if r >= 0.01),
        "sun_hours": round(sum(d.get("sun_hours") or 0.0 for _, d in rows), 1),
    }


def change(a, b):
    """a minus b, or None when either is missing."""
    if a is None or b is None:
        return None
    return round(a - b, 2)


def typical(days: list[tuple], day: date, window: int = 7) -> dict:
    """Average high and low for the days within `window` days of this calendar date in other years."""
    def offset(d: date) -> int:
        diff = abs((date(2000, d.month, d.day) - date(2000, day.month, day.day)).days)
        return min(diff, 366 - diff)

    highs, lows, years = [], [], set()
    for d, s in days:
        if d.year == day.year or offset(d) > window:
            continue
        if s.get("tempf_max") is not None:
            highs.append(s["tempf_max"])
        if s.get("tempf_min") is not None:
            lows.append(s["tempf_min"])
        years.add(d.year)
    return {"high": round(mean(highs), 1) if highs else None,
            "low": round(mean(lows), 1) if lows else None,
            "years": len(years)}


HEAT_LEVELS = (100, 110)  # degrees Fahrenheit


def heat_days_by_year(days: list[tuple]) -> dict[int, dict[int, int]]:
    """{year: {100: days at or above 100 F, 110: days at or above 110 F}}, oldest year first."""
    out = {}
    for d, s in days:
        high = s.get("tempf_max")
        if high is None:
            continue
        counts = out.setdefault(d.year, {level: 0 for level in HEAT_LEVELS})
        for level in HEAT_LEVELS:
            if high >= level:
                counts[level] += 1
    return dict(sorted(out.items()))


def by_this_time(today: list[dict], yesterday: list[dict]) -> dict:
    """Highest temperature, rain so far and highest gust, today and yesterday over the same hours: {key: (today, yesterday)}."""
    def top(rows, key):
        values = [r[key] for r in rows if r.get(key) is not None]
        return max(values) if values else None

    return {key: (top(today, key), top(yesterday, key)) for key in ("tempf", "dailyrainin", "windgustmph")}


def _degrees(change: float, metric: bool) -> str:
    return f"{change * 5 / 9:+.0f} °C" if metric else f"{change:+.0f} °F"


def unusual(day: date, summary: dict, days: list[tuple], threshold: float = 10.0, heavy_rain: float = 1.0,
            metric: bool = False) -> list[str]:
    """Why this day stands out: a high or low at least `threshold` degrees from the usual value for the date
    (needs two other years of data), or heavy rain. Empty when it is ordinary."""
    reasons = []
    usual = typical(days, day)
    if usual["years"] >= 2:
        if summary.get("tempf_max") is not None and usual["high"] is not None:
            change = summary["tempf_max"] - usual["high"]
            if abs(change) >= threshold:
                reasons.append(f"high {_degrees(change, metric)} from usual")
        if summary.get("tempf_min") is not None and usual["low"] is not None:
            change = summary["tempf_min"] - usual["low"]
            if abs(change) >= threshold:
                reasons.append(f"low {_degrees(change, metric)} from usual")
    rain = summary.get("rain_in") or 0.0
    if rain >= heavy_rain:
        reasons.append(f"{rain * 25.4:.1f} mm of rain" if metric else f"{rain:.2f} in of rain")
    return reasons
