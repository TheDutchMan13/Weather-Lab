"""Replay helpers: the time range of a day in a given time zone."""

from datetime import datetime, timedelta
from datetime import time as clock_time


def day_bounds(day, tz):
    """Start and end of a calendar day in tz, as Unix timestamps. The end is the start of the next day."""
    start = datetime.combine(day, clock_time(0), tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), clock_time(0), tzinfo=tz)
    return start.timestamp(), end.timestamp()
