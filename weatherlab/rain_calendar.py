"""Rain calendar and yearly rain totals, from the daily rain summaries."""

import calendar
from datetime import date


def month_cells(year, month, rain):
    """Weeks of seven cells, Sunday first. A cell is None for a blank, or (day number, inches or None)."""
    weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(year, month)
    return [[None if d == 0 else (d, rain.get(date(year, month, d))) for d in week] for week in weeks]


def year_totals(rain):
    """({year: total inches}, {year: days with rain}) from {date: inches}."""
    totals, rainy = {}, {}
    for day, value in rain.items():
        if value is None:
            continue
        totals[day.year] = round(totals.get(day.year, 0.0) + value, 2)
        if value > 0:
            rainy[day.year] = rainy.get(day.year, 0) + 1
    return totals, rainy
