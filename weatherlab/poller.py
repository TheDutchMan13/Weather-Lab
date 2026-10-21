"""Background thread that reads the station every POLL_SECONDS and stores each reading.

Streamlit reruns the page script on every interaction, so the poller is started
once per process (see app.py) and kept in st.cache_resource.

Every failure is recorded in `status` and the loop keeps going, so a bad read
or a database error never stops the thread silently.
"""

import json
import sqlite3
import threading
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from weatherlab import alert_rules, airquality, backup, cwop, mqtt_publish, pwsweather, uploads, weathercloud, wunderground, daily, digest, fire, forecast_check, gateway_sensors, history, lightning, nws, parse, quiet, station_watch, stuck, updates, record_alerts, secrets, storage, units
from weatherlab.config import APP_VERSION
from weatherlab.settings import load_settings

POLL_SECONDS = 30  # the gateway refreshes about every 16-60 seconds
ROLLUP_SECONDS = 300  # how often to rebuild the last few daily summaries
AQI_SECONDS = 1800  # AirNow updates about hourly
FIRE_SECONDS = 3600  # fire weather index is calculated once an hour
CWOP_SECONDS = 300  # CWOP's usual interval: one report every five minutes
UPLOAD_SECONDS = 300  # Weather Underground, PWSweather and Weathercloud: one upload every five minutes each
MQTT_SECONDS = 60  # MQTT: readings are published once a minute
DISCOVERY_SECONDS = 3600  # Home Assistant discovery messages are sent once an hour
ROLLUP_DAYS_BACK = 3
RECORD_REFRESH_SECONDS = 3600  # how often the all-time records reload from the daily summaries
BACKUP_CHECK_SECONDS = 3600  # how often to check whether a daily database backup is due
SENSOR_SECONDS = 1800  # how often to check sensor batteries and signal
FORECAST_SECONDS = 10800  # how often to save the forecast, so accuracy can be checked later
STUCK_SECONDS = 1800  # how often to check for an outdoor sensor that has stopped changing
ENV_SECONDS = 300  # how often to check UV, air quality and fire danger
UPDATE_SECONDS = 86400  # how often to check for a newer version


@dataclass
class PollStatus:
    started: float | None = None
    last_attempt: float | None = None
    last_ok: float | None = None
    last_error: str = ""
    skipped: int = 0
    aqi_error: str = ""
    recent_alerts: list = field(default_factory=list)  # (timestamp, message), newest first
    cwop_error: str = ""
    cwop_last: float | None = None
    wu_error: str = ""
    wu_last: float | None = None
    pws_error: str = ""
    pws_last: float | None = None
    wc_error: str = ""
    wc_last: float | None = None
    mqtt_error: str = ""
    mqtt_last: float | None = None
    backup_error: str = ""
    sensor_error: str = ""
    forecast_error: str = ""
    update_available: str = ""
    skipped_log: list = field(default_factory=list)  # (timestamp, reason), newest first


