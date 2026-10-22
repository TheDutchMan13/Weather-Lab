"""Regional wind: a grid of points around the station, with wind now and later, from Open-Meteo (no key needed).

The grid is centred on the station, so its middle point is the station. Results are kept for an hour in the station's
folder, so the page doesn't ask Open-Meteo every time it opens.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weatherlab import stations

BASE = "https://api.open-meteo.com/v1/forecast"
ROWS, COLS = 5, 7  # the grid; odd numbers keep the station in the middle
STEP = 0.2  # degrees between points: about 22 km north to south
CACHE_S = 3600
TIMEOUT_S = 20
TIMES = {"Now": 0, "+3 h": 3, "+6 h": 6, "+12 h": 12}  # the choices on the page, and hours ahead
BANDS = [(5, "#c6dbef", "0–5"), (10, "#6baed6", "5–10"), (15, "#2171b5", "10–15"), (20, "#fdae6b", "15–20"),
         (float("inf"), "#e6550d", "20+")]  # speed in mph: upper limit, colour, label


class WindError(Exception):
    """The wind couldn't be fetched, and nothing is saved from before."""


def grid_points(lat: float, lon: float) -> list[tuple[float, float]]:
    """Points row by row from the north-west corner."""
    return [(round(lat + (ROWS // 2 - r) * STEP, 4), round(lon + (c - COLS // 2) * STEP, 4))
            for r in range(ROWS) for c in range(COLS)]


def band(speed_mph: float | None) -> int:
    """Index into BANDS for a speed in mph. Missing speeds count as the calmest band."""
    value = speed_mph or 0.0
    for i, (upper, _, _) in enumerate(BANDS):
        if value < upper:
            return i
    return len(BANDS) - 1


def toward(direction_deg: float | None) -> float:
    """Arrows point where the wind goes: the direction it comes from, turned around."""
    return ((direction_deg or 0.0) + 180.0) % 360.0


def url_for(points: list[tuple[float, float]]) -> str:
    query = urlencode({"latitude": ",".join(str(p[0]) for p in points),
                       "longitude": ",".join(str(p[1]) for p in points),
                       "hourly": "wind_speed_10m,wind_direction_10m", "wind_speed_unit": "mph",
                       "timezone": "auto", "forecast_days": 2})
    return f"{BASE}?{query}"


def frames_from(data, now_local: str) -> dict:
    """Open-Meteo's answer -> {"0": [(speed mph, direction), ...], "3": [...], ...}, one list of points per time.
    now_local is the current hour in the station's time zone, like 2026-10-22T08:00."""
    locations = data if isinstance(data, list) else [data]
    frames: dict = {str(hours): [] for hours in TIMES.values()}
    for loc in locations:
        hourly = loc.get("hourly") or {}
        times = hourly.get("time") or []
        speeds = hourly.get("wind_speed_10m") or []
        dirs = hourly.get("wind_direction_10m") or []
        start = times.index(now_local) if now_local in times else 0
        for hours in TIMES.values():
            i = min(start + hours, len(times) - 1) if times else 0
            speed = speeds[i] if i < len(speeds) else None
            direction = dirs[i] if i < len(dirs) else None
            frames[str(hours)].append((speed, direction))
    return frames


def _path() -> Path:
    return stations.folder() / "wind_grid.json"


def _fetch(points: list[tuple[float, float]], now_local: str) -> dict:
    request = Request(url_for(points), headers={"User-Agent": "WeatherLab"})
    try:
        with urlopen(request, timeout=TIMEOUT_S) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise WindError(f"Couldn't reach the wind service ({type(exc).__name__}).") from exc
    return frames_from(data, now_local)


def _saved() -> dict | None:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load(lat: float, lon: float, now: float, tz) -> dict:
    """The grid's wind frames for this station: the saved copy when it is under an hour old, otherwise a fresh copy.
    If the wind service can't be reached, the last saved copy is used when there is one."""
    saved = _saved()
    if saved and saved.get("lat") == lat and saved.get("lon") == lon and now - saved.get("fetched", 0) < CACHE_S:
        return saved
    now_local = datetime.fromtimestamp(now, tz).strftime("%Y-%m-%dT%H:00")
    try:
        frames = _fetch(grid_points(lat, lon), now_local)
    except WindError:
        if saved and saved.get("lat") == lat and saved.get("lon") == lon:
            return saved
        raise
    result = {"lat": lat, "lon": lon, "fetched": now, "points": grid_points(lat, lon), "frames": frames}
    try:
        _path().parent.mkdir(parents=True, exist_ok=True)
        _path().write_text(json.dumps(result), encoding="utf-8")
    except OSError:
        pass
    return result


def arrow_html(speed: float | None, direction: float | None, size: str = "70%") -> str:
    """One arrow: its colour is the speed band, and it points where the wind goes."""
    _, colour, _ = BANDS[band(speed)]
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true" '
            f'style="transform:rotate({toward(direction):.0f}deg)"><path d="M12 2 L19 20 L12 16 L5 20 Z" '
            f'fill="{colour}" stroke="#1b4f7a" stroke-width="0.8"/></svg>')
