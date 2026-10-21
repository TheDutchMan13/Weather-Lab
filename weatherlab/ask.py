"""Answers simple questions about the stored daily history, using fixed patterns. Nothing is sent anywhere."""

import calendar
import re
from datetime import date

from weatherlab import units

MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_name) if number}
EXAMPLES = ("warmest day, coldest night, wettest day, wettest month, driest month, hottest month, "
            "rain in March 2026, how many days over 100")


def _temp(value: float, metric: bool) -> str:
    return units.format_value("tempf", value, metric, 0)


def _rain(value: float, metric: bool) -> str:
    return units.format_value("dailyrainin", value, metric, 2)


def _day(day: date) -> str:
    return day.strftime("%b %d, %Y")


def _month_name(year: int, month: int) -> str:
    return f"{calendar.month_name[month]} {year}"


def _monthly(days: list[tuple[date, dict]]) -> dict:
    """{(year, month): {"rain": total inches, "highs": [daily highs], "days": count}}"""
    out = {}
    for day, summary in days:
        entry = out.setdefault((day.year, day.month), {"rain": 0.0, "highs": [], "days": 0})
        entry["rain"] += summary.get("rain_in") or 0.0
        entry["days"] += 1
        if summary.get("tempf_max") is not None:
            entry["highs"].append(summary["tempf_max"])
    return out


def answer(question: str, days: list[tuple[date, dict]], today: date, metric: bool = False) -> str:
    """A short plain-language answer, or a list of the questions that can be asked."""
    q = " ".join(question.lower().split())
    if not days:
        return "There is no daily history yet."
    done = {k: v for k, v in _monthly(days).items() if k != (today.year, today.month)}  # the current month is unfinished

    m = re.search(r"rain in ([a-z]+)(?: (\d{4}))?", q)
    if m and m.group(1) in MONTHS:
        month = MONTHS[m.group(1)]
        matches = [(y, mo) for (y, mo) in _monthly(days) if mo == month and (not m.group(2) or y == int(m.group(2)))]
        if not matches:
            return f"There is no rain data for {calendar.month_name[month]}" + (f" {m.group(2)}." if m.group(2) else ".")
        year, _ = max(matches)
        entry = _monthly(days)[(year, month)]
        return (f"{_month_name(year, month)} had {_rain(entry['rain'], metric)} of rain, "
                f"across {entry['days']} days with data.")
    if "wettest month" in q and done:
        key = max(done, key=lambda k: done[k]["rain"])
        return f"The wettest month was {_month_name(*key)}, with {_rain(done[key]['rain'], metric)} of rain."
    if "driest month" in q and done:
        key = min(done, key=lambda k: done[k]["rain"])
        return f"The driest month was {_month_name(*key)}, with {_rain(done[key]['rain'], metric)} of rain."
    if ("hottest month" in q or "warmest month" in q) and done:
        scored = {k: sum(v["highs"]) / len(v["highs"]) for k, v in done.items() if v["highs"]}
        if scored:
            key = max(scored, key=scored.get)
            return (f"The warmest month on average was {_month_name(*key)}, "
                    f"with an average high of {_temp(scored[key], metric)}.")
    m = re.search(r"how many days (?:over|above|at least|reached) (\d+)", q)
    if m:
        limit = float(m.group(1))
        count = sum(1 for _, s in days if s.get("tempf_max") is not None and s["tempf_max"] >= limit)
        return f"{count} {'day' if count == 1 else 'days'} reached {limit:g} °F or higher in the stored history."
    if "warmest" in q or "hottest" in q or "highest temp" in q:
        day, s = max(((d, s) for d, s in days if s.get("tempf_max") is not None), key=lambda x: x[1]["tempf_max"])
        return f"The warmest day was {_day(day)}, with a high of {_temp(s['tempf_max'], metric)}."
    if "coldest" in q or "coolest" in q or "lowest temp" in q:
        day, s = min(((d, s) for d, s in days if s.get("tempf_min") is not None), key=lambda x: x[1]["tempf_min"])
        return f"The coldest night was {_day(day)}, with a low of {_temp(s['tempf_min'], metric)}."
    if "wettest" in q or "most rain" in q:
        day, s = max(days, key=lambda x: x[1].get("rain_in") or 0.0)
        if not s.get("rain_in"):
            return "No rain is recorded in the stored history."
        return f"The wettest day was {_day(day)}, with {_rain(s['rain_in'], metric)} of rain."
    return f"I can answer questions like: {EXAMPLES}."
