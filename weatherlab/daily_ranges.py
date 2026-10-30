"""The periods on the History page (0.37.50) and the two ranges on its Daily view.

One Period control at the top of History sets how far back Records, Rankings, Coverage and Daily's several-days view
look. Daily still has its one-day view with a date box. Kept apart from the screens so the choices can be tested
without the page's dependencies."""
from datetime import date, timedelta

DAY_VIEW = "day"  # the one-day view: a date box, that day's readings and its PDF
PERIOD_VIEW = "period"  # several days together, as many as the Period control says
DAILY_RANGES = {"1 day": DAY_VIEW, "Several days": PERIOD_VIEW}

# The Period control at the top of History: the number of days back, None = all time.
HISTORY_PERIODS = {"7 days": 7, "30 days": 30, "90 days": 90, "1 year": 365, "All": None}
DEFAULT_PERIOD = "All"
PERIOD_VIEWS = ("Records", "Rankings", "Coverage")  # plus Daily when it shows several days


def is_day_view(choice: str) -> bool:
    return DAILY_RANGES.get(choice) == DAY_VIEW


def period_days(choice) -> int | None:
    """The number of days for a Period choice; an unknown or empty choice falls back to the default (all time)."""
    return HISTORY_PERIODS.get(choice or DEFAULT_PERIOD, HISTORY_PERIODS[DEFAULT_PERIOD])


def shows_period(view: str, daily_range: str | None) -> bool:
    """Whether the Period control applies to this History view."""
    return view in PERIOD_VIEWS or (view == "Daily" and not is_day_view(daily_range or "1 day"))


def in_period(days: list, n: int | None, today: date) -> list:
    """The (date, summary) pairs from the last n days before today; all of them when n is None."""
    if n is None:
        return list(days)
    start = today - timedelta(days=n)
    return [(d, s) for d, s in days if d >= start]
