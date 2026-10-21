"""US or metric display. Readings are stored in US units; this only changes how the app shows them.

The Settings page (Appearance) has the US/Metric choice. Export and import files stay in US units.
"""

CHOICES = ["US", "Metric"]
_TEMP = {"tempf", "tempinf", "dewpointf", "feelslikef", "heat_index"}
_FACTOR = {"windspeedmph": 1.609344, "windgustmph": 1.609344, "miles": 1.609344,
           "dailyrainin": 25.4, "rainratein": 25.4, "baromrelin": 33.8639, "baromabsin": 33.8639}
US_UNIT = {"tempf": "°F", "tempinf": "°F", "dewpointf": "°F", "feelslikef": "°F", "heat_index": "°F",
           "windspeedmph": "mph", "windgustmph": "mph", "dailyrainin": "in", "rainratein": "in/hr",
           "baromrelin": "inHg", "baromabsin": "inHg", "miles": "mi"}
METRIC_UNIT = {"tempf": "°C", "tempinf": "°C", "dewpointf": "°C", "feelslikef": "°C", "heat_index": "°C",
               "windspeedmph": "km/h", "windgustmph": "km/h", "dailyrainin": "mm", "rainratein": "mm/h",
               "baromrelin": "hPa", "baromabsin": "hPa", "miles": "km"}


def is_metric(choice):
    return choice == "Metric"


def converts(key):
    """True for readings that change with the units setting."""
    return key in US_UNIT


def convert(key, value, metric):
    """A US reading in the chosen units. None stays None."""
    if value is None or not metric or key not in METRIC_UNIT:
        return value
    if key in _TEMP:
        return (value - 32) * 5 / 9
    return value * _FACTOR[key]


def convert_change(key, change, metric):
    """A difference between two readings in the chosen units. Temperature differences have no 32 degree offset."""
    if change is None or not metric or key not in METRIC_UNIT:
        return change
    if key in _TEMP:
        return change * 5 / 9
    return change * _FACTOR[key]


def to_us(key, value, metric):
    """A value typed in the chosen units, converted back to US units for storage."""
    if value is None or not metric or key not in METRIC_UNIT:
        return value
    if key in _TEMP:
        return value * 9 / 5 + 32
    return value / _FACTOR[key]


def unit(key, metric):
    """The unit name, such as "°F" or "mph". Empty for readings without one."""
    return (METRIC_UNIT if metric else US_UNIT).get(key, "")


def suffix(key, metric):
    """The unit as it follows a number: "°F" with no space, " mph" with one."""
    text = unit(key, metric)
    if not text or text.startswith("°") or text == "%":
        return text
    return " " + text


def format_value(key, value, metric, decimals=None):
    """Text such as "72.5 °F" or "22.5 °C". Metric shows one decimal unless decimals is given."""
    if value is None:
        return "--"
    v = convert(key, value, metric)
    if decimals is None and metric:
        decimals = 1
    text = f"{v:.{decimals}f}" if decimals is not None else f"{v:g}"
    name = unit(key, metric)
    return f"{text} {name}" if name else text


def speed_unit(metric):
    return "km/h" if metric else "mph"


def speed_factor(metric):
    """Multiply a mph value by this to get the chosen speed unit."""
    return _FACTOR["windspeedmph"] if metric else 1.0
