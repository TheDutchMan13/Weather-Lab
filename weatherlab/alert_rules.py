"""Alert rules: a Windows notification and phone alert when readings cross thresholds. Rules are kept in settings.json.

The simple rule: {"name": "Extreme heat", "metric": "heat_index", "op": ">=", "value": 110}.

A rule with more conditions: {"name": "Hot and dry",
    "conditions": [{"metric": "tempf", "op": ">=", "value": 105}, {"metric": "humidity", "op": "<=", "value": 20}],
    "combine": "AND", "window": "day", "months": [], "escalate": True}
  combine: "AND" (all conditions) or "OR" (any condition).
  window: "any", "day" (6 AM to 6 PM), "night" (6 PM to 6 AM), or "months" (the months listed).
  escalate: when on, the message becomes more serious the longer the rule stays true.

Values are always stored in US units and shown in the chosen units.
"""

import math
from datetime import datetime

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
    "pressure_drop": ("Pressure falling", ""),  # inches of mercury per hour; see DELTA_UNITS
    "temp_drop": ("Temperature falling", ""),  # degrees Fahrenheit per hour; see DELTA_UNITS
}
OPS = {">=": "at or above", "<=": "at or below"}
WINDOWS = {"any": "any time", "day": "daytime, 6 AM to 6 PM", "night": "night, 6 PM to 6 AM", "months": "chosen months"}
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
               "October", "November", "December"]
LEVELS = {1: "Notice", 2: "Warning", 3: "Severe"}
COOLDOWN_S = 3600  # a rule that doesn't escalate repeats at most once an hour
ESCALATE_TO_WARNING_S = 3600  # an escalating rule is a Warning after an hour...
ESCALATE_TO_SEVERE_S = 3 * 3600  # ...and Severe after three hours
SEVERE_REPEAT_S = 3 * 3600  # Severe repeats every three hours while it lasts
RATE_WINDOW_S = 3600  # pressure and temperature falls are measured over the last hour
MIN_RATE_SPAN_S = 1800  # and need at least half an hour of readings

# Metrics that are changes per hour: (US to metric factor, US unit, metric unit)
DELTA_UNITS = {"pressure_drop": (33.8639, "inHg per hour", "mb per hour"),  # 1 inHg = 33.8639 hPa
               "temp_drop": (5 / 9, "°F per hour", "°C per hour")}


def conditions_of(rule: dict) -> list[dict]:
    """The rule's conditions. A simple rule is treated as one condition."""
    if rule.get("conditions"):
        return list(rule["conditions"])
    return [{"metric": rule.get("metric"), "op": rule.get("op"), "value": rule.get("value")}]


def _months(rule: dict) -> list[int]:
    return sorted({int(m) for m in rule.get("months") or [] if 1 <= int(m) <= 12})


def _valid_condition(c: dict):
    if c.get("metric") not in METRICS:
        return "Pick what to watch."
    if c.get("op") not in OPS:
        return "Pick at or above or at or below."
    try:
        value = float(c.get("value"))
    except (TypeError, ValueError):
        return "Enter a number."
    if not math.isfinite(value):
        return "Enter a number."
    return None


def valid_rule(rule: dict):
    """A problem to show the user, or None when the rule is fine."""
    conditions = conditions_of(rule)
    if not conditions:
        return "Add a condition."
    for c in conditions:
        problem = _valid_condition(c)
        if problem:
            return problem
    if len(conditions) > 1 and rule.get("combine", "AND") not in ("AND", "OR"):
        return "Pick AND or OR."
    if rule.get("window", "any") not in WINDOWS:
        return "Pick when the rule applies."
    if rule.get("window") == "months" and not _months(rule):
        return "Pick at least one month."
    return None


def in_window(rule: dict, now: float, tz=None) -> bool:
    """Whether the rule applies at this time, judged in the station's time zone."""
    window = rule.get("window", "any")
    if window == "any":
        return True
    local = datetime.fromtimestamp(now, tz) if tz else datetime.fromtimestamp(now)
    if window == "months":
        return local.month in _months(rule)
    if window == "day":
        return 6 <= local.hour < 18
    if window == "night":
        return local.hour < 6 or local.hour >= 18
    return True


def _shown(c: dict, metric: bool) -> str:
    """The threshold in the chosen units, with its unit: "110°F" or "43.3°C"."""
    key = c.get("metric")
    value = float(c.get("value", 0))
    if key in DELTA_UNITS:
        factor, us_unit, metric_unit = DELTA_UNITS[key]
        return f"{value * factor:.2f} {metric_unit}" if metric else f"{value:.2f} {us_unit}"
    if key in units.US_UNIT:
        shown = units.convert(key, value, metric)
        return (f"{shown:.1f}" if metric else f"{value:g}") + units.suffix(key, metric)
    return f"{value:g}" + METRICS.get(key, ("?", ""))[1]


