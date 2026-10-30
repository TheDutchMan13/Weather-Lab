"""Optional upload to PWSweather. Off by default.

PWSweather takes the same upload as Weather Underground, so this reuses that format. The station ID and key come
from your PWSweather account. The key is kept in Windows Credential Manager, never in a file.
"""

from datetime import datetime

from weatherlab import uploads, wunderground

URL = "https://www.pwsweather.com/pwsupdate/pwsupdate.php"
KEY_NAME = "pwsweather"


def send_reading(station_id: str, key: str, reading: dict, now: datetime | None = None) -> None:
    """Upload one reading. Raises UploadError when it can't be sent or PWSweather says no."""
    station_id = (station_id or "").strip()
    key = (key or "").strip()
    if not station_id or not key:
        raise uploads.UploadError("Enter your PWSweather station ID and key in Settings, under Station.")
    params = wunderground.values(station_id, key, reading, now or datetime.now())
    body = uploads.get(URL, params, "PWSweather")
    # PWSweather answers with an empty body when the upload is accepted; some replies say "success" instead.
    if body and body.lower() != "success":
        raise uploads.UploadError(f"PWSweather didn't accept the upload: {body[:80]}")
