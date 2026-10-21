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
