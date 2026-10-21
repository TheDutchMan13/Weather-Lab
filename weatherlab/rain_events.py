"""Rain events: rain grouped into separate showers.

The daily rain total starts again at midnight, so a drop in the total is treated as a new day, not as negative rain.
"""

GAP_SECONDS = 1800  # this long with no rain and the next rain starts a new event


def events(rows: list[tuple], gap_seconds: float = GAP_SECONDS) -> list[dict]:
    """rows: [(timestamp, reading)] in time order. Returns events with start, end, inches and peak_rate (in/hr)."""
    out, current, previous = [], None, None
    for ts, reading in rows:
        daily = reading.get("dailyrainin")
        if daily is None:
            continue
        rate = reading.get("rainratein") or 0.0
        if previous is None:
            step = 0.0
        else:
            step = daily - previous if daily >= previous else daily
        previous = daily
        if step <= 0 and rate <= 0:
            continue
        if current is not None and ts - current["end"] <= gap_seconds:
            current["end"] = ts
            current["inches"] += step
            current["peak_rate"] = max(current["peak_rate"], rate)
        else:
            if current is not None:
                out.append(current)
            current = {"start": ts, "end": ts, "inches": step, "peak_rate": rate}
    if current is not None:
        out.append(current)
    for event in out:
        event["inches"] = round(event["inches"], 2)
    return out
