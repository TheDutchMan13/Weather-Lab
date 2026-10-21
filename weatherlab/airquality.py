"""Air quality from the EPA's AirNow API, for the user's location and their own API key.

Based on the dashboard's import_airnow.py (fetch_aqi). The key is never written to a file;
it lives in Windows Credential Manager (see secrets.py).
"""

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://www.airnowapi.org/aq/observation/current/ziplatlong/"
TIMEOUT_S = 10

# AirNow category name -> RISK_COLORS key in config.py
CATEGORY_TO_RISK = {
    "Good": "good",
    "Moderate": "moderate",
    "Unhealthy for Sensitive Groups": "unhealthy_sensitive",
    "Unhealthy": "unhealthy",
    "Very Unhealthy": "very_unhealthy",
    "Hazardous": "hazardous",
}

POLLUTANTS = {"PM2.5": "pm25_aqi", "PM10": "pm10_aqi", "OZONE": "ozone_aqi",
              "NO2": "no2_aqi", "SO2": "so2_aqi", "CO": "co_aqi"}


class AirNowError(Exception):
    """AirNow couldn't be reached, the key was refused, or the reply can't be read."""


def fetch(lat: float, lon: float, api_key: str) -> dict | None:
    """Current air quality at a location: the highest AQI across pollutants, plus each pollutant."""
    query = urlencode({"latitude": lat, "longitude": lon, "format": "application/json", "api_key": api_key})
    req = Request(f"{BASE}?{query}", headers={"Accept": "application/json"})
    try:
        with urlopen(req, timeout=TIMEOUT_S) as response:
            records = json.loads(response.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        raise AirNowError(f"Couldn't reach AirNow ({type(exc).__name__}).") from exc
    if not isinstance(records, list):
        raise AirNowError("AirNow refused the request. Check the API key on Setup.")
    if not records:
        return None

    best, category = 0, "Unknown"
    pollutants = {}
    for r in records:
        value = int(r.get("nowcastAQI") or 0)
        if value > best:
            best, category = value, r.get("aqiCategoryName", "Unknown")
        key = POLLUTANTS.get(r.get("parameterName", ""))
        if key:
            pollutants[key] = value
    return {
        "aqi": best,
        "category": category,
        "risk": CATEGORY_TO_RISK.get(category, "good"),
        "station": records[0].get("reportingAreaName", ""),
        **pollutants,
    }
