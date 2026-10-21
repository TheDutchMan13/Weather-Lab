"""Optional publishing to an MQTT broker, such as the Mosquitto add-on in Home Assistant. Off by default.

Each reading goes to its own topic under your topic prefix, as plain text, and is kept by the broker (retained), so
Home Assistant has a value straight after a restart. Discovery messages let Home Assistant add the sensors itself.

This is a small built-in client for MQTT 3.1.1 that sends retained QoS 0 messages with a username and password. It
does not use TLS, so use it on your local network only. The password is kept in Windows Credential Manager.
"""

import json
import socket
import struct

from weatherlab import uploads
from weatherlab.config import APP_VERSION

TIMEOUT_S = 10
KEY_NAME = "mqtt"
DISCOVERY_PREFIX = "homeassistant"
DEVICE_ID = "weatherlab"
MqttError = uploads.UploadError  # the error every upload raises

# (topic part, Home Assistant name, reading field, unit, Home Assistant device class or None)
SENSORS = [
    ("temperature", "Outdoor temperature", "tempf", "°F", "temperature"),
    ("humidity", "Humidity", "humidity", "%", "humidity"),
    ("wind/speed", "Wind speed", "windspeedmph", "mph", None),
    ("wind/gust", "Wind gust", "windgustmph", "mph", None),
    ("wind/direction", "Wind direction", "winddir", "°", None),
    ("rain/daily", "Rain today", "dailyrainin", "in", None),
    ("pressure", "Pressure", "baromrelin", "inHg", "atmospheric_pressure"),
    ("uv", "UV index", "uv", "UV index", None),
    ("solar", "Solar radiation", "solarradiation", "W/m²", None),
]


def check_prefix(prefix: str) -> str:
    """The topic prefix without surrounding slashes. Raises MqttError when it can't be used in a topic."""
    prefix = (prefix or "").strip().strip("/")
    if not prefix or any(c in prefix for c in "+#\0") or "//" in prefix:
        raise MqttError("The topic prefix can't be empty and can't contain +, # or double slashes.")
    return prefix


def readings(prefix: str, reading: dict) -> list[tuple[str, str]]:
    """(topic, payload) for each reading the station reported, plus a retained online flag."""
    prefix = check_prefix(prefix)
    out = []
    for part, _label, field, _unit, _device_class in SENSORS:
        value = reading.get(field)
        if value is not None:
            out.append((f"{prefix}/{part}", f"{round(float(value), 2):g}"))
    out.append((f"{prefix}/status/online", "true"))
    return out


def discovery(prefix: str) -> list[tuple[str, str]]:
    """Home Assistant MQTT discovery messages, one per sensor. Retained, so Home Assistant keeps them."""
    prefix = check_prefix(prefix)
    device = {"identifiers": [DEVICE_ID], "name": "Weather Lab", "manufacturer": "Ecowitt",
              "model": "GW2000 with Weather Lab", "sw_version": APP_VERSION}
    out = []
    for part, label, _field, unit, device_class in SENSORS:
        object_id = f"{DEVICE_ID}_{part.replace('/', '_')}"
        config = {"name": label, "unique_id": object_id, "state_topic": f"{prefix}/{part}",
                  "unit_of_measurement": unit, "state_class": "measurement", "device": device}
        if device_class:
            config["device_class"] = device_class
        out.append((f"{DISCOVERY_PREFIX}/sensor/{DEVICE_ID}/{object_id}/config", json.dumps(config)))
    return out


def _text(value: str) -> bytes:
    data = value.encode("utf-8")
    return struct.pack("!H", len(data)) + data


def _remaining_length(n: int) -> bytes:
    out = bytearray()
    while True:
        byte = n % 128
        n //= 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def connect_packet(client_id: str, user: str = "", password: str = "", keepalive: int = 60) -> bytes:
    flags = 0x02  # clean session
    payload = _text(client_id)
    if user:
        flags |= 0x80
        payload += _text(user)
        if password:
            flags |= 0x40
            payload += _text(password)
    body = _text("MQTT") + bytes([4, flags]) + struct.pack("!H", keepalive) + payload  # protocol level 4 is 3.1.1
    return bytes([0x10]) + _remaining_length(len(body)) + body


def publish_packet(topic: str, payload: str, retain: bool = True) -> bytes:
    body = _text(topic) + payload.encode("utf-8")
    return bytes([0x31 if retain else 0x30]) + _remaining_length(len(body)) + body


DISCONNECT = b"\xe0\x00"
CONNACK_ERRORS = {1: "the broker doesn't support this protocol version", 2: "the broker rejected the client ID",
                  3: "the broker is unavailable", 4: "the broker rejected the username or password",
                  5: "the broker says this user isn't allowed to publish"}


def send(host: str, port: int, user: str, password: str, messages: list[tuple[str, str]],
         client_id: str = "weatherlab") -> None:
    """Connect, publish each message (retained), and disconnect. Raises MqttError when it can't be done."""
    host = (host or "").strip()
    if not host:
        raise MqttError("Enter the MQTT broker address on the Setup page.")
    try:
        with socket.create_connection((host, int(port)), timeout=TIMEOUT_S) as sock:
            sock.sendall(connect_packet(client_id, user, password))
            ack = sock.recv(4)
            if len(ack) != 4 or ack[0] != 0x20:
                raise MqttError("The MQTT broker didn't answer the connection request.")
            if ack[3] != 0:
                raise MqttError(f"MQTT broker refused the connection: {CONNACK_ERRORS.get(ack[3], 'unknown reason')}.")
            for topic, payload in messages:
                sock.sendall(publish_packet(topic, payload))
            sock.sendall(DISCONNECT)
    except MqttError:
        raise
    except OSError as exc:
        raise MqttError(f"Couldn't reach the MQTT broker ({type(exc).__name__}).") from None
