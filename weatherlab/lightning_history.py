"""Lightning by day: how many strikes each day, and how close the closest one was. Built from the stored strikes."""

from collections import defaultdict
from datetime import datetime


def per_day(strikes, tz) -> list[tuple]:
    """strikes: (timestamp, miles) pairs. Returns (day, count, closest miles) for each day with strikes, oldest first."""
    counts: dict = defaultdict(int)
    closest: dict = {}
    for ts, miles in strikes:
        day = datetime.fromtimestamp(ts, tz).date()
        counts[day] += 1
        closest[day] = min(miles, closest.get(day, miles))
    return [(day, counts[day], closest[day]) for day in sorted(counts)]
