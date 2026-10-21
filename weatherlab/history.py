"""Queries for the Daily, History, and Records pages."""

import csv
import io
import json
from datetime import date, timedelta

# Records to show: (daily key, label, "max" or "min", unit)
RECORD_ITEMS = [
    ("tempf_max", "Highest temperature", "max", "°F"),
    ("tempf_min", "Lowest temperature", "min", "°F"),
    ("gust_max", "Highest gust", "max", " mph"),
    ("wind_max", "Highest sustained wind", "max", " mph"),
    ("rain_in", "Most rain in a day", "max", " in"),
    ("rainrate_max", "Fastest rain rate", "max", " in/hr"),
    ("humidity_max", "Most humid day", "max", "%"),
    ("humidity_min", "Least humid day", "min", "%"),
    ("sun_hours", "Most sun hours", "max", " h"),
]


# Daily summary key -> the reading it summarises, so the app can show it in the chosen units.
RECORD_UNIT = {"tempf_max": "tempf", "tempf_min": "tempf", "gust_max": "windgustmph",
               "wind_max": "windspeedmph", "rain_in": "dailyrainin", "rainrate_max": "rainratein"}


def daily_between(db, start: date, end: date) -> list[tuple[date, dict]]:
    rows = db.execute("SELECT date, data FROM daily WHERE date >= ? AND date <= ? ORDER BY date",
                      (start.isoformat(), end.isoformat())).fetchall()
    return [(date.fromisoformat(d), json.loads(data)) for d, data in rows]


def all_daily(db) -> list[tuple[date, dict]]:
    rows = db.execute("SELECT date, data FROM daily ORDER BY date").fetchall()
    return [(date.fromisoformat(d), json.loads(data)) for d, data in rows]


def records(db) -> list[dict]:
    """For each record item: the best value and the day it happened. Empty list if no daily data yet."""
    days = all_daily(db)
    out = []
    for key, label, kind, unit in RECORD_ITEMS:
        found = [(d[key], day, bool(d.get("estimated"))) for day, d in days if d.get(key) is not None]
        if not found:
            continue
        value, day, estimated = max(found) if kind == "max" else min(found)
        out.append({"key": key, "label": label, "value": value, "unit": unit, "date": day, "estimated": estimated})
    return out


def rain_totals(db, today: date, live_today_in: float | None) -> dict[str, float]:
    """Rain totals in inches: today, the last 7 days, this month, and this year.
    Today comes from the live gauge; earlier days come from the daily summaries."""
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)
    days = all_daily(db)

    def total(start: date) -> float:
        return round(sum(d.get("rain_in", 0.0) for day, d in days if start <= day < today), 2)

    now = live_today_in or 0.0
    return {
        "today": round(now, 2),
        "last_7_days": round(total(week_start) + now, 2),
        "this_month": round(total(month_start) + now, 2),
        "this_year": round(total(year_start) + now, 2),
    }


def same_day_before(days: list[tuple[date, dict]], day: date) -> list[tuple[date, dict]]:
    """Summaries for the same month and day in earlier years, oldest first."""
    return sorted((d, s) for d, s in days if d.month == day.month and d.day == day.day and d.year < day.year)


def daily_csv(rows: list[tuple[date, dict]]) -> str:
    """One row per day in US units. Missing values are left empty."""
    keys = ["tempf_max", "tempf_min", "tempf_avg", "rain_in", "gust_max", "wind_run_mi", "sun_hours",
            "humidity_min", "humidity_max"]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["date", "high_f", "low_f", "average_f", "rain_in", "gust_max_mph", "wind_run_mi",
                     "sun_hours", "humidity_min_pct", "humidity_max_pct"])
    for day, summary in rows:
        writer.writerow([day.isoformat()] + ["" if summary.get(k) is None else summary[k] for k in keys])
    return out.getvalue()
