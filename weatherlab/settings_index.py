"""Find a setting (0.37.53): the settings people look for, and the tab each one is on.

The Find a setting box on Settings lists these; picking one opens its half of Settings and its tab. No Streamlit
here, so the tests can check every tab named below exists."""

# (what you'd look for, the tab it is on). The box filters on the name as you type.
ENTRIES: list[tuple[str, str]] = [
    ("Station IP address", "Station"),
    ("Timezone", "Station"),
    ("Location: latitude and longitude", "Station"),
    ("Elevation", "Station"),
    ("Contact email for forecasts", "Station"),
    ("Air quality key (AirNow)", "Air"),
    ("Lightning distance in kilometres", "Air"),
    ("CWOP uploads", "Uploads"),
    ("Weather Underground uploads", "Uploads"),
    ("PWSweather uploads", "Uploads"),
    ("Weathercloud uploads", "Uploads"),
    ("MQTT and Home Assistant", "Uploads"),
    ("Phones and other devices on my network", "Access"),
    ("Password for other devices", "Access"),
    ("Android app token", "Access"),
    ("Theme: light or dark", "Appearance"),
    ("Colour scheme", "Appearance"),
    ("Units", "Appearance"),
    ("Time format", "Appearance"),
    ("Compact spacing and larger text", "Appearance"),
    ("Tooltips and animated gauges", "Appearance"),
    ("Alert rules", "Alerts"),
    ("Low battery and weak signal warnings", "Alerts"),
    ("Morning summary and daily briefing", "Alerts"),
    ("Station stopped reporting", "Alerts"),
    ("Freeze warnings", "Alerts"),
    ("Quiet hours", "Alerts"),
    ("Lightning close by", "Alerts"),
    ("UV, air quality and fire danger notices", "Alerts"),
    ("Rain started and stopped", "Alerts"),
    ("National Weather Service warnings", "Alerts"),
    ("Phone alerts (ntfy)", "Phone alerts"),
    ("Update checks", "Updates"),
    ("Start with Windows", "Startup"),
]


def tab_of(name: str) -> str | None:
    """The tab a setting is on."""
    return dict(ENTRIES).get(name)
