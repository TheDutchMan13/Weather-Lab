"""All-time record alerts: a reading that beats the best day so far. Uses the daily summaries Weather Lab keeps."""

from weatherlab import units

READING_FOR = {  # daily summary key: (reading key, "max" or "min")
    "tempf_max": ("tempf", "max"), "tempf_min": ("tempf", "min"),
    "gust_max": ("windgustmph", "max"), "wind_max": ("windspeedmph", "max"),
    "rain_in": ("dailyrainin", "max"), "rainrate_max": ("rainratein", "max"),
    "humidity_max": ("humidity", "max"), "humidity_min": ("humidity", "min"),
}
LABELS = {"tempf_max": "Highest temperature", "tempf_min": "Lowest temperature", "gust_max": "Highest gust",
          "wind_max": "Highest wind", "rain_in": "Most rain in a day", "rainrate_max": "Fastest rain rate",
          "humidity_max": "Highest humidity", "humidity_min": "Lowest humidity"}
UNITS = {"tempf_max": "°F", "tempf_min": "°F", "gust_max": " mph", "wind_max": " mph", "rain_in": " in",
         "rainrate_max": " in/hr", "humidity_max": "%", "humidity_min": "%"}


def bests(daily_rows):
    """daily_rows: (date, summary) pairs. Returns the best value for each record key that has data."""
    out = {}
    for key, (_, kind) in READING_FOR.items():
        found = [d[key] for _, d in daily_rows if d.get(key) is not None]
        if found:
            out[key] = max(found) if kind == "max" else min(found)
    return out


def combine(a, b):
    """The better of two sets of bests, key by key (for example the saved ones and the ones seen today)."""
    out = dict(a)
    for key, value in b.items():
        if key not in READING_FOR or value is None:
            continue
        kind = READING_FOR[key][1]
        if key not in out or (value > out[key] if kind == "max" else value < out[key]):
            out[key] = value
    return out


def _text(key, value, metric):
    """A record value in the chosen units, such as "95°F" or "35.0°C"."""
    reading_key = READING_FOR[key][0]
    if reading_key in units.US_UNIT:
        shown = units.convert(reading_key, value, metric)
        return (f"{shown:.1f}" if metric else f"{value:g}") + units.suffix(reading_key, metric)
    return f"{value:g}{UNITS[key]}"


def check(best, reading, metric=False):
    """(key, value, message) for each reading that beats its record. Keys without a record are skipped."""
    out = []
    for key, (reading_key, kind) in READING_FOR.items():
        value, record = reading.get(reading_key), best.get(key)
        if value is None or record is None:
            continue
        if (kind == "max" and value > record) or (kind == "min" and value < record):
            out.append((key, value, f"New record: {LABELS[key]} {_text(key, value, metric)} "
                                    f"(was {_text(key, record, metric)})"))
    return out
