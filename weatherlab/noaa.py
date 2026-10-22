"""NOAA daily history for the nearest weather station, from Climate Data Online (a free token is needed).

The token is kept in Windows Credential Manager. Values come in US units: rain in inches, temperatures in °F.
NOAA's data is kept apart from the app's own daily summaries; it is used where the app has no history.
"""

import json
import math
from datetime import date
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from weatherlab import secrets

BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"
TOKEN_KEY = "noaa_token"
ELEMENTS = {"PRCP": "rain_in", "TMAX": "tempf_max", "TMIN": "tempf_min"}
PAGE = 1000  # the most rows NOAA returns for one request
TIMEOUT_S = 30


class NoaaError(Exception):
    """NOAA couldn't be reached, or didn't accept the token."""


def _get(path: str, params: dict, token: str) -> dict:
    url = f"{BASE}/{path}?{urlencode(params, doseq=True)}"
    request = Request(url, headers={"token": token, "User-Agent": "WeatherLab"})
    try:
        with urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise NoaaError("NOAA didn't accept the token. Check it on the NOAA Climate Data Online website.") from exc
        raise NoaaError(f"NOAA returned an error ({exc.code}).") from exc
    except (OSError, ValueError) as exc:
        raise NoaaError(f"Couldn't reach NOAA ({type(exc).__name__}).") from exc


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_station(results: list[dict], lat: float, lon: float):
    """(station id, name, km) for the station closest to the point, from NOAA's station list. None if there are none."""
    best = None
    for item in results or []:
        try:
            slat, slon = float(item["latitude"]), float(item["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        km = distance_km(lat, lon, slat, slon)
        if best is None or km < best[2]:
            best = (item.get("id", ""), item.get("name", ""), km)
    return best


def find_station(lat: float, lon: float, token: str):
    """The nearest GHCND station to a point, or None when NOAA has none nearby."""
    box = 0.5  # degrees, about 55 km
    data = _get("stations", {"datasetid": "GHCND", "extent": f"{lat - box},{lon - box},{lat + box},{lon + box}",
                             "limit": 1000}, token)
    return nearest_station(data.get("results") or [], lat, lon)


def parse_daily(items: list[dict]) -> dict:
    """NOAA daily rows -> {"2026-01-05": {"rain_in": 0.1, "tempf_max": 70.0, ...}}. Unknown elements are ignored."""
    days: dict = {}
    for item in items or []:
        key = ELEMENTS.get(item.get("datatype"))
        day = str(item.get("date", ""))[:10]
        if key is None or len(day) != 10 or item.get("value") is None:
            continue
        days.setdefault(day, {"source": "noaa"})[key] = round(float(item["value"]), 2)
    return days


def fetch_daily(station_id: str, start: date, end: date, token: str) -> dict:
    """NOAA daily values for a station between two dates, a year at a time, all pages included."""
    days: dict = {}
    year = start.year
    while year <= end.year:
        first = max(start, date(year, 1, 1))
        last = min(end, date(year, 12, 31))
        offset = 1
        while True:
            params = {"datasetid": "GHCND", "stationid": station_id, "startdate": first.isoformat(),
                      "enddate": last.isoformat(), "datatypeid": list(ELEMENTS), "units": "standard",
                      "limit": PAGE, "offset": offset}
            data = _get("data", params, token)
            days.update(parse_daily(data.get("results") or []))
            count = int((data.get("metadata") or {}).get("resultset", {}).get("count", 0))
            if offset + PAGE > count:
                break
            offset += PAGE
        year += 1
    return days


def token() -> str:
    return secrets.get_key(TOKEN_KEY)
