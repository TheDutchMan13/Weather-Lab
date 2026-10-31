"""The forecast report card (0.37.54): how close the National Weather Service forecast came to what the station
recorded, for highs and lows, by how many days ahead the forecast was made.

Weather Lab saves the first forecast of each day for every day it covers (storage.forecast_ahead). Once a day has
finished, its high and low are compared with each forecast that covered it: the one from that morning (same day),
the day before (1 day ahead), and so on. No Streamlit here, so the tests run without it."""
from datetime import date, datetime, timedelta
from statistics import mean

from weatherlab.forecast_check import highs_from_periods, pops_from_periods

LEADS = (0, 1, 2, 3, 4, 5, 6)  # days ahead: 0 is the forecast made the same morning


def _f(p: dict) -> float:
    temp = float(p["temperature"])
    return temp * 9 / 5 + 32 if str(p.get("unit", "F")).upper() == "C" else temp


def lows_from_periods(periods: list[dict], tz) -> dict[str, float]:
    """Overnight low for each date, in Fahrenheit. A night's low belongs to the morning it ends on: Tonight
    (Thursday 6 pm to Friday 6 am) is Friday's low, which is when the station records it."""
    out = {}
    for p in periods:
        if p.get("isDaytime") or p.get("temperature") is None or not p.get("start"):
            continue
        if p.get("end"):
            day = datetime.fromisoformat(p["end"]).astimezone(tz).date()
        else:
            day = datetime.fromisoformat(p["start"]).astimezone(tz).date() + timedelta(days=1)
        out[day.isoformat()] = round(_f(p), 1)
    return out


def snapshot(periods: list[dict], tz) -> dict[str, dict]:
    """{date: {"high", "low", "pop"}} for every date the forecast covers. Missing parts are None."""
    highs, lows, pops = highs_from_periods(periods, tz), lows_from_periods(periods, tz), pops_from_periods(periods, tz)
    return {d: {"high": highs.get(d), "low": lows.get(d), "pop": pops.get(d)} for d in sorted({*highs, *lows})}


def pairs(saved: list[tuple], actuals: dict[date, tuple[float | None, float | None]], today: date) -> list[tuple]:
    """(days ahead, "high" or "low", forecast, actual) for every saved forecast of a finished day.

    saved: (made, date, high, low, pop) as ISO dates; actuals: {date: (high, low)} from the daily summaries. Today
    isn't finished, so it isn't graded."""
    out = []
    for made, day, high, low, _pop in saved:
        d = date.fromisoformat(day)
        lead = (d - date.fromisoformat(made)).days
        if d >= today or d not in actuals or lead not in LEADS:
            continue
        act_high, act_low = actuals[d]
        if high is not None and act_high is not None:
            out.append((lead, "high", high, act_high))
        if low is not None and act_low is not None:
            out.append((lead, "low", low, act_low))
    return out


def grade_rows(found: list[tuple], within_f: float = 3.0) -> list[dict]:
    """One row per days-ahead that has data: {"lead", "high": stats, "low": stats}. Each stats is None or
    {"days", "miss" (average miss, ignoring direction), "bias" (positive means the forecast ran warm),
    "within" (percent of days within within_f degrees F)}."""
    def stats(diffs: list[float]) -> dict | None:
        if not diffs:
            return None
        return {"days": len(diffs), "miss": round(mean(abs(x) for x in diffs), 1), "bias": round(mean(diffs), 1),
                "within": round(100 * sum(1 for x in diffs if abs(x) <= within_f + 1e-9) / len(diffs))}
    rows = []
    for lead in LEADS:
        highs = [f - a for ld, kind, f, a in found if ld == lead and kind == "high"]
        lows = [f - a for ld, kind, f, a in found if ld == lead and kind == "low"]
        if highs or lows:
            rows.append({"lead": lead, "high": stats(highs), "low": stats(lows)})
    return rows


def letter(rows: list[dict]) -> tuple[str, int, int] | None:
    """The overall grade, from the next-day forecast (1 day ahead, or same day while that's all there is): the share
    of highs and lows within the margin. A is 80% or more, B 65%, C 50%, D 35%, F below. (letter, percent, days)."""
    pick = next((r for r in rows if r["lead"] == 1), None) or next((r for r in rows if r["lead"] == 0), None)
    if pick is None:
        return None
    parts = [s for s in (pick["high"], pick["low"]) if s]
    days = sum(s["days"] for s in parts)
    pct = round(sum(s["within"] * s["days"] for s in parts) / days)
    for mark, floor in (("A", 80), ("B", 65), ("C", 50), ("D", 35)):
        if pct >= floor:
            return mark, pct, days
    return "F", pct, days


def lead_name(lead: int) -> str:
    return "Same day" if lead == 0 else "1 day ahead" if lead == 1 else f"{lead} days ahead"
