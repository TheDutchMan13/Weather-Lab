"""App name, live card labels, and the dashboard's colors.

The colors were copied from the dashboard's config.py (see SOURCES.md).
"""

APP_NAME = "Weather Lab"
APP_VERSION = "0.16.0"

# Live card choices: key -> (label, unit suffix). Keys match weatherlab/parse.py.
CARD_LABELS = {
    "tempf": ("Outdoor temperature", "°F"),
    "humidity": ("Humidity", "%"),
    "feelslikef": ("Feels like", "°F"),
    "dewpointf": ("Dew point", "°F"),
    "windspeedmph": ("Wind", "mph"),
    "windgustmph": ("Gust", "mph"),
    "winddir": ("Wind direction", "°"),
    "dailyrainin": ("Rain today", "in"),
    "rainratein": ("Rain rate", "in/hr"),
    "solarradiation": ("Solar", "W/m²"),
    "uv": ("UV index", ""),
    "tempinf": ("Indoor temperature", "°F"),
    "humidityin": ("Indoor humidity", "%"),
    "baromrelin": ("Pressure", "inHg"),
}

# Colors from the dashboard's config.py
ACCENT_COLOR = "#4a9eff"
RISK_COLORS = {
    "good": "#4ac880",
    "moderate": "#facc15",
    "unhealthy_sensitive": "#fb923c",
    "unhealthy": "#f87171",
    "very_unhealthy": "#dc2626",
    "hazardous": "#7f1d1d",
}
