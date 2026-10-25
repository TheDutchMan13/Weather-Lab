"""National Weather Service alerts and forecasts. No API key is needed.

The NWS asks every app to identify itself in the User-Agent header, so the user's
optional contact email from Setup is included.

Alert colors come from the dashboard's utils/alert_cards.py SEV table (see SOURCES.md).
The forecast URLs come from the NWS /points endpoint for the user's own location,
not from the dashboard's hardcoded grid point.
"""

import json
import math
from urllib.request import Request, urlopen

BASE = "https://api.weather.gov"
TIMEOUT_S = 10

SEVERITY_ORDER = ["Extreme", "Severe", "Moderate", "Minor", "Unknown"]
SEVERITY_COLORS = {  # accent color per NWS severity, from the dashboard's SEV table
    "Extreme": "#d92d20",
    "Severe": "#e8590c",
    "Moderate": "#f08c00",
    "Minor": "#2f9e44",
    "Unknown": "#6b7280",
}


class NwsError(Exception):
    """The National Weather Service couldn't be reached or sent data we can't read."""


def _get(url: str, contact: str) -> dict:
    agent = f"WeatherLab/0.1 ({contact.strip() or 'contact not set'})"
    req = Request(url, headers={"User-Agent": agent, "Accept": "application/geo+json"})
    try:
        with urlopen(req, timeout=TIMEOUT_S) as response:
            return json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise NwsError(f"Couldn't reach the National Weather Service ({type(exc).__name__}).") from exc


def points(lat: float, lon: float, contact: str) -> dict:
    """Forecast URLs and zone for a location."""
    data = _get(f"{BASE}/points/{lat:.4f},{lon:.4f}", contact)
    p = data.get("properties") or {}
    if "forecast" not in p:
        raise NwsError("The National Weather Service doesn't cover this location.")
    return {"forecast": p["forecast"], "forecastHourly": p.get("forecastHourly", ""),
            "zone": str(p.get("forecastZone", "")).rsplit("/", 1)[-1],
            "radar": p.get("radarStation") or "",
            "stations": p.get("observationStations") or ""}


def alerts(lat: float, lon: float, contact: str) -> list[dict]:
    """Active alerts for a location, most severe first."""
    data = _get(f"{BASE}/alerts/active?point={lat:.4f},{lon:.4f}", contact)
    out = []
    for feature in data.get("features", []):
        p = feature.get("properties") or {}
        sev = p.get("severity") or "Unknown"
        out.append({
            "event": p.get("event", "Alert"),
            "headline": p.get("headline") or "",
            "severity": sev if sev in SEVERITY_ORDER else "Unknown",
            "expires": p.get("expires") or "",
            "description": p.get("description") or "",
            "ugc": list((p.get("geocode") or {}).get("UGC") or []),
            "area": p.get("areaDesc") or "",
        })
    out.sort(key=lambda a: SEVERITY_ORDER.index(a["severity"]))
    return out


def _rings(geometry) -> list:
    """Outer outline rings (lon, lat) from a GeoJSON Polygon or MultiPolygon. Holes are ignored."""
    geometry = geometry or {}
    kind, coords = geometry.get("type"), geometry.get("coordinates") or []
    if kind == "Polygon" and coords:
        return [coords[0]]
    if kind == "MultiPolygon":
        return [poly[0] for poly in coords if poly]
    return []


def zone_rings(zone: str, contact: str) -> list:
    """Outline rings for a forecast zone (such as AZZ512) or a county (such as AZC013). Empty when there is none."""
    kind = "county" if len(zone) > 2 and zone[2] == "C" else "forecast"
    return _rings(_get(f"{BASE}/zones/{kind}/{zone}", contact).get("geometry"))


def forecast_daily(url: str, contact: str) -> list[dict]:
    """Up to 14 day and night periods (7 days)."""
    periods = (_get(url, contact).get("properties") or {}).get("periods") or []
    return [{
        "name": p.get("name", ""),
        "isDaytime": bool(p.get("isDaytime")),
        "temperature": p.get("temperature"),
        "unit": p.get("temperatureUnit", "F"),
        "wind": p.get("windSpeed", ""),
        "short": p.get("shortForecast", ""),
        "detail": p.get("detailedForecast", ""),
        "pop": (p.get("probabilityOfPrecipitation") or {}).get("value"),
        "start": p.get("startTime", ""),
    } for p in periods[:14]]


def forecast_hourly(url: str, contact: str, limit: int = 48) -> list[dict]:
    """Up to `limit` hours. Humidity and wind are included for the fire weather index."""
    periods = (_get(url, contact).get("properties") or {}).get("periods") or []
    return [{
        "start": p.get("startTime", ""),
        "temperature": p.get("temperature"),
        "unit": p.get("temperatureUnit", "F"),
        "short": p.get("shortForecast", ""),
        "pop": (p.get("probabilityOfPrecipitation") or {}).get("value"),
        "humidity": (p.get("relativeHumidity") or {}).get("value"),
        "wind": p.get("windSpeed", ""),
    } for p in periods[:limit]]


COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
AIRPORT_WORDS = ("airport", "international", "intl", "regional", "airfield")
AIRPORT_MAX_KM = 80  # an airport station counts as nearby within this distance


def compass(degrees) -> str:
    """A wind direction in degrees as a point of the compass, such as "SW". Empty when there is no direction."""
    if degrees is None:
        return ""
    return COMPASS[int((float(degrees) % 360) / 22.5 + 0.5) % 16]


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def nearest_airport_station(url: str, lat: float, lon: float, contact: str) -> dict | None:
    """The observation station to use for a point: the nearest airport within AIRPORT_MAX_KM, otherwise the
    nearest station of any kind. url is the observationStations link from /points."""
    rows = []
    for feature in _get(url, contact).get("features", []):
        p = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        station_id = p.get("stationIdentifier")
        if not station_id or len(coords) < 2:
            continue
        name = p.get("name") or station_id
        rows.append({"id": station_id, "name": name,
                     "km": _km(lat, lon, float(coords[1]), float(coords[0])),
                     "airport": any(word in name.lower() for word in AIRPORT_WORDS)})
    if not rows:
        return None
    airports = [r for r in rows if r["airport"] and r["km"] <= AIRPORT_MAX_KM]
    return min(airports or rows, key=lambda r: r["km"])


def _value(p: dict, key: str):
    value = (p.get(key) or {}).get("value")
    return None if value is None else float(value)


def parse_observation(data: dict) -> dict:
    """A station's latest observation in US units: temperature in °F, wind in mph, humidity in %."""
    p = data.get("properties") or {}
    celsius = _value(p, "temperature")
    kmh, gust = _value(p, "windSpeed"), _value(p, "windGust")
    vis = _value(p, "visibility")  # metres
    return {
        "time": p.get("timestamp") or "",
        "text": p.get("textDescription") or "",
        "temp_f": None if celsius is None else celsius * 9 / 5 + 32,
        "humidity": _value(p, "relativeHumidity"),
        "wind_mph": None if kmh is None else kmh / 1.609344,
        "gust_mph": None if gust is None else gust / 1.609344,
        "direction": _value(p, "windDirection"),
        "visibility_mi": None if vis is None else vis / 1609.344,
        "present": [w.get("weather") or w.get("rawString") or "" for w in (p.get("presentWeather") or []) if isinstance(w, dict)],
    }


def latest_observation(station_id: str, contact: str) -> dict:
    """The latest reading from one observation station."""
    return parse_observation(_get(f"{BASE}/stations/{station_id}/observations/latest", contact))
