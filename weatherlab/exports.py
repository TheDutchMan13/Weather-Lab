"""Date helpers for the Export page's downloads: the bounds of a month and the Unix times for a range of days."""

from datetime import date, datetime, timedelta


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """The first and last day of a month. February of a leap year has 29 days."""
    first = date(year, month, 1)
    next_first = date(year + (month == 12), month % 12 + 1, 1)
    return first, next_first - timedelta(days=1)


def day_start(day: date, tz) -> float:
    """The Unix time when a day starts in the given timezone."""
    return datetime.combine(day, datetime.min.time(), tzinfo=tz).timestamp()


def day_range_ts(first: date, last: date, tz) -> tuple[float, float]:
    """Unix times for the start of the first day and the start of the day after the last one (so the end is excluded)."""
    return day_start(first, tz), day_start(last + timedelta(days=1), tz)
