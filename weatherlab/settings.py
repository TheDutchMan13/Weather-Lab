"""User settings stored as JSON in %APPDATA%\\WeatherLab\\settings.json.

API keys are NOT stored here. They go in Windows Credential Manager in a later phase.
"""

import ipaddress
import json
import os
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from weatherlab import stations

DEFAULT_CARDS = ["windgustmph", "dailyrainin", "tempinf"]  # temperature, humidity and wind are in the Last 24 hours row (0.37.44)


@dataclass
class Settings:
    station_ip: str = ""
    latitude: float | None = None
    longitude: float | None = None
    elevation_m: float = 0.0
    timezone: str = "UTC"
    nws_contact: str = ""  # optional; the National Weather Service asks apps to identify themselves
    lightning_value_is_km: bool = False  # set on if the station's lightning distance is really kilometres
    cwop_enabled: bool = False  # send readings to CWOP, which makes the location public. Off by default.
    cwop_callsign: str = ""
    wu_enabled: bool = False  # send readings to Weather Underground; the key is in Windows Credential Manager
    wu_station_id: str = ""
    pws_enabled: bool = False  # send readings to PWSweather; the key is in Windows Credential Manager
    pws_station_id: str = ""
    weathercloud_enabled: bool = False  # send readings to Weathercloud; the key is in Windows Credential Manager
    weathercloud_id: str = ""
    mqtt_enabled: bool = False  # publish readings to an MQTT broker such as Home Assistant's Mosquitto add-on
    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_user: str = ""  # the password is in Windows Credential Manager
    mqtt_prefix: str = "weatherlab/home"
    mqtt_discovery: bool = True  # send Home Assistant discovery messages so the sensors appear by themselves
    theme_mode: str = "auto"  # "auto", "light", or "dark"
    allow_network: bool = False  # let phones and other devices on the home network open the app
    live_cards: list[str] = field(default_factory=lambda: list(DEFAULT_CARDS))
    alert_rules: list[dict] = field(default_factory=list)  # see alert_rules.py
    units: str = "US"  # "US" or "Metric"; changes the display only, readings stay in US units
    color_scheme: str = "Default"  # see theme.SCHEMES
    compact: bool = False  # tighter spacing
    large_text: bool = False  # bigger text and tiles, for easier reading
    time_24h: bool = False  # show times as 14:30 instead of 2:30 PM
    chart_toolbar: bool = False  # keep the chart buttons visible, including save as picture
    tooltips: bool = True  # hover text on charts (the dashboard's 'Show helpful tooltips')
    animate: bool = True  # gauges sweep into place when a page loads (the dashboard's 'Animate gauges')
    backup_enabled: bool = True  # copy the database once a day
    backup_keep: int = 14  # how many copies to keep
    sensor_alerts: bool = True  # warn about low sensor batteries and weak signal
    digest_enabled: bool = True  # a short notification each morning about yesterday
    digest_hour: int = 7  # local hour the morning summary is sent
    api_enabled: bool = False  # the read-only API for the Android app; needs phones and devices to be allowed too
    api_port: int = 8600  # the port the API listens on
    home_briefing: bool = True  # show the briefing at the top of Home
    wide_cards: list[str] = field(default_factory=list)  # Home cards drawn across the whole row (0.37.42)
    gauges: str = "auto"  # the Gauges group on Home: "auto" (open on a computer, closed on a phone), "open" or "closed"
    checklist_hidden: bool = False  # hide the Getting started list on Home (0.37.49)
    briefing_notice: bool = False  # send today's briefing as a notification each morning
    briefing_hour: int = 7  # local hour the briefing is sent
    weekly_digest: bool = False  # a short summary of the last 7 days, sent on Mondays with the morning summary
    offline_alerts: bool = True  # notify when the station stops sending readings
    frost_alerts: bool = True  # notify about freezing nights in the forecast
    frost_threshold_f: float = 36.0  # forecast lows at or below this (Fahrenheit) trigger the freeze warning
    quiet_enabled: bool = False  # hold back non-urgent notifications during quiet hours
    quiet_start: int = 22  # quiet hours begin at this hour
    quiet_end: int = 6  # and end at this hour
    stuck_alerts: bool = True  # warn when outdoor temperature or humidity stops changing
    health_alerts: bool = True  # alert the phone when disk space runs out or a backup fails
    lightning_alerts: bool = False  # notify when lightning is close
    lightning_alert_miles: float = 5.0  # how close counts as close, in miles
    uv_alerts: bool = False  # notify when the UV index reaches the level below, once a day
    uv_alert_level: float = 8.0
    aqi_alerts: bool = False  # notify when AirNow's air quality index reaches the level below, once a day
    aqi_alert_level: float = 151.0  # 151 is 'unhealthy' on the US scale
    fire_alerts: bool = False  # notify when the fire weather index reaches the level below, once a day
    fire_alert_fwi: float = 21.0  # 21 is 'very high' on the Canadian fire weather scale
    rain_notices: bool = False  # notify when rain starts and when it stops
    ntfy_server: str = ""  # phone alerts server address; blank means ntfy.sh
    backup_copy_folder: str = ""  # also copy each backup here, such as a USB drive or synced folder
    update_url: str = ""  # optional address of a text file whose first line is the newest version
    nws_alerts: bool = False  # send new National Weather Service warnings and advisories to your phone and PC
    auto_reports: bool = False  # create last month's PDF report each month (and last year's in January)
    archive_after_days: int = 0  # move raw readings older than this into the archive table; 0 keeps them all
    noaa_station: str = ""  # NOAA station ID for the nearest weather station, found on the Import page
    noaa_station_name: str = ""


def settings_path() -> Path:
    """The settings file for the current station."""
    return stations.folder() / "settings.json"


def load_settings() -> Settings:
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return Settings()
    known = {f.name for f in fields(Settings)}
    return Settings(**{k: v for k, v in data.items() if k in known})


def save_settings(settings: Settings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")


def valid_ip(text: str) -> bool:
    try:
        ipaddress.ip_address(text)
        return True
    except ValueError:
        return False