def _describe_condition(c: dict, metric: bool) -> str:
    label, _ = METRICS.get(c.get("metric"), ("?", ""))
    return f"{label} {OPS.get(c.get('op'), '?')} {_shown(c, metric)}"


def describe(rule: dict, metric: bool = False) -> str:
    conditions = conditions_of(rule)
    first_label, _ = METRICS.get(conditions[0].get("metric"), ("?", ""))
    joiner = " or " if rule.get("combine") == "OR" else " and "
    text = f"{rule.get('name') or first_label}: " + joiner.join(_describe_condition(c, metric) for c in conditions)
    if rule.get("window", "any") != "any":
        if rule["window"] == "months":
            text += " (" + ", ".join(MONTH_NAMES[m - 1] for m in _months(rule)) + ")"
        else:
            text += f" ({WINDOWS[rule['window']]})"
    return text


def value_of(metric: str, reading: dict, context: dict | None = None):
    if context and metric in context:
        return context[metric]
    if metric == "heat_index":
        t, rh = reading.get("tempf"), reading.get("humidity")
        if t is None or rh is None:
            return None
        return comfort.heat_index_f(t, rh)
    return reading.get(metric)


def _met(c: dict, reading: dict, context: dict | None) -> bool:
    v = value_of(c["metric"], reading, context)
    if v is None:
        return False
    limit = float(c["value"])
    return v >= limit if c["op"] == ">=" else v <= limit


def triggered(rule: dict, reading: dict, context: dict | None = None) -> bool:
    """True when the rule's conditions hold together (AND) or one of them holds (OR). The time window is checked
    separately, in evaluate()."""
    results = [_met(c, reading, context) for c in conditions_of(rule)]
    if not results:
        return False
    return any(results) if rule.get("combine") == "OR" else all(results)


def rates(readings: list, now: float) -> dict:
    """Pressure falling (inches of mercury per hour) and temperature falling (degrees per hour), from the readings
    of the last hour. Positive numbers mean falling. readings: [(timestamp, reading)] in time order."""
    recent = [(ts, r) for ts, r in readings if now - RATE_WINDOW_S <= ts <= now]
    out = {}
    if len(recent) < 2:
        return out
    (t0, first), (t1, last) = recent[0], recent[-1]
    span = t1 - t0
    if span < MIN_RATE_SPAN_S:
        return out
    hours = span / 3600
    if first.get("baromrelin") is not None and last.get("baromrelin") is not None:
        out["pressure_drop"] = round((first["baromrelin"] - last["baromrelin"]) / hours, 3)
    if first.get("tempf") is not None and last.get("tempf") is not None:
        out["temp_drop"] = round((first["tempf"] - last["tempf"]) / hours, 1)
    return out


def to_us_value(key: str, value: float, metric: bool) -> float:
    """A value typed in the chosen units, converted to the US units rules are stored in."""
    if key in DELTA_UNITS:
        return round(value / DELTA_UNITS[key][0], 3) if metric else value
    return units.to_us(key, value, metric)


def rule_key(rule: dict) -> str:
    return repr(sorted(rule.items()))


def evaluate(rules, reading: dict, now: float, state: dict, metric: bool = False, tz=None,
             context: dict | None = None) -> list[str]:
    """Messages for rules that just fired. state remembers, for each rule, when it started and when it last sent a
    message, so messages don't repeat too often and escalating rules step up."""
    messages = []
    for rule in rules or []:
        if valid_rule(rule):
            continue
        key = rule_key(rule)
        if not (in_window(rule, now, tz) and triggered(rule, reading, context)):
            state.pop(key, None)
            continue
        entry = state.get(key)
        if entry is None:
            entry = {"since": now, "level": 0, "sent": None}
            state[key] = entry
        text = describe(rule, metric)
        if rule.get("escalate"):
            elapsed = now - entry["since"]
            level = 3 if elapsed >= ESCALATE_TO_SEVERE_S else 2 if elapsed >= ESCALATE_TO_WARNING_S else 1
            if level > entry["level"]:
                entry["level"], entry["sent"] = level, now
                messages.append(f"{LEVELS[level]}: {text}")
            elif level == 3 and now - entry["sent"] >= SEVERE_REPEAT_S:
                entry["sent"] = now
                messages.append(f"{LEVELS[3]}, still going: {text}")
        elif entry["sent"] is None or now - entry["sent"] >= COOLDOWN_S:
            entry["sent"] = now
            messages.append(text)
    return messages


def notify(title: str, text: str) -> bool:
    """Shows a Windows notification. Returns False if it can't be shown; the message is still listed in Settings."""
    try:
        from plyer import notification
        notification.notify(title=title, message=text, app_name="Weather Lab", timeout=10)
        return True
    except Exception:
        return False
