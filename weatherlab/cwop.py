"""Optional upload to CWOP (Citizen Weather Observer Program). Off by default.

Sends the latest reading as an APRS position weather report over APRS-IS. Once CWOP is on,
your station's location is public on weather maps such as aprs.fi.

The passcode is the standard APRS-IS passcode, calculated from the callsign.
"""

import socket
from datetime import datetime, timezone

HOST = "rotate.aprs2.net"
PORT = 14580
TIMEOUT_S = 10
SOFTWARE = "WeatherLab 0.1"
MISSING = "."  # APRS uses dots for a value that isn't available


class CwopError(Exception):
    """CWOP couldn't be reached, or the callsign was rejected."""


def passcode(callsign: str) -> int:
    """The APRS-IS passcode for a callsign, with any SSID dropped."""
    call = callsign.strip().upper().split("-")[0]
    h = 0x73E2
    for i in range(0, len(call), 2):
        h ^= ord(call[i]) << 8
        if i + 1 < len(call):
            h ^= ord(call[i + 1])
    return h & 0x7FFF


def _lat(lat: float) -> str:
    a = abs(lat)
    d = int(a)
    return f"{d:02d}{(a - d) * 60:05.2f}{'N' if lat >= 0 else 'S'}"


def _lon(lon: float) -> str:
    a = abs(lon)
    d = int(a)
    return f"{d:03d}{(a - d) * 60:05.2f}{'E' if lon >= 0 else 'W'}"


def _field(value, width: int, scale: float = 1.0) -> str:
    if value is None:
        return MISSING * width
    return f"{round(value * scale):0{width}d}"


def weather_packet(callsign: str, reading: dict, lat: float, lon: float, now: datetime) -> str:
    """One position weather report. Units: wind mph, temperature F, rain in hundredths of an inch,
    humidity %, pressure in tenths of hPa (from the sea-level reading)."""
    call = callsign.strip().upper()
    stamp = now.astimezone(timezone.utc).strftime("%d%H%M")
    hum = reading.get("humidity")
    hum_text = MISSING * 2 if hum is None else f"{round(hum) % 100:02d}"  # APRS writes 100% as 00
    return (f"{call}>APRS,TCPIP*:@{stamp}z{_lat(lat)}/{_lon(lon)}_"
            f"{_field(reading.get('winddir'), 3)}/{_field(reading.get('windspeedmph'), 3)}"
            f"g{_field(reading.get('windgustmph'), 3)}"
            f"t{_field(reading.get('tempf'), 3)}"
            f"r{MISSING * 3}p{MISSING * 3}"
            f"P{_field(reading.get('dailyrainin'), 3, 100)}"
            f"h{hum_text}"
            f"b{_field(reading.get('baromrelin'), 5, 33.8639 * 10)}")


def send_reading(callsign: str, reading: dict, lat, lon, now: datetime | None = None) -> str:
    """Log in to APRS-IS and send one weather report. Returns the packet that was sent."""
    call = (callsign or "").strip()
    if not call:
        raise CwopError("Enter a CWOP callsign on the Setup page.")
    if lat is None or lon is None:
        raise CwopError("Set your latitude and longitude on the Setup page.")
    packet = weather_packet(call, reading, lat, lon, now or datetime.now(timezone.utc))
    try:
        with socket.create_connection((HOST, PORT), timeout=TIMEOUT_S) as sock:
            link = sock.makefile("rwb")
            link.readline()  # server greeting
            link.write(f"user {call.upper()} pass {passcode(call)} vers {SOFTWARE}\r\n".encode("ascii"))
            link.flush()
            reply = link.readline().decode("ascii", "replace").lower()
            if "unverified" in reply or "verified" not in reply:
                raise CwopError("CWOP didn't accept this callsign. Check it on the Setup page.")
            link.write((packet + "\r\n").encode("ascii"))
            link.flush()
    except OSError as exc:
        raise CwopError(f"Couldn't reach the CWOP network ({type(exc).__name__}).") from exc
    return packet
