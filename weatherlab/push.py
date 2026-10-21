"""Phone alerts through ntfy. The free ntfy app on a phone shows each alert when this PC sends it.

The topic is a name only you know. It is kept in Windows Credential Manager, beside the AirNow key.
Anyone who knows the topic can read the alerts, so the default one is long and random.
"""

import threading
import uuid

from weatherlab import secrets as keystore
from weatherlab import stations
from weatherlab.settings import load_settings

DEFAULT_SERVER = "https://ntfy.sh"
TOPIC_KEY = "ntfy_topic"


def topic_key(station_id: str | None = None) -> str:
    """The Credential Manager name for a station's topic. Each station has its own topic."""
    sid = station_id or stations.current()
    return TOPIC_KEY if sid == stations.MAIN else f"{TOPIC_KEY}:{sid}"


def new_topic() -> str:
    return "weatherlab-" + uuid.uuid4().hex[:20]


def request_for(server: str, topic: str, title: str, message: str, priority: str = "default"):
    """(url, headers, body) for one notification. Kept separate so it can be tested without the network."""
    base = (server or DEFAULT_SERVER).strip().rstrip("/")
    return f"{base}/{topic}", {"Title": title, "Priority": priority}, message.encode("utf-8")


def send(server: str, topic: str, title: str, message: str, timeout: float = 6.0) -> bool:
    """Send one notification. Returns False when there is no topic or the server can't be reached."""
    import urllib.request
    if not topic.strip():
        return False
    url, headers, body = request_for(server, topic.strip(), title, message)
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


def send_async(message: str) -> None:
    """Send an alert to the phone in the background, when a topic is set. Never holds up the collector."""
    topic = keystore.get_key(topic_key())
    if not topic:
        return
    server = load_settings().ntfy_server
    threading.Thread(target=send, args=(server, topic, "Weather Lab", message), daemon=True).start()
