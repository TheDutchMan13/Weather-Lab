"""Tropical storms and hurricanes from the National Hurricane Center (NHC), measured from the station.

Adapted from the dashboard's utils/tropics.py (see SOURCES.md). The list is downloaded at most every
30 minutes, and the last good copy is kept when the NHC can't be reached.
"""

import json
import math
import time
from pathlib import Path
from urllib.request import Request, urlopen

NHC_URL = "https://www.nhc.noaa.gov/CurrentStorms.json"
KT_TO_MPH = 1.15078
TIMEOUT_S = 20
POINTS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def miles_between(a, b):
    """Great-circle distance in miles between two (latitude, longitude) pairs."""
    la1, lo1 = map(math.radians, a)
    la2, lo2 = map(math.radians, b)
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def bearing(home, point):
    """Direction from home to point, in degrees clockwise from north."""
    p1, p2 = math.radians(home[0]), math.radians(point[0])
    dl = math.radians(point[1] - home[1])
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


def compass(deg):
    if deg is None:
        return ""
    return POINTS[int(((deg % 360) + 22.5) // 45) % 8]


def parse(raw, home):
    """Rows sorted nearest first. Storms without a position are skipped; missing values stay None."""
    out = []
    for s in (raw or {}).get("activeStorms", []) or []:
        lat, lon = _num(s.get("latitudeNumeric")), _num(s.get("longitudeNumeric"))
        if lat is None or lon is None:
            continue
        kt = _num(s.get("intensity"))
        mdir, mspd = _num(s.get("movementDir")), _num(s.get("movementSpeed"))
        out.append({
            "name": str(s.get("name") or s.get("id") or "Unnamed"),
            "class": str(s.get("classification") or ""),
            "wind_mph": round(kt * KT_TO_MPH) if kt is not None else None,
            "miles": round(miles_between(home, (lat, lon))),
            "direction": compass(bearing(home, (lat, lon))),
            "move": f"{compass(mdir)} at {round(mspd)} mph" if mspd is not None else compass(mdir),
            "move_dir": compass(mdir),
            "move_mph": round(mspd) if mspd is not None else None,
            "lat": lat, "lon": lon,
            "updated": str(s.get("lastUpdate") or ""),
        })
    return sorted(out, key=lambda r: r["miles"])


def _download():
    req = Request(NHC_URL, headers={"User-Agent": "WeatherLab/0.1"})
    with urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def read_cache(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def refresh(home, path, min_minutes=30, fetch=None):
    """Downloads the storm list if the saved copy is older than min_minutes. Returns the saved copy either way."""
    cache = read_cache(path)
    if cache.get("checked_ts") and time.time() - cache["checked_ts"] < min_minutes * 60:
        return cache
    checked = {"checked_ts": time.time(), "checked": time.strftime("%Y-%m-%d %H:%M")}
    try:
        raw = fetch() if fetch else _download()
        cache = {**checked, "ok": True, "storms": parse(raw, home), "error": ""}
    except (OSError, ValueError) as exc:
        cache = {**cache, **checked, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return cache
