"""Reads and checks GW2000 live data.

Copied from the dashboard's collectors/gw2000_collector.py (unit handling,
parse_livedata, LIMITS, clean, plausible). See SOURCES.md for the line ranges.
"""

import json
import re
import time
import urllib.request

MIN_ROWS_FOR_DAY = 20  # unused in Phase 1, kept for the daily summaries in a later phase

# ------------------------------------------------------------------ unit handling
_NUM = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*(.*)$")


def split_val(item):
    """{'val': '0.05 in'} or {'val': '78.8', 'unit': 'F'} -> (0.05, 'in'). (None, '') if there is no number."""
    m = _NUM.match(str(item.get("val", "")))
    if not m:
        return None, ""
    return float(m.group(1)), str(item.get("unit") or m.group(2) or "").strip()


def to_f(v, u):
    return v * 9 / 5 + 32 if u.upper().replace("°", "").replace("℃", "C") in ("C",) else v


def to_mph(v, u):
    u = u.lower().replace(" ", "")
    if u in ("km/h", "kmh", "kph"):
        return v * 0.621371
    if u in ("m/s", "ms"):
        return v * 2.236936
    if u in ("knots", "kn", "kt", "kts"):
        return v * 1.150779
    if u in ("ft/s", "fps"):
        return v * 0.681818
    return v


def to_in(v, u):
    return v / 25.4 if u.lower().startswith("mm") else v


def to_inhg(v, u):
    u = u.lower()
    if u in ("hpa", "mbar", "mb"):
        return v * 0.0295300
    if u == "kpa":
        return v * 0.2953
    if u == "mmhg":
        return v * 0.0393701
    return v


def to_wm2(v, u):
    u = u.lower()
    if u == "klux":
        return v * 1000 / 126.7
    if u == "lux":
        return v / 126.7
    if u == "fc":
        return v * 10.76 / 126.7
    return v


def _r(x, n=3):
    return None if x is None else round(x, n)


# ------------------------------------------------------------------ parsing the gateway's answer
def parse_livedata(live):
    """The GW2000's /get_livedata_info JSON -> one reading in imperial units (keys only for values present)."""
    common = {str(i.get("id", "")).lower(): i for i in live.get("common_list", []) if isinstance(i, dict)}
    out = {}

    def put(key, item_id, conv=None):
        it = common.get(item_id)
        if it is None:
            return
        v, u = split_val(it)
        if v is not None:
            out[key] = _r(conv(v, u) if conv else v)

    put("tempf", "0x02", to_f)
    put("humidity", "0x07")
    put("feelslikef", "3", to_f)
    put("dewpointf", "0x03", to_f)
    put("windspeedmph", "0x0b", to_mph)
    put("windgustmph", "0x0c", to_mph)
    put("solarradiation", "0x15", to_wm2)
    put("uv", "0x17")
    put("winddir", "0x0a")

    # Rain: a piezo gauge arrives as "piezoRain", a tipping-bucket gauge as "rain". Same IDs in both:
    # 0x0E rate, 0x10 today (0x11 week, 0x12 month, 0x13 year).
    rain_list = live.get("piezoRain") or live.get("rain")
    rain = {str(i.get("id", "")).lower(): i for i in (rain_list or []) if isinstance(i, dict)}
    for key, rid in (("rainratein", "0x0e"), ("dailyrainin", "0x10")):
        if rid in rain:
            v, u = split_val(rain[rid])
            if v is not None:
                out[key] = _r(to_in(v, u))

    w = (live.get("wh25") or [{}])[0]
    for key, field, conv in (("tempinf", "intemp", to_f), ("humidityin", "inhumi", None),
                             ("baromrelin", "rel", to_inhg), ("baromabsin", "abs", to_inhg)):
        if field in w:
            v, u = split_val({"val": w[field], "unit": w.get("unit") if field == "intemp" else None})
            if v is not None:
                out[key] = _r(conv(v, u) if conv else v)
    return out


LIMITS = {"tempf": (-40, 135), "feelslikef": (-60, 160), "dewpointf": (-60, 100), "humidity": (1, 100),
          "tempinf": (20, 130), "humidityin": (1, 100), "windspeedmph": (0, 120), "windgustmph": (0, 160),
          "winddir": (0, 360), "solarradiation": (0, 1800), "uv": (0, 20), "rainratein": (0, 20), "dailyrainin": (0, 20),
          "baromrelin": (25.5, 32.5), "baromabsin": (25.0, 32.5)}
MAX_TEMP_JUMP = 12.0  # degrees F between reads less than 5 minutes apart: anything bigger is a glitch


def clean(r):
    """Drops values outside physical limits (a single bad sensor value must not become an all-time record)."""
    return {k: v for k, v in r.items() if k not in LIMITS or LIMITS[k][0] <= v <= LIMITS[k][1]}


def plausible(r, prev=None):
    """Reject a read that is clearly not a weather reading (sensor offline, bad parse, sudden spike).
    prev: (ts, reading) of the last stored read, used for the spike check."""
    t = r.get("tempf")
    if t is None:
        return False
    if prev and time.time() - prev[0] < 300 and prev[1].get("tempf") is not None \
            and abs(t - prev[1]["tempf"]) > MAX_TEMP_JUMP:
        return False
    return True


# ------------------------------------------------------------------ talking to the gateway
def fetch(ip, path="/get_livedata_info", timeout=8):
    with urllib.request.urlopen(f"http://{ip}{path}", timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))
