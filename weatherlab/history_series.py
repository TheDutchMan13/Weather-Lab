"""Thins a history of readings to one point per time bucket, and sums it up, for the history windows. No Streamlit here,
so it can be tested on its own."""


def thin(points: list[tuple[float, float]], bucket_s: int = 600) -> list[tuple[float, float]]:
    """One point per bucket: the latest reading in each bucket wins. points are (timestamp, value) in time order."""
    out: list[tuple[float, float]] = []
    last = None
    for ts, value in points:
        bucket = int(ts // bucket_s)
        if bucket == last:
            out[-1] = (ts, value)
        else:
            out.append((ts, value))
            last = bucket
    return out


def summary(points: list[tuple[float, float]]) -> dict | None:
    """Highest, lowest and average value, with the highest and lowest times. None when there are no points."""
    if not points:
        return None
    high = max(points, key=lambda p: p[1])
    low = min(points, key=lambda p: p[1])
    return {"high": high, "low": low, "average": sum(v for _, v in points) / len(points)}
