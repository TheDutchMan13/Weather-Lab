"""Battery and signal for the wireless sensors, read from the GW2000 on your network (its /get_sensors_info pages).

Ported from the dashboard's utils/sensor_battery.py (see SOURCES.md). Battery levels run 0 to 5 (5 full,
6 = mains powered, 9 = no sensor paired). Signal runs 0 to 4 (4 best), with radio strength in dBm.
"""

import json
import urllib.request

UNPAIRED = ("FFFFFFFF", "FFFFFFFE")
FRIENDLY = {"wh90": "Outdoor array (WS90)", "wh57": "Lightning sensor (WH57)", "wh85": "Wind and rain (WH85)",
            "wh69": "Outdoor array (WH69)", "wh31": "Temperature and humidity", "wh41": "Air quality (PM2.5)",
            "wh45": "Air quality (PM2.5, CO2)", "wh55": "Leak sensor", "wn20": "Rain gauge", "wh40": "Rain gauge",
            "wh26": "Temperature and humidity", "wh25": "Indoor sensor", "wh68": "Solar and wind", "wh80": "Wind sensor"}


def _num(x, cast=float):
    try:
        return cast(str(x).strip())
    except (TypeError, ValueError):
        return None


def parse_sensors(pages):
    """pages: the JSON lists from /get_sensors_info (pages 1 and 2). Returns the paired sensors only."""
    rows = []
    for page in pages:
        for it in page if isinstance(page, list) else []:
            sid = str(it.get("id", "")).upper()
            if not sid or sid in UNPAIRED:
                continue
            img = str(it.get("img", ""))
            batt = _num(it.get("batt"), int)
            rows.append({"name": FRIENDLY.get(img, str(it.get("name") or img)),
                         "batt": None if batt == 9 else batt,
                         "rssi": _num(it.get("rssi"), int), "signal": _num(it.get("signal"), int)})
    return rows


def fetch(ip, path, timeout=6):
    with urllib.request.urlopen(f"http://{ip}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def read(ip):
    """Paired sensors on the station at ip. Raises OSError or ValueError when the station can't be reached."""
    return parse_sensors([fetch(ip, "/get_sensors_info?page=1"), fetch(ip, "/get_sensors_info?page=2")])


def battery_state(batt):
    """(state, text). state: good, ok, watch, low, dc or unknown."""
    if batt is None:
        return "unknown", ""
    if batt == 6:
        return "dc", "mains powered"
    state = "good" if batt >= 4 else "ok" if batt == 3 else "watch" if batt == 2 else "low"
    return state, f"level {batt} of 5"


def signal_state(signal, rssi=None):
    """(state, text). state: good, fair, weak, none or unknown."""
    if signal is None and rssi is None:
        return "unknown", ""
    state = "unknown"
    if signal is not None:
        state = "good" if signal >= 3 else "fair" if signal == 2 else "weak" if signal == 1 else "none"
    if rssi is not None and rssi <= -92 and state in ("good", "fair", "unknown"):
        state = "weak"
    bits = []
    if signal is not None:
        bits.append(f"{signal} of 4")
    if rssi is not None:
        bits.append(f"{rssi} dBm")
    return state, ", ".join(bits)


def warnings(sensors):
    """Plain-language warnings for sensors with a low battery or a weak signal."""
    out = []
    for sensor in sensors:
        name = sensor.get("name") or "Sensor"
        batt_state, _ = battery_state(sensor.get("batt"))
        if batt_state == "low":
            out.append(f"{name}: battery is low. Replace it soon.")
        elif batt_state == "watch":
            out.append(f"{name}: battery is getting low.")
        signal, _ = signal_state(sensor.get("signal"), sensor.get("rssi"))
        if signal in ("weak", "none"):
            out.append(f"{name}: signal is weak. Check its distance from the station.")
    return out
