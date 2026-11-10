"""Place search for the setup wizard (0.37.60): a town, city or ZIP code to latitude, longitude, time zone and
elevation, from Open-Meteo's free geocoding service. Only the typed place name is sent. No key needed."""

import json
import urllib.parse
import urllib.request

from weatherlab import plain_errors
from weatherlab.config import APP_VERSION

URL = "https://geocoding-api.open-meteo.com/v1/search"


class GeocodeError(Exception):
    pass


def parse(raw: str) -> list[dict]:
    """The places in an Open-Meteo answer, each with a label, lat, lon, timezone and elevation (meters or None)."""
    out = []
    for r in json.loads(raw).get("results") or []:
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        parts = [r.get("name"), r.get("admin1"), r.get("country")]
        label = ", ".join(dict.fromkeys(p for p in parts if p))
        elev = r.get("elevation")
        out.append({"label": label or f"{lat:.2f}, {lon:.2f}", "lat": round(lat, 5), "lon": round(lon, 5),
                    "timezone": r.get("timezone") or "", "elevation": float(elev) if isinstance(elev, (int, float)) else None})
    return out


def search(name: str, timeout: float = 8.0) -> list[dict]:
    name = name.strip()
    if not name:
        return []
    query = urllib.parse.urlencode({"name": name, "count": 6, "language": "en", "format": "json"})
    req = urllib.request.Request(f"{URL}?{query}", headers={"User-Agent": f"WeatherLab/{APP_VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return parse(resp.read(200000).decode("utf-8", "replace"))
    except (OSError, ValueError) as exc:
        raise GeocodeError(plain_errors.service("the place search", exc)) from exc
