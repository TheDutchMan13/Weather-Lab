"""Shared pieces for sending readings to weather networks: one GET request and clear error messages.

Keys are sent in the request but never shown in an error message.
"""

import urllib.error
import urllib.parse
import urllib.request

from weatherlab.config import APP_VERSION

TIMEOUT_S = 10


class UploadError(Exception):
    """A weather network couldn't be reached, or it rejected the upload."""


def get(url: str, params: dict, name: str) -> str:
    """Send one GET request and return the reply text, stripped. Raises UploadError when it can't be sent."""
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(f"{url}?{query}", headers={"User-Agent": f"WeatherLab {APP_VERSION}"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return response.read().decode("utf-8", "replace").strip()
    except urllib.error.HTTPError as exc:
        raise UploadError(f"{name} returned an error ({exc.code}).") from None
    except OSError as exc:
        raise UploadError(f"Couldn't reach {name} ({type(exc).__name__}).") from None


def tenths(value: float) -> str:
    """A value times ten, rounded to a whole number, as a string. Many networks expect this form."""
    return str(round(value * 10))
