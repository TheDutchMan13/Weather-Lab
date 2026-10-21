"""Optional upload to Weather Underground's personal weather station network. Off by default.

Sends the latest reading to Weather Underground. The station ID and key come from your station page on
wunderground.com. The key is kept in Windows Credential Manager, never in a file, and is never shown in messages.
"""

import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from weatherlab.config import APP_VERSION

URL = "https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
TIMEOUT_S = 10
KEY_NAME = "wunderground"

# Weather Underground's field name -> the reading's field name. Readings are in US units already.
FIELDS = {
    "tempf": "tempf",
    "dewptf": "dewpointf",
    "humidity": "humidity",
    "windspeedmph": "windspeedmph",
    "windgustmph": "windgustmph",
    "winddir": "winddir",
    "baromin": "baromrelin",
    "dailyrainin": "dailyrainin",
    "solarradiation": "solarradiation",
    "UV": "uv",
}


class WuError(Exception):
    """Weather Underground couldn't be reached, or it rejected the upload."""


def values(station_id: str, key: str, reading: dict, now: datetime) -> dict:
    """The query values for one upload. Fields the station didn't report are left out."""
    out = {
        "ID": station_id,
        "PASSWORD": key,
        "action": "updateraw",
        "dateutc": now.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "softwaretype": f"WeatherLab {APP_VERSION}",
    }
    for wu_name, source in FIELDS.items():
        value = reading.get(source)
        if value is not None:
            out[wu_name] = f"{round(float(value), 2):g}"
    return out


def send_reading(station_id: str, key: str, reading: dict, now: datetime | None = None) -> None:
    """Upload one reading. Raises WuError when it can't be sent or Weather Underground says no."""
    station_id = (station_id or "").strip()
    key = (key or "").strip()
    if not station_id or not key:
        raise WuError("Enter your Weather Underground station ID and key on the Setup page.")
    query = urllib.parse.urlencode(values(station_id, key, reading, now or datetime.now(timezone.utc)))
    request = urllib.request.Request(f"{URL}?{query}", headers={"User-Agent": f"WeatherLab {APP_VERSION}"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = response.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as exc:
        raise WuError(f"Weather Underground returned an error ({exc.code}).") from None
    except OSError as exc:
        raise WuError(f"Couldn't reach Weather Underground ({type(exc).__name__}).") from None
    if body.lower() != "success":
        raise WuError(f"Weather Underground didn't accept the upload: {body[:80]}")
