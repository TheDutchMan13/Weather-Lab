"""National Weather Service alerts and forecasts. No API key is needed.

The NWS asks every app to identify itself in the User-Agent header, so the user's
optional contact email from Setup is included.

Alert colors come from the dashboard's utils/alert_cards.py SEV table (see SOURCES.md).
The forecast URLs come from the NWS /points endpoint for the user's own location,
not from the dashboard's hardcoded grid point.
"""

import json
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
            "radar": p.get("radarStation") or ""}


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
