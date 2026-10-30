"""Lightning from the GW2000's live data.

Based on the dashboard's collectors/gw2000_collector.py parse_lightning (see SOURCES.md).
The station labels distances "mi", but some firmware reports kilometres. The Settings page
has a switch for that, because the dashboard's station needed it.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

from weatherlab.parse import split_val


def parse_lightning(live: dict, tz: ZoneInfo, now: datetime, value_is_km: bool) -> dict | None:
    """The last strike the gateway remembers, or None. Returns ts, distance in miles, and strikes today."""
    try:
        item = (live.get("lightning") or [None])[0]
        if not item:
            return None
        dist, unit = split_val({"val": item.get("distance", "")})
        when = datetime.fromisoformat(str(item.get("date", "")))
        if dist is None or when.year < 2000 or dist < 0 or dist > 1000:
            return None
        when = when.replace(tzinfo=tz)
        miles = dist * 0.621371 if (value_is_km or unit.lower().startswith("km")) else dist
        count = int(float(item.get("count", 0) or 0))
        return {"ts": int(when.timestamp()), "distance_mi": round(miles, 3),
                "today": count if when.date() == now.date() else 0}
    except (ValueError, TypeError):
        return None
