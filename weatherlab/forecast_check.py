"""Forecast accuracy: the high the forecast gave for each day, compared with the high that happened."""

from datetime import date, datetime, timedelta
from statistics import mean


def highs_from_periods(periods: list[dict], tz) -> dict[str, float]:
    """Daytime high for each date, in Fahrenheit, from the NWS daily forecast periods."""
    out = {}
    for p in periods:
        if not p.get("isDaytime") or p.get("temperature") is None or not p.get("start"):
            continue
        temp = float(p["temperature"])
        if str(p.get("unit", "F")).upper() == "C":
            temp = temp * 9 / 5 + 32
        day = datetime.fromisoformat(p["start"]).astimezone(tz).date().isoformat()
        out[day] = round(temp, 1)
    return out


def compare(forecasts: dict[date, float], actuals: dict[date, float]) -> list[tuple[date, float, float, float]]:
    """(day, forecast high, actual high, forecast minus actual) for days that have both, newest first."""
    rows = [(d, forecasts[d], actuals[d], round(forecasts[d] - actuals[d], 1))
            for d in sorted(forecasts) if d in actuals]
    return list(reversed(rows))


def accuracy(rows: list[tuple]) -> dict:
    """Average miss (ignoring direction) and bias (positive means the forecast ran high)."""
    if not rows:
        return {"days": 0, "mae": None, "bias": None}
    diffs = [r[3] for r in rows]
    return {"days": len(rows), "mae": round(mean(abs(x) for x in diffs), 1), "bias": round(mean(diffs), 1)}


def frost_nights(periods: list[dict], tz, now: datetime, threshold_f: float, hours: int = 36) -> list[tuple[str, float]]:
    """Nights whose forecast low is at or below the threshold and that start within the next `hours`.
    Returns (date the night starts, low in Fahrenheit). now must be timezone-aware."""
    out = []
    for p in periods:
        if p.get("isDaytime") or p.get("temperature") is None or not p.get("start"):
            continue
        start = datetime.fromisoformat(p["start"]).astimezone(tz)
        if not (now - timedelta(hours=12) <= start <= now + timedelta(hours=hours)):
            continue
        low = float(p["temperature"])
        if str(p.get("unit", "F")).upper() == "C":
            low = low * 9 / 5 + 32
        if low <= threshold_f:
            out.append((start.date().isoformat(), round(low, 1)))
    return out


def pops_from_periods(periods: list[dict], tz) -> dict[str, float]:
    """Daytime chance of rain (percent) for each date, from the NWS daily forecast."""
    out = {}
    for p in periods:
        if not p.get("isDaytime") or p.get("pop") is None or not p.get("start"):
            continue
        day = datetime.fromisoformat(p["start"]).astimezone(tz).date().isoformat()
        out[day] = float(p["pop"])
    return out


def combine(highs: dict[str, float], pops: dict[str, float]) -> dict[str, dict]:
    """One stored forecast per date: the high and the chance of rain."""
    return {day: {"high": high, "pop": pops.get(day)} for day, high in highs.items()}


def rain_summary(pops: dict, rained: dict) -> dict:
    """Forecast chance of 50% or more ('wet') against under 50% ('dry'), and how often it actually rained (0.01 in or more)."""
    out = {"wet_days": 0, "wet_rained": 0, "dry_days": 0, "dry_rained": 0}
    for day, chance in pops.items():
        if day not in rained or chance is None:
            continue
        kind = "wet" if chance >= 50 else "dry"
        out[f"{kind}_days"] += 1
        if rained[day]:
            out[f"{kind}_rained"] += 1
    return out
