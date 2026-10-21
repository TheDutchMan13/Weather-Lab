"""Summaries from the daily summaries: rankings, the same date in past years, monthly climate, and a year in review.
Pure functions over (date, summary) pairs. Summaries use the stored US units (see daily.summarize_day)."""


def ranking(days: list, key: str, kind: str = "max", n: int = 10) -> list:
    """The n best days for a measure: (date, value), highest first for "max" and lowest first for "min"."""
    found = [(d, s[key]) for d, s in days if s.get(key) is not None]
    found.sort(key=lambda item: item[1], reverse=(kind == "max"))
    return found[:n]


def on_this_day(days: list, month: int, day: int) -> list:
    """(date, summary) for the same month and day in every year, oldest first."""
    return [(d, s) for d, s in days if d.month == month and d.day == day]


def monthly(days: list) -> dict:
    """{year: {month: {"temp": average of daily averages, "rain": total inches, "days": days with data}}}."""
    buckets = {}
    for d, s in days:
        b = buckets.setdefault((d.year, d.month), {"temps": [], "rain": 0.0, "days": 0})
        if s.get("tempf_avg") is not None:
            b["temps"].append(s["tempf_avg"])
        if s.get("rain_in") is not None:
            b["rain"] += s["rain_in"]
        b["days"] += 1
    out = {}
    for (year, month), b in sorted(buckets.items()):
        temp = round(sum(b["temps"]) / len(b["temps"]), 1) if b["temps"] else None
        out.setdefault(year, {})[month] = {"temp": temp, "rain": round(b["rain"], 2), "days": b["days"]}
    return out


def year_summary(days: list, year: int, hot_f: float = 100.0, freeze_f: float = 32.0):
    """Totals and record days for one year, or None when the year has no data."""
    rows = [(d, s) for d, s in days if d.year == year]
    if not rows:
        return None
    highs = [(d, s["tempf_max"]) for d, s in rows if s.get("tempf_max") is not None]
    lows = [(d, s["tempf_min"]) for d, s in rows if s.get("tempf_min") is not None]
    gusts = [(d, s["gust_max"]) for d, s in rows if s.get("gust_max") is not None]
    rains = [s["rain_in"] for _, s in rows if s.get("rain_in") is not None]
    return {
        "days": len(rows),
        "rain": round(sum(rains), 2),
        "rainy_days": sum(1 for r in rains if r > 0),
        "hottest": max(highs, key=lambda item: item[1], default=None),
        "coldest": min(lows, key=lambda item: item[1], default=None),
        "windiest": max(gusts, key=lambda item: item[1], default=None),
        "hot_days": sum(1 for _, v in highs if v >= hot_f),
        "freezing": sum(1 for _, v in lows if v <= freeze_f),
    }
