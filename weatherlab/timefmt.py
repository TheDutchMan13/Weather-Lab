"""Times on screen: 12-hour ("2:30 PM") or 24-hour ("14:30"), as chosen in Settings. Defaults to 12-hour."""

import time as _time
from datetime import datetime

_cache = [0.0, False]   # when it was read, and whether 24-hour is on


def use_24h() -> bool:
    """The Settings choice. Read from disk at most once every two seconds."""
    now = _time.monotonic()
    if now - _cache[0] > 2.0:
        try:
            from weatherlab.settings import load_settings
            _cache[1] = bool(load_settings().time_24h)
        except Exception:
            _cache[1] = False
        _cache[0] = now
    return _cache[1]


def time_text(dt: datetime, seconds: bool = False, h24: bool | None = None) -> str:
    """The time of day: "2:30 PM", "2:30:36 PM", or "14:30" / "14:30:36" in 24-hour."""
    h24 = use_24h() if h24 is None else h24
    tail = f":{dt.second:02d}" if seconds else ""
    if h24:
        return f"{dt.hour:02d}:{dt.minute:02d}{tail}"
    return f"{dt.hour % 12 or 12}:{dt.minute:02d}{tail} {'AM' if dt.hour < 12 else 'PM'}"


def stamp(dt: datetime, date_format: str = "%b %d", sep: str = ", ", seconds: bool = False, h24: bool | None = None) -> str:
    """A date and time together, such as "Oct 26, 2:30 PM"."""
    return f"{dt.strftime(date_format)}{sep}{time_text(dt, seconds, h24)}"


def hover_format(h24: bool | None = None) -> str:
    """The plotly format for a chart's hover time."""
    return "%b %d, %H:%M" if (use_24h() if h24 is None else h24) else "%b %d, %-I:%M %p"
