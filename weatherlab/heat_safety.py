"""Heat safety: how hot it feels and what to do about it, from the heat index.

Levels are the National Weather Service heat index categories. The advice is general, not medical.
"""

from weatherlab import comfort

LEVELS = [  # (lowest heat index in °F, level, advice), highest first
    (125, "Extreme danger", "Heatstroke is likely. Stay indoors in air conditioning and don't work or exercise outside."),
    (104, "Danger", "Heat cramps and exhaustion are likely. Limit time outdoors, rest in the shade often, and drink water."),
    (91, "Extreme caution", "Heat cramps and exhaustion are possible. Take breaks, drink water, and watch for signs of heat illness."),
    (80, "Caution", "Fatigue is possible with long time in the heat. Drink water and take breaks in the shade."),
    (-999, "Comfortable", "No heat warning. Drink water as usual when you're active outside."),
]


def heat_index(temp_f, humidity):
    """Heat index in °F, or None when temperature or humidity is missing."""
    if temp_f is None or humidity is None:
        return None
    return comfort.heat_index_f(temp_f, humidity)


def level_for(index):
    """(level, advice) for a heat index value."""
    for low, name, advice in LEVELS:
        if index >= low:
            return name, advice
    return LEVELS[-1][1], LEVELS[-1][2]


def status(temp_f, humidity):
    index = heat_index(temp_f, humidity)
    if index is None:
        return {"heat_index": None, "level": "No data", "advice": ""}
    name, advice = level_for(index)
    return {"heat_index": index, "level": name, "advice": advice}


LEVEL_NAMES = [name for _, name, _ in reversed(LEVELS)]   # Comfortable first, Extreme danger last
LEVEL_COLOURS = {"Comfortable": "#2fbf71", "Caution": "#d9a441", "Extreme caution": "#e8833a",
                 "Danger": "#e5534b", "Extreme danger": "#8f1d1d"}
MAX_GAP_SECONDS = 1800   # a gap in readings longer than this is not counted
DANGER_INDEX = 104       # heat index at which the Danger level starts


def hours_by_level(series) -> dict:
    """series: [(timestamp, heat index F or None)] in time order. Hours spent in each level.

    Each reading counts until the next one; a gap over 30 minutes counts as 30 minutes."""
    hours = {name: 0.0 for name in LEVEL_NAMES}
    points = [(ts, hi) for ts, hi in series if hi is not None]
    for (t0, hi), (t1, _) in zip(points, points[1:]):
        hours[level_for(hi)[0]] += min(max(t1 - t0, 0), MAX_GAP_SECONDS) / 3600
    return hours


def danger_hours(hours: dict) -> float:
    """Hours at Danger or worse."""
    return hours.get("Danger", 0.0) + hours.get("Extreme danger", 0.0)


def dangerous_days(days) -> list:
    """days: [(date, daily summary)]. Days whose highest heat index reached Danger, worst first: [(date, index, level)]."""
    found = [(d, s["heat_index_max"]) for d, s in days
             if s.get("heat_index_max") is not None and s["heat_index_max"] >= DANGER_INDEX]
    found.sort(key=lambda x: (x[1], x[0]), reverse=True)
    return [(d, hi, level_for(hi)[0]) for d, hi in found]
