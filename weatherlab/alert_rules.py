"""Alert rules: a Windows notification when a reading crosses a threshold. Rules are kept in settings.json.

A rule looks like {"name": "Extreme heat", "metric": "heat_index", "op": ">=", "value": 110}.
The value is always stored in US units and shown in the chosen units.
"""

import math

from weatherlab import comfort, units

METRICS = {  # key: (label, unit shown after the value when the reading has no unit of its own)
    "tempf": ("Temperature", "°F"),
    "heat_index": ("Heat index", "°F"),
    "tempinf": ("Indoor temperature", "°F"),
    "humidity": ("Humidity", "%"),
    "windspeedmph": ("Wind", " mph"),
    "windgustmph": ("Wind gust", " mph"),
    "rainratein": ("Rain rate", " in/hr"),
    "dailyrainin": ("Rain today", " in"),
    "uv": ("UV index", ""),
}
OPS = {">=": "at or above", "<=": "at or below"}
COOLDOWN_S = 3600  # the same rule repeats at most once an hour


def valid_rule(rule):
    """A problem to show the user, or None when the rule is fine."""
    if rule.get("metric") not in METRICS:
        return "Pick what to watch."
    if rule.get("op") not in OPS:
        return "Pick at or above or at or below."
    try:
        value = float(rule.get("value"))
    except (TypeError, ValueError):
        return "Enter a number."
    if not math.isfinite(value):
        return "Enter a number."
    return None


def _shown(rule, metric):
    """The threshold in the chosen units, with its unit: "110°F" or "43.3°C"."""
    key = rule.get("metric")
    value = float(rule.get("value", 0))
    if key in units.US_UNIT:
        shown = units.convert(key, value, metric)
        return (f"{shown:.1f}" if metric else f"{value:g}") + units.suffix(key, metric)
    return f"{value:g}" + METRICS.get(key, ("?", ""))[1]


def describe(rule, metric=False):
    label, _ = METRICS.get(rule.get("metric"), ("?", ""))
    return f"{rule.get('name') or label}: {label} {OPS.get(rule.get('op'), '?')} {_shown(rule, metric)}"


def value_of(metric, reading):
    if metric == "heat_index":
        t, rh = reading.get("tempf"), reading.get("humidity")
        if t is None or rh is None:
            return None
        return comfort.heat_index_f(t, rh)
    return reading.get(metric)


def triggered(rule, reading):
    v = value_of(rule["metric"], reading)
    if v is None:
        return False
    limit = float(rule["value"])
    return v >= limit if rule["op"] == ">=" else v <= limit


def evaluate(rules, reading, now, last_fired, metric=False):
    """Messages for rules that just triggered. last_fired remembers when each rule last sent a message."""
    messages = []
    for rule in rules or []:
        if valid_rule(rule) or not triggered(rule, reading):
            continue
        key = repr(sorted(rule.items()))
        if key in last_fired and now - last_fired[key] < COOLDOWN_S:
            continue
        last_fired[key] = now
        messages.append(describe(rule, metric))
    return messages


def notify(title, text):
    """Shows a Windows notification. Returns False if it can't be shown; the message is still listed in Setup."""
    try:
        from plyer import notification
        notification.notify(title=title, message=text, app_name="Weather Lab", timeout=10)
        return True
    except Exception:
        return False
