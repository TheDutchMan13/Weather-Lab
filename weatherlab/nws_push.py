"""New National Weather Service warnings and advisories, each sent once to the phone and shown on the PC.

The seen list in the station's folder remembers which alerts were already sent. The first check after the setting is
turned on only remembers what is active now, so an old warning is not sent as news.
"""

import json

from weatherlab import stations

SEEN_FILE = "nws_seen.json"
KEEP = 300  # how many sent alerts to remember


def alert_id(alert: dict) -> str:
    """One alert keeps the same id until it is reissued or expires."""
    return "|".join([alert.get("event", ""), alert.get("expires", ""), alert.get("headline", "")])


def new_alerts(alerts: list[dict], seen: list[str]) -> tuple[list[dict], list[str]]:
    """The alerts not seen before, and the seen list to keep afterwards."""
    known = set(seen)
    fresh = [a for a in alerts if alert_id(a) not in known]
    return fresh, (list(seen) + [alert_id(a) for a in fresh])[-KEEP:]


def message(alert: dict) -> str:
    event = alert.get("event") or "Weather alert"
    headline = alert.get("headline") or ""
    return f"{event}: {headline}" if headline else event


def is_urgent(alert: dict) -> bool:
    """Extreme and Severe alerts go through quiet hours; the rest wait, like other non-urgent notices."""
    return alert.get("severity") in ("Extreme", "Severe")


def load_seen() -> list[str] | None:
    """The seen list, or None when this station has never checked (so the first check only remembers)."""
    try:
        data = json.loads((stations.folder() / SEEN_FILE).read_text(encoding="utf-8"))
        return [str(x) for x in data.get("seen", [])]
    except (OSError, ValueError, AttributeError):
        return None


def save_seen(seen: list[str]) -> None:
    path = stations.folder() / SEEN_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"seen": seen[-KEEP:]}), encoding="utf-8")