class Poller(threading.Thread):
    def __init__(self, station: str = "main") -> None:
        super().__init__(daemon=True, name=f"weatherlab-poller-{station}")
        self.station = station
        self._stop_event = threading.Event()
        self.status = PollStatus()
        self._prev: tuple[float, dict] | None = None
        self._last_rollup = 0.0
        self._last_aqi = 0.0
        self._last_fire = 0.0
        self._fired: dict = {}
        self._last_cwop = 0.0
        self._last_wu = 0.0
        self._last_extra = 0.0
        self._last_mqtt = 0.0
        self._last_discovery = 0.0
        self._best: dict | None = None
        self._best_at = 0.0
        self._record_day: dict = {}
        self._last_backup = 0.0
        self._last_sensors = 0.0
        self._last_forecast = 0.0
        self._digest_day = None
        self._sensor_sent: dict = {}
        self._offline = False
        self._frost_sent: set = set()
        self._quiet = False
        self._last_stuck = 0.0
        self._last_strike_alert = 0.0
        self._db = None
        self._raining = None
        self._last_env = 0.0
        self._last_update = 0.0
        self._update_sent: set = set()

    def stop(self) -> None:
        """Ask the collector to finish its current pass and exit."""
        self._stop_event.set()

    def run(self) -> None:
        from weatherlab import stations
        stations.set_current(self.station)
        self.status.started = time.time()
        db = None
        while not self._stop_event.is_set():
            try:
                if db is None:
                    db = storage.connect()
                self._db = db
                s = load_settings()
                self._quiet = s.quiet_enabled and quiet.is_quiet(datetime.now(_zone(s)).hour, s.quiet_start, s.quiet_end)
                if s.station_ip.strip():
                    self._poll_once(db, s)
                if time.time() - self._last_rollup > ROLLUP_SECONDS:
                    self._rollup(db, s)
                if time.time() - self._last_aqi > AQI_SECONDS:
                    self._aqi(db, s)
                if time.time() - self._last_fire > FIRE_SECONDS:
                    self._fire(db, s)
                if s.cwop_enabled and time.time() - self._last_cwop > CWOP_SECONDS:
                    self._cwop(db, s)
                if s.wu_enabled and time.time() - self._last_wu > UPLOAD_SECONDS:
                    self._wu(db, s)
                if (s.pws_enabled or s.weathercloud_enabled) and time.time() - self._last_extra > UPLOAD_SECONDS:
                    self._extra_uploads(db, s)
                if s.mqtt_enabled and time.time() - self._last_mqtt > MQTT_SECONDS:
                    self._mqtt(db, s)
                if s.backup_enabled and time.time() - self._last_backup > BACKUP_CHECK_SECONDS:
                    self._backup(s)
                if s.sensor_alerts and s.station_ip.strip() and time.time() - self._last_sensors > SENSOR_SECONDS:
                    self._sensors(s)
                if s.latitude is not None and s.longitude is not None and time.time() - self._last_forecast > FORECAST_SECONDS:
                    self._forecast(db, s)
                if s.digest_enabled:
                    self._digest(db, s)
                if s.offline_alerts and s.station_ip.strip():
                    self._watch_station()
                if s.stuck_alerts and s.station_ip.strip() and time.time() - self._last_stuck > STUCK_SECONDS:
                    self._stuck(db, s)
                if time.time() - self._last_env > ENV_SECONDS:
                    self._environment(db, s)
                if s.update_url.strip() and time.time() - self._last_update > UPDATE_SECONDS:
                    if self.station == "main": self._update_check(s)
            except Exception as exc:  # keep the thread alive no matter what
                self.status.last_error = f"Poller error: {type(exc).__name__}: {exc}"
                traceback.print_exc()
                db = None  # reconnect next time
            self._stop_event.wait(POLL_SECONDS)

    def _poll_once(self, db, s) -> None:
        ip = s.station_ip.strip()
        self.status.last_attempt = time.time()
        try:
            live = parse.fetch(ip)
        except (OSError, ValueError) as exc:
            self.status.last_error = f"Can't reach the station at {ip} ({type(exc).__name__})."
            return
        reading = parse.clean(parse.parse_livedata(live))
        if not parse.plausible(reading, self._prev):
            self.status.skipped += 1
            self.status.skipped_log = ([(time.time(), "A reading was skipped because its values did not look plausible.")]
                                       + self.status.skipped_log)[:20]
            self.status.last_error = "Skipped an implausible reading."
            return
        now = time.time()
        storage.store_reading(db, reading, now)
        self._prev = (now, reading)
        for text in alert_rules.evaluate(s.alert_rules, reading, now, self._fired, units.is_metric(s.units)):
            self._announce(text, severe=True)
        self._records(db, s, reading, now)
        self._rain_notice(s, reading)
        self.status.last_ok = now
        self.status.last_error = ""

        tz = _zone(s)
        strike = lightning.parse_lightning(live, tz, datetime.now(tz), s.lightning_value_is_km)
        if strike:
            storage.store_strike(db, strike["ts"], strike["distance_mi"])
            if s.lightning_alerts and strike["distance_mi"] <= s.lightning_alert_miles and time.time() - self._last_strike_alert > 600:
                self._last_strike_alert = time.time()
                metric = units.is_metric(s.units)
                shown, unit = (strike["distance_mi"] * 1.609344, "km") if metric else (strike["distance_mi"], "miles")
                self._announce(f"Lightning about {shown:.0f} {unit} away.", severe=True)

    def _records(self, db, s, reading: dict, now: float) -> None:
        """Announce a new all-time record. Each record is announced at most once a day."""
        if self._best is None or time.time() - self._best_at > RECORD_REFRESH_SECONDS:
            fresh = record_alerts.bests(history.all_daily(db))
            self._best = record_alerts.combine(fresh, self._best or {})
            self._best_at = time.time()
        today = datetime.now(_zone(s)).date()
        for key, value, text in record_alerts.check(self._best, reading, units.is_metric(s.units)):
            self._best[key] = value  # keep the best seen so far, even when it isn't announced again
            if self._record_day.get(key) == today:
                continue
            self._record_day[key] = today
            self._announce(text, severe=True)

    def _rollup(self, db, s) -> None:
        """Rebuild summaries for the last few finished days (fills gaps after a restart)."""
        self._last_rollup = time.time()
        tz = _zone(s)
        today = datetime.now(tz).date()
        days = [today - timedelta(days=i) for i in range(1, ROLLUP_DAYS_BACK + 1)]
        daily.rollup_days(db, days, s.latitude or 0.0, s.longitude or 0.0, s.elevation_m, tz, today)

    def _backup(self, s) -> None:
        """Copy the database once a day and keep the newest few copies."""
        self._last_backup = time.time()
        try:
            backup.run_if_due(storage.db_path(), s.backup_keep, datetime.now(), s.backup_copy_folder)
            self.status.backup_error = ""
        except (OSError, sqlite3.Error) as exc:
            self.status.backup_error = f"Database backup failed: {exc}"

    def _sensors(self, s) -> None:
        """Warn about low sensor batteries and weak signal. Each warning is sent once a day."""
        self._last_sensors = time.time()
        try:
            sensors = gateway_sensors.read(s.station_ip.strip())
        except (OSError, ValueError):
            self.status.sensor_error = "Can't read sensor status from the station."
            return
        self.status.sensor_error = ""
        today = datetime.now(_zone(s)).date()
        for text in gateway_sensors.warnings(sensors):
            if self._sensor_sent.get(text) == today:
                continue
            if self._announce(text):
                self._sensor_sent[text] = today

    def _announce(self, text: str, severe: bool = False) -> bool:
        """Show the message in the app and send a notification. Non-urgent messages wait during quiet hours."""
        if self._quiet and not severe:
            return False
        now = time.time()
        self.status.recent_alerts = ([(now, text)] + self.status.recent_alerts)[:20]
        if self._db is not None:
            try:
                storage.log_alert(self._db, now, text)
            except sqlite3.Error:
                pass
        alert_rules.notify("Weather Lab", text)
        from weatherlab import push
        push.send_async(text)
        return True

    def _forecast(self, db, s) -> None:
        """Save the NWS daytime high for each coming day, so the Forecast page can check it later."""
        self._last_forecast = time.time()
        try:
            pts = nws.points(s.latitude, s.longitude, s.nws_contact)
            periods = nws.forecast_daily(pts["forecast"], s.nws_contact)
            storage.store_forecasts(db, forecast_check.combine(forecast_check.highs_from_periods(periods, _zone(s)),
                                                              forecast_check.pops_from_periods(periods, _zone(s))))
            if s.frost_alerts:
                self._frost(periods, s)
            self.status.forecast_error = ""
        except (nws.NwsError, KeyError, ValueError) as exc:
            self.status.forecast_error = str(exc) or type(exc).__name__

    def _watch_station(self) -> None:
        """One notification when readings stop for 15 minutes, and one when they come back."""
        self._offline, text = station_watch.check(self._offline, self.status.last_ok or self.status.started, time.time())
        if text:
            self._announce(text, severe=True)

    def _frost(self, periods, s) -> None:
        """Warn once per night when the forecast low is at or below the freeze threshold."""
        tz = _zone(s)
        metric = units.is_metric(s.units)
        for day, low in forecast_check.frost_nights(periods, tz, datetime.now(tz), s.frost_threshold_f):
            if day in self._frost_sent:
                continue
            self._frost_sent.add(day)
            when = datetime.fromisoformat(day).strftime("%b %d")
            self._announce(f"Freeze risk: a low of {units.format_value('tempf', low, metric, 0)} is forecast "
                           f"for the night of {when}. Cover or bring in plants.", severe=True)

    def _stuck(self, db, s) -> None:
        """Warn when outdoor temperature or humidity has not changed for three hours. Once a day per sensor."""
        self._last_stuck = time.time()
        rows = storage.readings_between(db, self._last_stuck - 3 * 3600, self._last_stuck + 1)
        today = datetime.now(_zone(s)).date()
        for key in stuck.stuck_keys(rows):
            text = f"The {stuck.LABELS[key]} has not changed in 3 hours. The sensor may be stuck or have lost contact."
            if self._sensor_sent.get(text) == today:
                continue
            if self._announce(text):
                self._sensor_sent[text] = today

    def _rain_notice(self, s, reading: dict) -> None:
        """Notify when rain starts and when it stops (only when the user has turned this on)."""
        raining = (reading.get("rainratein") or 0.0) > 0
        was, self._raining = self._raining, raining
        if s.rain_notices and was is not None and raining != was:
            self._announce("Rain has started." if raining else "Rain has stopped.")

    def _environment(self, db, s) -> None:
        """UV, air quality and fire danger notices. Each kind is sent at most once a day."""
        self._last_env = time.time()
        today = datetime.now(_zone(s)).date()
        checks = []
        latest = storage.latest(db)
        if latest and time.time() - latest[0] <= 900:
            uv = latest[1].get("uv")
            if s.uv_alerts and uv is not None and uv >= s.uv_alert_level:
                checks.append(("uv", f"UV index is {uv:.0f}. Use sun protection outdoors."))
        aqi = storage.latest_aqi(db)
        if s.aqi_alerts and aqi and (aqi[1].get("aqi") or 0) >= s.aqi_alert_level:
            category = str(aqi[1].get("category", "unhealthy")).lower()
            checks.append(("aqi", f"Air quality is {category} (AQI {aqi[1]['aqi']})."))
        fire = storage.latest_fire(db)
        if s.fire_alerts and fire and (fire.get("fwi") or 0) >= s.fire_alert_fwi:
            checks.append(("fire", f"Fire danger is high (fire weather index {fire['fwi']:.0f}). "
                                   "Avoid open flames and check local burn rules."))
        for kind, text in checks:
            if self._sensor_sent.get(kind) == today:
                continue
            if self._announce(text):
                self._sensor_sent[kind] = today

    def _update_check(self, s) -> None:
        """Once a day, see whether the address the user gave names a newer version. Tells the user once per version."""
        self._last_update = time.time()
        try:
            newer = updates.check(s.update_url.strip(), APP_VERSION)
        except (OSError, ValueError):
            return
        self.status.update_available = newer or ""
        if newer and newer not in self._update_sent:
            self._update_sent.add(newer)
            self._announce(f"Weather Lab {newer} is available. Get it from the place you got this copy.")

    def _digest(self, db, s) -> None:
        """Once a day, after the chosen hour, send a short summary of yesterday."""
        now = datetime.now(_zone(s))
        if self._quiet or now.hour < s.digest_hour or self._digest_day == now.date():
            return
        self._digest_day = now.date()
        yesterday = now.date() - timedelta(days=1)
        held = db.execute("SELECT data FROM daily WHERE date = ?", (yesterday.isoformat(),)).fetchone()
        if not held:
            return
        line = digest.text(yesterday.strftime("%b %d"), json.loads(held[0]), units.is_metric(s.units))
        if line:
            self._announce(line)

    def _cwop(self, db, s) -> None:
        """Send the latest reading to CWOP. Only runs when the user has turned CWOP on."""
        self._last_cwop = time.time()
        latest = storage.latest(db)
        if latest is None or time.time() - latest[0] > 1800:
            self.status.cwop_error = "No recent reading to send to CWOP."
            return
        try:
            cwop.send_reading(s.cwop_callsign, latest[1], s.latitude, s.longitude)
            self.status.cwop_last = time.time()
            self.status.cwop_error = ""
        except cwop.CwopError as exc:
            self.status.cwop_error = str(exc)

    def _wu(self, db, s) -> None:
        """Upload the latest reading to Weather Underground. Only runs when the user has turned it on."""
        self._last_wu = time.time()
        latest = storage.latest(db)
        if latest is None or time.time() - latest[0] > 1800:
            self.status.wu_error = "No recent reading to send to Weather Underground."
            return
        try:
            wunderground.send_reading(s.wu_station_id, secrets.get_key(wunderground.KEY_NAME), latest[1])
            self.status.wu_last = time.time()
            self.status.wu_error = ""
        except uploads.UploadError as exc:
            self.status.wu_error = str(exc)

    def _extra_uploads(self, db, s) -> None:
        """Send the latest reading to PWSweather and Weathercloud. Each one only runs when the user has turned it on."""
        self._last_extra = time.time()
        latest = storage.latest(db)
        fresh = latest is not None and time.time() - latest[0] <= 1800
        targets = []
        if s.pws_enabled:
            targets.append(("pws", lambda r: pwsweather.send_reading(s.pws_station_id, secrets.get_key(pwsweather.KEY_NAME), r)))
        if s.weathercloud_enabled:
            targets.append(("wc", lambda r: weathercloud.send_reading(s.weathercloud_id, secrets.get_key(weathercloud.KEY_NAME), r)))
        for prefix, send in targets:
            if not fresh:
                setattr(self.status, f"{prefix}_error", "No recent reading to send.")
                continue
            try:
                send(latest[1])
                setattr(self.status, f"{prefix}_last", time.time())
                setattr(self.status, f"{prefix}_error", "")
            except uploads.UploadError as exc:
                setattr(self.status, f"{prefix}_error", str(exc))

    def _mqtt(self, db, s) -> None:
        """Publish the latest reading to the MQTT broker, with Home Assistant discovery once an hour."""
        self._last_mqtt = time.time()
        try:
            latest = storage.latest(db)
            if latest is None or time.time() - latest[0] > 1800:
                self.status.mqtt_error = "No recent reading to publish."
                return
            messages = mqtt_publish.readings(s.mqtt_prefix, latest[1])
            discovering = s.mqtt_discovery and time.time() - self._last_discovery > DISCOVERY_SECONDS
            if discovering:
                messages = mqtt_publish.discovery(s.mqtt_prefix) + messages
            mqtt_publish.send(s.mqtt_host, s.mqtt_port, s.mqtt_user, secrets.get_key(mqtt_publish.KEY_NAME),
                              messages, client_id=f"weatherlab-{self.station}")
            if discovering:
                self._last_discovery = time.time()
            self.status.mqtt_last = time.time()
            self.status.mqtt_error = ""
        except uploads.UploadError as exc:
            self.status.mqtt_error = str(exc)

    def _fire(self, db, s) -> None:
        """Fire weather index from the latest reading, with the NWS forecast when the location is in the US."""
        self._last_fire = time.time()
        latest = storage.latest(db)
        if latest is None or time.time() - latest[0] > 7200:
            return
        _, data = latest
        temp, hum = data.get("tempf"), data.get("humidity")
        wind, rain = data.get("windspeedmph"), data.get("dailyrainin")
        if None in (temp, hum, wind, rain):
            return
        tz = _zone(s)
        now = datetime.now(tz)

        forecast = {}
        if s.latitude is not None and s.longitude is not None:
            try:
                pts = nws.points(s.latitude, s.longitude, s.nws_contact)
                if pts.get("forecastHourly"):
                    hourly = nws.forecast_hourly(pts["forecastHourly"], s.nws_contact, limit=156)
                    forecast = fire.forecast_noon(hourly, tz)
            except nws.NwsError:
                forecast = {}  # keep the current index even when the forecast isn't available

        obs = {"temp_f": temp, "humidity": hum, "wind_mph": wind, "rain_in": rain}
        obs["days_since_rain"] = fire.days_since_rain(storage.recent_daily_rain(db), now.date(), rain)
        record = fire.build(obs, storage.latest_fire(db) or {}, now, forecast)
        storage.store_fire(db, record)

    def _aqi(self, db, s) -> None:
        """Fetch air quality from AirNow, if a key is saved and a location is set."""
        self._last_aqi = time.time()
        key = secrets.get_key("airnow")
        if not key or s.latitude is None or s.longitude is None:
            return
        try:
            data = airquality.fetch(s.latitude, s.longitude, key)
            if data:
                storage.store_aqi(db, data)
            self.status.aqi_error = ""
        except airquality.AirNowError as exc:
            self.status.aqi_error = str(exc)


def _zone(s) -> ZoneInfo:
    try:
        return ZoneInfo(s.timezone)
    except Exception:
        return ZoneInfo("UTC")
