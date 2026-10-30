"""Optional upload to Weather Underground's personal weather station network. Off by default.

Sends the latest reading to Weather Underground. The station ID and key come from your station page on
wunderground.com. The key is kept in Windows Credential Manager, never in a file, and is never shown in messages.
"""

from datetime import datetime, timezone

from weatherlab import uploads
from weatherlab.config import APP_VERSION

URL = "https://weatherstation.wunderground.com/weatherstation/updateweatherstation.php"
KEY_NAME = "wunderground"
WuError = uploads.UploadError  # the error every upload raises

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


def values(station_id: str, key: str, reading: dict, now: datetime) -> dict:
    """The query values for one upload in the Weather Underground format. Missing fields are left out."""
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
    """Upload one reading. Raises UploadError when it can't be sent or Weather Underground says no."""
    station_id = (station_id or "").strip()
    key = (key or "").strip()
    if not station_id or not key:
        raise uploads.UploadError("Enter your Weather Underground station ID and key in Settings, under Station.")
    body = uploads.get(URL, values(station_id, key, reading, now or datetime.now(timezone.utc)), "Weather Underground")
    if body.lower() != "success":
        raise uploads.UploadError(f"Weather Underground didn't accept the upload: {body[:80]}")
