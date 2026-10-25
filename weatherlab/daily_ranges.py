"""The ranges on the Daily page: one day (with a date box), or several days together.

Kept apart from the screens so the choices can be tested without the page's dependencies."""

DAY_VIEW = "day"  # the one-day view: a date box, that day's readings and its PDF
DAILY_RANGES = {"1 day": DAY_VIEW, "7 days": 7, "30 days": 30, "All": None}  # several days: the number of days, None = all time


def is_day_view(choice: str) -> bool:
    return DAILY_RANGES[choice] == DAY_VIEW
