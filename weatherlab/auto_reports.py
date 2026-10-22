"""Automatic PDF reports: last month's report each month, and last year's in January. Each file is made once.

Files go to the reports folder beside the station's data. A report is made only when there is data for its period.
"""

from datetime import date, timedelta
from pathlib import Path

from weatherlab import stations


def folder() -> Path:
    return stations.folder() / "reports"


def monthly_name(year: int, month: int) -> str:
    return f"weather_report_{year}_{month:02d}.pdf"


def yearly_name(year: int) -> str:
    return f"weather_report_{year}.pdf"


def month_range(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    last = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    return first, last


def due(today: date, existing: set[str]) -> list[tuple[str, str, int, int]]:
    """Reports to make today, as (file name, kind, year, month). kind is "monthly" or "yearly"; yearly has month 0.
    Waits until the second day of the month, so the last day has been summarized."""
    if today.day < 2:
        return []
    out = []
    prev_year, prev_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    name = monthly_name(prev_year, prev_month)
    if name not in existing:
        out.append((name, "monthly", prev_year, prev_month))
    if today.month == 1:
        name = yearly_name(today.year - 1)
        if name not in existing:
            out.append((name, "yearly", today.year - 1, 0))
    return out
