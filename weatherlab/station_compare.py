"""Compare two stations side by side (0.37.34): the numbers for each, and the difference between them.

Pure helpers with no streamlit, so the tests run without the page's dependencies. The page reads each station's own
database and hands the readings here."""

from weatherlab import units

# (key in the stored reading, label). The rows of the comparison table, in order.
FIELDS = [
    ("tempf", "Temperature"), ("feelslikef", "Feels like"), ("humidity", "Humidity"),
    ("windspeedmph", "Wind"), ("windgustmph", "Gust"), ("baromrelin", "Pressure"),
    ("dailyrainin", "Rain today"), ("uv", "UV index"),
]
DECIMALS = {"tempf": 1, "feelslikef": 1, "humidity": 0, "windspeedmph": 0, "windgustmph": 0, "baromrelin": 2,
            "dailyrainin": 2, "uv": 1}


def summarize(name: str, readings: list, now: float) -> dict:
    """What one station shows: its newest reading, how old that is, and the last 24 hours' high, low and top gust.

    readings is [(timestamp, {key: value})], oldest first, covering the last 24 hours."""
    if not readings:
        return {"name": name, "age_seconds": None, "now": {}, "high": None, "low": None, "gust_max": None, "count": 0}
    ts, latest = readings[-1]
    temps = [d["tempf"] for _, d in readings if isinstance(d.get("tempf"), (int, float))]
    gusts = [d["windgustmph"] for _, d in readings if isinstance(d.get("windgustmph"), (int, float))]
    return {"name": name, "age_seconds": max(0, int(now - ts)),
            "now": {k: latest[k] for k, _ in FIELDS if isinstance(latest.get(k), (int, float))},
            "high": max(temps) if temps else None, "low": min(temps) if temps else None,
            "gust_max": max(gusts) if gusts else None, "count": len(readings)}


def _signed(key: str, change: float, metric: bool) -> str:
    value = units.convert_change(key, change, metric)
    decimals = DECIMALS.get(key, 1)
    text = f"{abs(value):.{decimals}f}"
    if float(text) == 0:
        return "same"
    sign = "+" if value > 0 else "−"
    return f"{sign}{text}{units.suffix(key, metric)}"


def _text(key: str, value, metric: bool) -> str:
    if value is None:
        return "--"
    if key in units.US_UNIT:
        return units.format_value(key, value, metric, DECIMALS.get(key))
    return f"{value:.{DECIMALS.get(key, 1)}f}" + ("%" if key == "humidity" else "")


def rows(a: dict, b: dict, metric: bool) -> list[dict]:
    """The table: one row per reading both stations could have, with A, B and A minus B."""
    out = []
    for key, label in FIELDS:
        va, vb = a["now"].get(key), b["now"].get(key)
        if va is None and vb is None:
            continue
        out.append({"label": label, "a": _text(key, va, metric), "b": _text(key, vb, metric),
                    "diff": _signed(key, va - vb, metric) if va is not None and vb is not None else "--"})
    for key, label, field in (("tempf", "High, last 24 hours", "high"), ("tempf", "Low, last 24 hours", "low"),
                              ("windgustmph", "Top gust, last 24 hours", "gust_max")):
        va, vb = a.get(field), b.get(field)
        if va is None and vb is None:
            continue
        out.append({"label": label, "a": _text(key, va, metric), "b": _text(key, vb, metric),
                    "diff": _signed(key, va - vb, metric) if va is not None and vb is not None else "--"})
    return out


def headline(a: dict, b: dict, metric: bool) -> str:
    """One sentence on the temperature gap, or why there isn't one."""
    ta, tb = a["now"].get("tempf"), b["now"].get("tempf")
    if ta is None or tb is None:
        missing = a["name"] if ta is None else b["name"]
        return f"No recent temperature from {missing}."
    change = units.convert_change("tempf", abs(ta - tb), metric)
    unit_text = units.unit("tempf", metric)
    if round(change, 1) == 0:
        return f"{a['name']} and {b['name']} are at the same temperature."
    warmer, cooler = (a["name"], b["name"]) if ta > tb else (b["name"], a["name"])
    return f"{warmer} is {change:.1f}{unit_text} warmer than {cooler} right now."


def age_text(seconds) -> str:
    if seconds is None:
        return "no readings yet"
    if seconds < 90:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} d ago"
