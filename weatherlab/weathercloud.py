"""Optional upload to Weathercloud. Off by default.

Weathercloud takes metric values, each multiplied by ten (so 21.1 degrees is sent as 211). The device ID and key
come from your Weathercloud account. The key is kept in Windows Credential Manager, never in a file.
"""

from datetime import datetime, timezone

from weatherlab import uploads
from weatherlab.config import APP_VERSION

URL = "https://api.weathercloud.net/v01/set"
KEY_NAME = "weathercloud"
TYPE_CODE = "481"  # the station type code that Weathercloud expects for a generic station


def _c(f: float) -> float:
    return (f - 32) * 5 / 9


def values(device_id: str, key: str, reading: dict, now: datetime) -> dict:
    """The query values for one upload. Missing fields are left out."""
    out = {
        "wid": device_id,
        "key": key,
        "ver": APP_VERSION,
        "type": TYPE_CODE,
        "time": now.astimezone(timezone.utc).strftime("%Y%m%d %H%M%S"),
    }

    def put(name, value, convert):
        if value is not None:
            out[name] = convert(float(value))

    mph_to_ms = 0.44704
    inhg_to_hpa = 33.8639
    put("temp", reading.get("tempf"), lambda f: uploads.tenths(_c(f)))
    put("dew", reading.get("dewpointf"), lambda f: uploads.tenths(_c(f)))
    put("hum", reading.get("humidity"), lambda h: str(round(h)))
    for name in ("wspd", "wspdavg"):
        put(name, reading.get("windspeedmph"), lambda m: uploads.tenths(m * mph_to_ms))
    put("wspdhi", reading.get("windgustmph"), lambda m: uploads.tenths(m * mph_to_ms))
    for name in ("wdir", "wdiravg"):
        put(name, reading.get("winddir"), lambda d: str(round(d) % 360))
    put("bar", reading.get("baromrelin"), lambda inhg: uploads.tenths(inhg * inhg_to_hpa))
    put("rain", reading.get("dailyrainin"), lambda i: uploads.tenths(i * 25.4))
    put("rainrate", reading.get("rainratein"), lambda i: uploads.tenths(i * 25.4))
    put("solarrad", reading.get("solarradiation"), uploads.tenths)
    put("uvi", reading.get("uv"), uploads.tenths)
    return out


def send_reading(device_id: str, key: str, reading: dict, now: datetime | None = None) -> None:
    """Upload one reading. Raises UploadError when it can't be sent or Weathercloud says no."""
    device_id = (device_id or "").strip()
    key = (key or "").strip()
    if not device_id or not key:
        raise uploads.UploadError("Enter your Weathercloud device ID and key on the Setup page.")
    params = values(device_id, key, reading, now or datetime.now(timezone.utc))
    body = uploads.get(URL, params, "Weathercloud")
    if body != "200":
        raise uploads.UploadError(f"Weathercloud didn't accept the upload: {body[:80]}")
