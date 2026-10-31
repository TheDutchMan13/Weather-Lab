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


def compare_years(days: list, year: int, hot_f: float = 100.0, freeze_f: float = 32.0) -> dict | None:
    """A year next to the one before (0.37.54): each total as (this year, last year, change), plus how many days of
    data each year has, so a short year can be flagged. None when the year before has no data.

    While the year is still going, last year is cut to the same dates (January 1 to the last day with data this year),
    so October's totals are compared with last year's up to October, not with the whole year. "through" says the last
    date compared, or None when the whole of both years is compared."""
    this_year = [d for d, _ in days if d.year == year]
    through = max(this_year) if this_year else None
    if through is not None and (through.month, through.day) == (12, 31):
        through = None
    before_days = [(d, s) for d, s in days if d.year != year - 1 or through is None
                   or (d.month, d.day) <= (through.month, through.day)]
    now, before = year_summary(days, year, hot_f, freeze_f), year_summary(before_days, year - 1, hot_f, freeze_f)
    if not now or not before:
        return None

    def pair(key: str) -> tuple:
        a, b = now[key], before[key]
        return a, b, round(a - b, 2)

    def peak(key: str) -> tuple:
        a, b = now[key], before[key]
        if not a or not b:
            return a, b, None
        return a, b, round(a[1] - b[1], 1)

    return {"rain": pair("rain"), "rainy_days": pair("rainy_days"), "hot_days": pair("hot_days"),
            "freezing": pair("freezing"), "hottest": peak("hottest"), "coldest": peak("coldest"),
            "days": (now["days"], before["days"]), "through": through}


def month_extremes(days: list, year: int, min_days: int = 20) -> dict:
    """The wettest, driest, warmest and coolest months of a year (0.37.54), as {name: (month, value)}. Months with
    fewer than min_days days of data are left out, so a half-recorded month can't be the 'driest'. Temperatures are
    the average of the daily averages; rain is the month's total."""
    months = {m: v for m, v in monthly(days).get(year, {}).items() if v["days"] >= min_days}
    out = {}
    if months:
        out["wettest"] = max(((m, v["rain"]) for m, v in months.items()), key=lambda x: x[1])
        out["driest"] = min(((m, v["rain"]) for m, v in months.items()), key=lambda x: x[1])
    temps = [(m, v["temp"]) for m, v in months.items() if v["temp"] is not None]
    if temps:
        out["warmest"] = max(temps, key=lambda x: x[1])
        out["coolest"] = min(temps, key=lambda x: x[1])
    return out


def year_announcement(summary: dict | None, year: int, rain_text: str, hottest_text: str | None) -> str | None:
    """The phone notice sent in January once last year's report is made (0.37.54). The values come in already
    formatted in the chosen units."""
    if not summary:
        return None
    parts = [f"Your {year} weather year is ready: {rain_text} of rain on {summary['rainy_days']} days"]
    if summary.get("hottest") and hottest_text:
        parts.append(f"hottest {hottest_text} on {summary['hottest'][0].strftime('%b %d').replace(' 0', ' ')}")
    return ", ".join(parts) + ". See History, Year."
