"""Quiet hours: a window of the day when non-urgent notifications wait. The window may cross midnight."""


def is_quiet(hour: int, start: int, end: int) -> bool:
    """True when `hour` falls inside the window from `start` up to, not including, `end`."""
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    return hour >= start or hour < end
