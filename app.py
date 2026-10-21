"""Weather Lab: Streamlit entry point. Run with: streamlit run app.py (or open WeatherLab.exe)."""

import calendar
import html
import io
import json
import os
import sqlite3
import time
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, available_timezones

import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from weatherlab import (alert_map, alert_rules, astro, auth, autofit, autostart, charts, comfort, daily, dials, ecowitt_import, gateway_sensors, gauges, health, hero, heat_safety, history, history_compare, airquality, importer, coverage, backup, ask, dew, digest, discover, forecast_check, parse, rain_events, motion, network, nws, rain_calendar, replay, report, secrets, sparks, station_status, storage, sun_uv, theme, tropics, units, whats_new, wind_rose, wx_icons, yearly)
from weatherlab.config import APP_NAME, APP_VERSION, CARD_LABELS, RISK_COLORS
from weatherlab import forecast_view, health_check, lightning_history, pwsweather, push, stations, updates, weathercloud, wunderground
from weatherlab.poller import Poller
from weatherlab.settings import Settings, load_settings, save_settings, settings_path, valid_ip

REFRESH_SECONDS = 30
GROUPS = {  # sidebar sections, each with its pages
    "Now": ["Live", "Sensors", "Status", "Health check", "Alert history", "What's New"],
    "History": ["Daily", "History", "Records", "Coverage", "Rankings", "Rewind", "Climate charts", "My year", "Rain calendar", "Rain events", "Ask", "Unusual days", "Replay", "Reports"],
    "Outlook": ["Forecast", "Heat", "Wind", "Sun", "Astronomy"],
    "Hazards": ["Air", "Fire", "Lightning", "Tropics", "Radar"],
    "Data and setup": ["Import", "Export", "Setup", "Settings", "Stations"],
}


@st.cache_resource
def _collectors() -> dict:
    """The background collector for each station, started once and kept for as long as the app runs."""
    return {}


def start_poller() -> Poller:
    """The collector for the station on screen. Starts one for each station that doesn't have one running yet,
    and stops the ones for stations that were removed."""
    collectors = _collectors()
    ids = stations.ids()
    for sid in list(collectors):
        if sid not in ids:
            collectors.pop(sid).stop()
    for sid in ids:
        if sid not in collectors or not collectors[sid].is_alive():
            collectors[sid] = Poller(sid)
            collectors[sid].start()
    return collectors[stations.current()]


def _clock(ts: float) -> str:
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _conv(key: str, values: list, metric: bool) -> list:
    """Each US value converted to the chosen units. None stays None."""
    return [units.convert(key, v, metric) for v in values]


def _tile(label: str, value: str, note: str = "") -> str:
    body = theme.tile_html(html.escape(label), html.escape(value))
    if note:
        body = body.replace("</div></div>", f'</div><div class="wl-label">{html.escape(note)}</div></div>')
    return body


def _tz(s: Settings) -> ZoneInfo:
    try:
        return ZoneInfo(s.timezone)
    except Exception:
        return ZoneInfo("UTC")


# ---------------------------------------------------------------- Setup

def _password_section() -> None:
    st.markdown("**Password for other devices**")
    st.caption("A password is set." if auth.password_set()
               else "No password yet. Other devices can't open Weather Lab until you set one.")
    new = st.text_input(f"New password (at least {auth.MIN_LENGTH} characters)", type="password", key="new-password")
    again = st.text_input("Type it again", type="password", key="new-password-again")
    if st.button("Save password"):
        if len(new) < auth.MIN_LENGTH:
            st.error(f"Use at least {auth.MIN_LENGTH} characters.")
        elif new != again:
            st.error("The two passwords don't match.")
        else:
            try:
                auth.set_password(new)
                st.success("Password saved.")
            except Exception as exc:
                st.error(f"Couldn't save the password: {exc}")
    if auth.password_set() and st.button("Remove password"):
        auth.clear_password()
        st.rerun()


def _station_tools(s: Settings) -> None:
    """Test the connection to the station, or look for it on the local network."""
    with st.expander("Find or test the station"):
        if st.button("Test the connection", key="station_test"):
            ip = s.station_ip.strip()
            if not ip:
                st.warning("Enter the station IP address and save first.")
            else:
                try:
                    reading = parse.clean(parse.parse_livedata(parse.fetch(ip)))
                    shown = units.format_value("tempf", reading.get("tempf"), units.is_metric(s.units), 1)
                    st.success(f"Connected to {ip}. Outdoor temperature reads {shown}.")
                except (OSError, ValueError) as exc:
                    st.error(f"Couldn't reach the station at {ip} ({type(exc).__name__}).")
        if st.button("Find the station on my network", key="station_find"):
            with st.spinner("Looking on your network. This takes a few seconds."):
                st.session_state["found_station"] = discover.find()
            if not st.session_state["found_station"]:
                st.warning("No station found on this network. It may be asleep, or on another network range. "
                           "Enter its address by hand.")
        for ip in st.session_state.get("found_station", []):
            if st.button(f"Use {ip}", key=f"use_station_{ip}"):
                save_settings(replace(s, station_ip=ip))
                st.success(f"Saved {ip}. Reload the page to see it in the station address box.")


def _appearance_section(s: Settings) -> None:
    """Theme, colours, units, and the Live readings. Saved as soon as a choice changes."""
    st.subheader("Appearance")
    modes = ["auto", "light", "dark"]
    theme_mode = st.radio("Theme", modes, index=modes.index(s.theme_mode), horizontal=True, key="ap_theme",
                          format_func=lambda m: {"auto": "Automatic", "light": "Light", "dark": "Dark"}[m])
    schemes = list(theme.SCHEMES)
    color_scheme = st.selectbox("Colour scheme", schemes,
                                index=schemes.index(s.color_scheme) if s.color_scheme in schemes else 0, key="ap_scheme")
    units_choice = st.radio("Units", units.CHOICES,
                            index=units.CHOICES.index(s.units) if s.units in units.CHOICES else 0,
                            horizontal=True, key="ap_units",
                            help="US: °F, mph and inches. Metric: °C, km/h and millimetres. Every page and chart "
                                 "follows this, except export files, which stay in US units, and the Ask page, "
                                 "which reads questions in °F.")
    tooltips = st.checkbox("Show helpful tooltips", value=s.tooltips, help="Hover text on charts.", key="ap_tooltips")
    animate = st.checkbox("Animate gauges", value=s.animate, help="Gauges sweep into place when a page loads.",
                          key="ap_animate")
    compact = st.checkbox("Compact spacing", value=s.compact, help="Tighter spacing between tiles on the Live page.",
                          key="ap_compact")
    large = st.checkbox("Larger text", value=s.large_text,
                        help="Bigger text and tiles, for easier reading on a phone or from a distance.", key="ap_large")
    toolbar = st.checkbox("Always show the chart buttons", value=s.chart_toolbar,
                          help="Shows the buttons on charts all the time instead of only on hover. "
                               "The camera button saves the chart as a PNG picture.", key="ap_toolbar")
    cards = st.multiselect("Live readings", options=list(CARD_LABELS), default=s.live_cards,
                           format_func=lambda k: CARD_LABELS[k][0], key="ap_cards")
    current = (theme_mode, color_scheme, units_choice, tooltips, animate, compact, tuple(cards), large, toolbar)
    saved = (s.theme_mode, s.color_scheme, s.units, s.tooltips, s.animate, s.compact, tuple(s.live_cards),
             s.large_text, s.chart_toolbar)
    if current != saved:
        save_settings(replace(s, theme_mode=theme_mode, color_scheme=color_scheme, units=units_choice,
                              tooltips=tooltips, animate=animate, compact=compact, live_cards=list(cards),
                              large_text=large, chart_toolbar=toolbar))
        st.rerun()


def _startup_section() -> None:
    """Start Weather Lab when Windows signs in. Only available in the Windows app."""
    st.subheader("Startup")
    can_autostart = autostart.supported()
    current = autostart.is_enabled()
    on = st.checkbox("Start Weather Lab when I sign in to Windows", value=current, disabled=not can_autostart,
                     key="startup_on",
                     help=None if can_autostart else "Available in the Windows app (WeatherLab.exe).")
    if can_autostart and on != current:
        try:
            autostart.set_enabled(on)
        except OSError as exc:
            st.error(f"Couldn't change the sign-in setting: {exc}")


@st.cache_data(ttl=300, show_spinner=False)
def _tailscale_address() -> str | None:
    """This PC's Tailscale address, looked up at most every five minutes."""
    return network.tailscale_address()


def _phone_alerts_section(s: Settings) -> None:
    """Alerts on your phone through the free ntfy app. The topic is kept in Windows Credential Manager."""
    st.subheader("Phone alerts (ntfy)")
    st.caption("Install the free ntfy app on your phone, then add the topic below to it. Alerts reach the phone "
               "while this PC is on and online. Anyone who knows the topic can read the alerts, so keep it private.")
    server = st.text_input("ntfy server (leave blank for ntfy.sh)", value=s.ntfy_server, key="ph_server",
                           help="Only change this if you run your own ntfy server.")
    if server.strip() != s.ntfy_server.strip():
        save_settings(replace(s, ntfy_server=server.strip()))
    topic = secrets.get_key(push.TOPIC_KEY)
    if topic:
        st.code(topic, language=None)
    left, middle, right = st.columns(3)
    if left.button("Make a new topic", help="Replaces the current topic. Add the new one to the ntfy app."):
        secrets.set_key(push.TOPIC_KEY, push.new_topic())
        st.rerun()
    if middle.button("Send a test", disabled=not topic):
        if push.send(server.strip(), topic, "Weather Lab", "Test alert from Weather Lab."):
            st.success("Sent. Check the ntfy app on your phone.")
        else:
            st.warning("Couldn't send it. Check the internet connection and the server address.")
    if right.button("Remove topic", disabled=not topic):
        secrets.set_key(push.TOPIC_KEY, "")
        st.rerun()


def _updates_section(s: Settings) -> None:
    """Looks for a newer version at the address the user gives, and can download and run its installer."""
    st.subheader("Updates")
    st.caption(f"You have Weather Lab {APP_VERSION}.")
    url = st.text_input("Update address (optional)", value=s.update_url, key="up_url",
                        help="Where Weather Lab looks for the newest version: the latest.json file that "
                             "build_installer.py writes, kept beside the installer. Leave blank to skip updates.")
    if url.strip() != s.update_url.strip():
        save_settings(replace(s, update_url=url.strip()))
    if st.button("Check for updates", disabled=not url.strip()):
        try:
            st.session_state["update_info"] = updates.latest(url.strip(), APP_VERSION)
            st.session_state["update_checked"] = True
        except (OSError, ValueError) as exc:
            st.session_state["update_info"] = None
            st.session_state["update_checked"] = False
            st.error(f"Couldn't read the update address: {exc}")
    info = st.session_state.get("update_info")
    if info is None:
        if st.session_state.get("update_checked"):
            st.success("You have the newest version.")
        return
    st.info(f"Weather Lab {info['version']} is available.")
    if not info["file"]:
        st.caption("This address doesn't name an installer yet. Put the latest.json file from the newest build beside "
                   "the installer, then check again.")
        return
    if st.button(f"Download and install {info['version']}"):
        try:
            path = updates.download(info, stations.base_dir() / "updates")
            updates.start_installer(path)
        except (OSError, ValueError) as exc:
            st.error(f"The update didn't start: {exc}")
        else:
            st.success("The installer is running. Weather Lab will close, update, and open again. "
                       "If it doesn't reopen, start it from the Start menu.")


def settings_page() -> None:
    s = load_settings()
    st.markdown(theme.title_html("Settings"), unsafe_allow_html=True)
    look_tab, alerts_tab, phone_tab, updates_tab, backups_tab, start_tab = st.tabs(
        ["Appearance", "Alerts", "Phone alerts", "Updates", "Backups", "Startup"])
    with look_tab:
        _appearance_section(s)
    with alerts_tab:
        _alert_rules_section()
        _notifications_section(s)
        _quiet_section(s)
        _alert_extras_section(s)
    with phone_tab:
        _phone_alerts_section(s)
    with updates_tab:
        _updates_section(s)
    with backups_tab:
        _backups_section(s)
    with start_tab:
        _startup_section()


def setup_page() -> None:
    st.markdown(theme.title_html("Setup"), unsafe_allow_html=True)
    s = load_settings()
    _station_tools(s)
    (station_tab, air_tab, cwop_tab, wu_tab, other_tab, phone_tab) = st.tabs(
        ["Station", "Air and lightning", "CWOP", "Weather Underground", "Other services", "Phone access"])

    with station_tab:
        ip = st.text_input("Station IP address", value=s.station_ip, placeholder="for example 192.168.1.224",
                           help="Shown on the GW2000's web page or in your router's device list.")
        zones = sorted(available_timezones())
        tz = st.selectbox("Timezone", zones, index=zones.index(s.timezone) if s.timezone in zones else 0)
        lat = st.number_input("Latitude", value=float(s.latitude or 0.0), min_value=-90.0, max_value=90.0,
                              format="%.5f", help="Used for sun hours, day summaries, forecasts and air quality.")
        lon = st.number_input("Longitude", value=float(s.longitude or 0.0), min_value=-180.0, max_value=180.0,
                              format="%.5f")
        elev = st.number_input("Elevation (meters)", value=float(s.elevation_m), min_value=-500.0,
                               max_value=9000.0, step=1.0)
        contact = st.text_input("Contact email (optional)", value=s.nws_contact,
                                help="Sent to the National Weather Service with forecast requests.")
        if s.latitude is None or s.longitude is None:
            st.caption("Set your latitude and longitude so sun hours and forecasts can be calculated.")

    with air_tab:
        st.subheader("Air quality (optional)")
        has_key = bool(secrets.get_key("airnow"))
        airnow_key = st.text_input(
            "AirNow API key", type="password",
            placeholder="Saved in Windows Credential Manager" if has_key else "Paste your free AirNow key",
            help="Get a free key from the AirNow API website. It is stored in Windows Credential Manager, not in a file.")
        remove_key = st.checkbox("Remove the saved AirNow key", value=False, disabled=not has_key)
        st.subheader("Lightning")
        km = st.checkbox("The station's lightning distance is in kilometres", value=s.lightning_value_is_km,
                         help="Some GW2000 firmware labels kilometres as miles. Turn this on if the distances look too small.")

    with cwop_tab:
        st.subheader("CWOP (optional, public)")
        cwop_on = st.checkbox(
            "Send my readings to CWOP",
            value=s.cwop_enabled,
            help="The Citizen Weather Observer Program shows your station on public weather maps such as aprs.fi. "
                 "Your station's location becomes public. Off by default.",
        )
        cwop_call = st.text_input("CWOP callsign", value=s.cwop_callsign,
                                  placeholder="for example CW1234 or your amateur callsign")
        if cwop_on:
            cwop_status = start_poller().status
            if cwop_status.cwop_error:
                st.warning(cwop_status.cwop_error)
            elif cwop_status.cwop_last:
                st.caption(f"Last sent to CWOP {_clock(cwop_status.cwop_last)}")

    with wu_tab:
        st.subheader("Weather Underground (optional, public)")
        wu_on = st.checkbox(
            "Send my readings to Weather Underground",
            value=s.wu_enabled,
            help="Weather Underground shows your station on its public map. Get the station ID and key from your "
                 "station's page on wunderground.com. Off by default.",
        )
        wu_id = st.text_input("Station ID", value=s.wu_station_id, placeholder="for example KAZPHOEN123")
        wu_key_saved = bool(secrets.get_key(wunderground.KEY_NAME))
        wu_key = st.text_input(
            "Station key", type="password",
            placeholder="Saved in Windows Credential Manager" if wu_key_saved else "Paste your station key",
            help="Stored in Windows Credential Manager, not in a file.")
        remove_wu_key = st.checkbox("Remove the saved Weather Underground key", value=False, disabled=not wu_key_saved)
        if wu_on:
            wu_status = start_poller().status
            if wu_status.wu_error:
                st.warning(wu_status.wu_error)
            elif wu_status.wu_last:
                st.caption(f"Last sent to Weather Underground {_clock(wu_status.wu_last)}")

    with other_tab:
        st.subheader("PWSweather (optional, public)")
        pws_on = st.checkbox("Send my readings to PWSweather", value=s.pws_enabled,
                             help="PWSweather shows your station on its public map. Get the station ID and key from your "
                                  "PWSweather account. Off by default.")
        pws_id = st.text_input("PWSweather station ID", value=s.pws_station_id)
        pws_key_saved = bool(secrets.get_key(pwsweather.KEY_NAME))
        pws_key = st.text_input("PWSweather station key", type="password",
                                placeholder="Saved in Windows Credential Manager" if pws_key_saved else "Paste your station key")
        remove_pws_key = st.checkbox("Remove the saved PWSweather key", value=False, disabled=not pws_key_saved)
        if pws_on:
            pws_status = start_poller().status
            if pws_status.pws_error:
                st.warning(pws_status.pws_error)
            elif pws_status.pws_last:
                st.caption(f"Last sent to PWSweather {_clock(pws_status.pws_last)}")
        st.subheader("Weathercloud (optional, public)")
        wc_on = st.checkbox("Send my readings to Weathercloud", value=s.weathercloud_enabled,
                            help="Weathercloud shows your station on its public map. Get the device ID and key from your "
                                 "Weathercloud account. Off by default.")
        wc_id = st.text_input("Weathercloud device ID", value=s.weathercloud_id)
        wc_key_saved = bool(secrets.get_key(weathercloud.KEY_NAME))
        wc_key = st.text_input("Weathercloud device key", type="password",
                               placeholder="Saved in Windows Credential Manager" if wc_key_saved else "Paste your device key")
        remove_wc_key = st.checkbox("Remove the saved Weathercloud key", value=False, disabled=not wc_key_saved)
        if wc_on:
            wc_status = start_poller().status
            if wc_status.wc_error:
                st.warning(wc_status.wc_error)
            elif wc_status.wc_last:
                st.caption(f"Last sent to Weathercloud {_clock(wc_status.wc_last)}")

    with phone_tab:
        st.subheader("Phones and other devices")
        allow_network = st.checkbox(
            "Let phones and other devices on my home network open Weather Lab", value=s.allow_network,
            help="Opens the app to other devices on your Wi-Fi or network. Restart Weather Lab after changing this.")
        if allow_network:
            st.caption("Other devices must sign in with a password. Set one below.")
            st.caption(f"After restarting Weather Lab, open http://{network.lan_address()}:{network.app_port()} "
                       "on a phone or computer on the same network. If Windows asks about the firewall, allow "
                       "Private networks.")
            ts_address = _tailscale_address()
            if ts_address:
                st.caption(f"Away from home: on your phone, with Tailscale signed in to the same account, open "
                           f"http://{ts_address}:{network.app_port()}.")
            else:
                st.caption("Away from home: install Tailscale on this PC and on your phone, then sign in to the same "
                           "account. This address appears here once Tailscale is running.")
            _password_section()

    if st.button("Save"):
        ip = ip.strip()
        if ip and not valid_ip(ip):
            st.error("That isn't a valid IP address.")
            return
        if cwop_on and not cwop_call.strip():
            st.error("Enter a CWOP callsign to turn CWOP on.")
            return
        if wu_on and not wu_id.strip():
            st.error("Enter your Weather Underground station ID to turn uploads on.")
            return
        if wu_on and not (wu_key.strip() or (wu_key_saved and not remove_wu_key)):
            st.error("Enter your Weather Underground station key to turn uploads on.")
            return
        if pws_on and not (pws_id.strip() and (pws_key.strip() or (pws_key_saved and not remove_pws_key))):
            st.error("Enter your PWSweather station ID and key to turn uploads on.")
            return
        if wc_on and not (wc_id.strip() and (wc_key.strip() or (wc_key_saved and not remove_wc_key))):
            st.error("Enter your Weathercloud device ID and key to turn uploads on.")
            return
        try:
            if remove_key:
                secrets.set_key("airnow", "")
            elif airnow_key.strip():
                secrets.set_key("airnow", airnow_key.strip())
            if remove_wu_key:
                secrets.set_key(wunderground.KEY_NAME, "")
            elif wu_key.strip():
                secrets.set_key(wunderground.KEY_NAME, wu_key.strip())
            if remove_pws_key:
                secrets.set_key(pwsweather.KEY_NAME, "")
            elif pws_key.strip():
                secrets.set_key(pwsweather.KEY_NAME, pws_key.strip())
            if remove_wc_key:
                secrets.set_key(weathercloud.KEY_NAME, "")
            elif wc_key.strip():
                secrets.set_key(weathercloud.KEY_NAME, wc_key.strip())
        except Exception as exc:
            st.error(f"Couldn't save the keys: {exc}")
            return
        save_settings(replace(s, station_ip=ip, latitude=lat, longitude=lon, elevation_m=elev,
                               timezone=tz, nws_contact=contact.strip(),
                               lightning_value_is_km=km, cwop_enabled=cwop_on,
                               cwop_callsign=cwop_call.strip().upper(), wu_enabled=wu_on,
                               wu_station_id=wu_id.strip(), pws_enabled=pws_on,
                               pws_station_id=pws_id.strip(), weathercloud_enabled=wc_on,
                               weathercloud_id=wc_id.strip(), allow_network=allow_network))
        st.success(f"Saved to {settings_path()}")


def _notifications_section(s: Settings) -> None:
    """Sensor warnings and the morning summary, plus a button to check that Windows notifications show."""
    st.markdown("**Notifications**")
    sensors_on = st.checkbox("Warn about low sensor batteries and weak signal", value=s.sensor_alerts, key="notify_sensors")
    digest_on = st.checkbox("Send a short summary each morning about yesterday", value=s.digest_enabled, key="notify_digest")
    hour = int(st.number_input("Morning summary time (hour, 0 to 23)", min_value=0, max_value=23,
                               value=int(s.digest_hour), step=1, key="notify_hour"))
    offline_on = st.checkbox("Warn when the station stops sending readings", value=s.offline_alerts, key="notify_offline")
    frost_on = st.checkbox("Warn about freezing nights in the forecast", value=s.frost_alerts, key="notify_frost")
    metric = units.is_metric(s.units)
    frost_shown = float(st.number_input(
        f"Freeze warning when the forecast low is at or below ({'°C' if metric else '°F'})",
        min_value=round(units.convert("tempf", 20.0, metric), 1), max_value=round(units.convert("tempf", 45.0, metric), 1),
        value=round(units.convert("tempf", float(s.frost_threshold_f), metric), 1), step=1.0,
        key=f"notify_frost_{'c' if metric else 'f'}"))
    frost_f = round(units.to_us("tempf", frost_shown, metric), 1)
    if (sensors_on, digest_on, hour, offline_on, frost_on, frost_f) != (
            s.sensor_alerts, s.digest_enabled, s.digest_hour, s.offline_alerts, s.frost_alerts,
            round(s.frost_threshold_f, 1)):
        save_settings(replace(s, sensor_alerts=sensors_on, digest_enabled=digest_on, digest_hour=hour,
                              offline_alerts=offline_on, frost_alerts=frost_on, frost_threshold_f=frost_f))
    if st.button("Send a test notification"):
        if alert_rules.notify("Weather Lab", "This is a test notification from Weather Lab."):
            st.success("Sent. If nothing appears, check that Windows notifications are on for this app.")
        else:
            st.warning("Couldn't show a Windows notification here. Alerts are still listed in the app.")


def _quiet_section(s: Settings) -> None:
    """Quiet hours, the stuck-sensor check and the lightning notice."""
    st.markdown("**Quiet hours and more checks**")
    quiet_on = st.checkbox("Quiet hours: hold back non-urgent notifications", value=s.quiet_enabled, key="quiet_on",
                           help="Sensor warnings, stuck-sensor warnings and the morning summary wait until quiet hours end. "
                                "Station offline, freeze and lightning notices still sound.")
    start = int(st.number_input("Quiet from (hour, 0 to 23)", min_value=0, max_value=23, value=int(s.quiet_start),
                                step=1, key="quiet_start"))
    end = int(st.number_input("Quiet until (hour, 0 to 23)", min_value=0, max_value=23, value=int(s.quiet_end),
                              step=1, key="quiet_end"))
    stuck_on = st.checkbox("Warn when outdoor temperature or humidity stops changing", value=s.stuck_alerts, key="stuck_on")
    light_on = st.checkbox("Notify me when lightning is close", value=s.lightning_alerts, key="light_on")
    miles = float(st.number_input("Lightning notice within (miles)", min_value=1.0, max_value=25.0,
                                  value=float(s.lightning_alert_miles), step=1.0, key="light_miles"))
    if (quiet_on, start, end, stuck_on, light_on, miles) != (
            s.quiet_enabled, s.quiet_start, s.quiet_end, s.stuck_alerts, s.lightning_alerts, s.lightning_alert_miles):
        save_settings(replace(s, quiet_enabled=quiet_on, quiet_start=start, quiet_end=end, stuck_alerts=stuck_on,
                              lightning_alerts=light_on, lightning_alert_miles=miles))


def _alert_extras_section(s: Settings) -> None:
    """UV, air quality and fire danger notices, rain start and stop, and the optional version check address."""
    st.markdown("**More notices**")
    uv_on = st.checkbox("UV index notice", value=s.uv_alerts, key="ex_uv")
    uv_level = float(st.number_input("UV level for the notice", min_value=1.0, max_value=15.0,
                                     value=float(s.uv_alert_level), step=1.0, key="ex_uv_level"))
    aqi_on = st.checkbox("Air quality notice", value=s.aqi_alerts, key="ex_aqi",
                         help="Uses the AirNow key saved on the Setup page.")
    aqi_level = float(st.number_input("Air quality notice at AQI", min_value=50.0, max_value=500.0,
                                      value=float(s.aqi_alert_level), step=1.0, key="ex_aqi_level"))
    fire_on = st.checkbox("Fire danger notice", value=s.fire_alerts, key="ex_fire")
    fire_level = float(st.number_input("Fire danger notice at fire weather index", min_value=5.0, max_value=60.0,
                                       value=float(s.fire_alert_fwi), step=1.0, key="ex_fire_level"))
    rain_on = st.checkbox("Rain started and stopped notices", value=s.rain_notices, key="ex_rain")
    current = (uv_on, uv_level, aqi_on, aqi_level, fire_on, fire_level, rain_on)
    saved = (s.uv_alerts, s.uv_alert_level, s.aqi_alerts, s.aqi_alert_level, s.fire_alerts, s.fire_alert_fwi,
             s.rain_notices)
    if current != saved:
        save_settings(replace(s, uv_alerts=uv_on, uv_alert_level=uv_level, aqi_alerts=aqi_on, aqi_alert_level=aqi_level,
                              fire_alerts=fire_on, fire_alert_fwi=fire_level, rain_notices=rain_on))


def _comfort_tiles(data: dict) -> list[str]:
    """Heat index, wind chill and humidex, shown only when they apply."""
    metric = units.is_metric(load_settings().units)
    t, rh, wind, dew = data.get("tempf"), data.get("humidity"), data.get("windspeedmph"), data.get("dewpointf")
    tiles = []
    if t is not None and rh is not None and t >= 80:
        tiles.append(_tile("Heat index", units.format_value("heat_index", comfort.heat_index_f(t, rh), metric, 0), "feels hotter than air"))
    if t is not None and wind is not None and t <= 50 and wind > 3:
        tiles.append(_tile("Wind chill", units.format_value("tempf", comfort.wind_chill_f(t, wind), metric, 0), "feels colder than air"))
    if t is not None and dew is not None:
        tiles.append(_tile("Humidex", f"{comfort.humidex_c(t, dew):.0f}°C", "humid-heat index"))
    return tiles


def _now_sky(s: Settings, data: dict) -> tuple[str, bool]:
    """The NWS wording for the current hour (empty if unavailable) and whether it is night."""
    short = ""
    if s.latitude is not None and s.longitude is not None:
        try:
            pts = _points(s.latitude, s.longitude, s.nws_contact)
            if pts.get("forecastHourly"):
                hours = _hourly(pts["forecastHourly"], s.nws_contact)
                if hours:
                    short = hours[0]["short"]
        except nws.NwsError:
            short = ""
    solar = data.get("solarradiation")
    hour = datetime.now(_tz(s)).hour
    night = solar < 5 if solar is not None else (hour < 6 or hour >= 19)
    return short, night


def _now_tile(short: str, night: bool) -> str:
    icon = wx_icons.forecast_icon(short, night, 64)
    return (f'<div class="wl-tile"><div style="display:flex;align-items:center;gap:12px">{icon}'
            f'<div style="min-width:0"><div class="wl-label">Right now</div>'
            f'<div class="wl-value" style="font-size:18px">{html.escape(short)}</div></div></div></div>')


@st.cache_data(ttl=600, show_spinner=False)
def _live_alerts(lat: float, lon: float, contact: str) -> list[dict]:
    """Active NWS warnings. A failure is remembered for 10 minutes, so an offline network can't slow Live down."""
    try:
        return nws.alerts(lat, lon, contact)
    except nws.NwsError:
        return []


def _warnings(s: Settings) -> None:
    """Recent rule alerts and active NWS warnings, shown at the top of Live."""
    now = time.time()
    for ts, text in [(t, m) for t, m in start_poller().status.recent_alerts if now - t < 6 * 3600][:3]:
        st.warning(f"{_clock(ts)}  {text}")
    if s.latitude is None or s.longitude is None:
        return
    active = _live_alerts(s.latitude, s.longitude, s.nws_contact)
    if active:
        st.markdown('<div class="wl-status">Active warnings</div>', unsafe_allow_html=True)
        st.markdown("".join(_alert_box(a) for a in active[:3]), unsafe_allow_html=True)
        if len(active) > 3:
            st.caption(f"{len(active) - 3} more on the Forecast page.")


def _naive(dt, tz):
    """A timezone-aware time as a naive local time (None stays None)."""
    return dt.astimezone(tz).replace(tzinfo=None) if dt is not None else None


def _span(delta) -> str:
    minutes = max(0, int(delta.total_seconds() // 60))
    h, m = divmod(minutes, 60)
    return f"{h} h {m} min" if h else f"{m} min"


def _uv_word(uv: float) -> str:
    return "low" if uv < 3 else "moderate" if uv < 6 else "high" if uv < 8 else "very high" if uv < 11 else "extreme"


def _press_word(now_value, old_value) -> str:
    if now_value is None or old_value is None:
        return ""
    ch = now_value - old_value
    return ("rising fast" if ch > 0.06 else "rising" if ch > 0.02 else
            "falling fast" if ch < -0.06 else "falling" if ch < -0.02 else "steady")


def _hero(s: Settings, row: tuple, short: str, night: bool, alerts: list[dict]) -> None:
    """The 'right now' panel: sky, temperature, alert, today's range, the last-hour trend and the main readings."""
    ts, data = row
    temp = data.get("tempf")
    if temp is None:
        return
    db = storage.connect()
    tz = _tz(s)
    metric = units.is_metric(s.units)
    wall = time.time()
    now_dt = datetime.now(tz)
    rise, sset = (None, None)
    if s.latitude is not None and s.longitude is not None:
        rise, sset = astro.sun_times(s.latitude, s.longitude, now_dt.date())
    now_n, rise_n, set_n = now_dt.replace(tzinfo=None), _naive(rise, tz), _naive(sset, tz)
    strike = storage.latest_strike(db)
    storm = strike is not None and wall - strike[0] < 1800
    raining = (data.get("rainratein") or 0) > 0
    cloudy = "cloud" in short.lower() or "overcast" in short.lower()
    kind = hero.sky_phase(hero.pick_kind(night, storm, raining, cloudy), now_n, rise_n, set_n)

    alert, tone = "", "warn"
    if alerts:
        top = alerts[0]  # nws.alerts puts the most severe first
        until = top["expires"][:16].replace("T", " ") if top["expires"] else ""
        alert = f"{top['event']} until {until}" if until else top["event"]
        if len(alerts) > 1:
            alert = f"{len(alerts)} alerts · {top['severity']} · {alert}"
        tone = "bad" if top["severity"] in ("Extreme", "Severe") else "warn"

    state, age_text = health.age_status(ts, wall)
    live_text = {"ok": f"Live · updated {age_text}", "slow": f"Late · last reading {age_text}",
                 "silent": f"No data for {age_text} · check the station",
                 "none": "Waiting for first reading"}[state]

    today = storage.readings_between(db, _start_of_today(s), wall + 1)
    today_temps = [r["tempf"] for _, r in today if r.get("tempf") is not None]
    gusts = [r["windgustmph"] for _, r in today if r.get("windgustmph") is not None]
    lo, hi = (min(today_temps), max(today_temps)) if today_temps else (None, None)

    prior = [r["tempf"] for _, r in storage.readings_between(db, wall - 3900, wall - 3300)
             if r.get("tempf") is not None]
    trend, trend_col = "", "#c3cbd8"
    if prior:
        delta = units.convert("tempf", temp, metric) - units.convert("tempf", prior[-1], metric)
        if abs(delta) >= 0.5:
            trend = f"{'▲' if delta > 0 else '▼'} {abs(delta):.0f}° in the last hour"
            trend_col = "#fdba74" if delta > 0 else "#93c5fd"
        else:
            trend = "– steady over the last hour"

    press = data.get("baromrelin")
    old_press = [r["baromrelin"] for _, r in storage.readings_between(db, wall - 3 * 3600 - 300, wall - 3 * 3600 + 300)
                 if r.get("baromrelin") is not None]
    press_word = _press_word(press, old_press[-1] if old_press else None)

    sun = ""
    if rise_n and now_n < rise_n:
        sun = f"Sunrise in {_span(rise_n - now_n)}"
    elif set_n and now_n < set_n:
        sun = f"Sunset in {_span(set_n - now_n)}"

    tiles = []
    ws, wd = data.get("windspeedmph"), data.get("winddir")
    if ws is not None:
        prefix = wind_rose.NAMES[round(wd / 22.5) % 16] + " " if wd is not None and ws >= 1 else ""
        gust_note = f"gusts {units.format_value('windgustmph', max(gusts), metric, 0)} today" if gusts else ""
        tiles.append(("Wind", prefix + units.format_value("windspeedmph", ws, metric, 0), gust_note))
    hum, dew = data.get("humidity"), data.get("dewpointf")
    if hum is not None:
        dew_note = f"dew point {units.format_value('dewpointf', dew, metric, 0)}" if dew is not None else ""
        tiles.append(("Humidity", f"{hum:.0f}%", dew_note))
    if press is not None:
        tiles.append(("Pressure", units.format_value("baromrelin", press, metric, 2), press_word))
    uv = data.get("uv")
    if uv is not None:
        tiles.append(("UV index", f"{uv:.0f}", _uv_word(uv)))
    rain = data.get("dailyrainin")
    if rain is not None:
        tiles.append(("Rain today", units.format_value("dailyrainin", rain, metric, 2), ""))

    parts = []
    if hi is not None:
        parts.append(f"high {units.convert('tempf', hi, metric):.0f}° · low {units.convert('tempf', lo, metric):.0f}°")
    if rain is not None:
        parts.append(f"rain {units.format_value('dailyrainin', rain, metric, 2)}")
    if gusts:
        parts.append(f"peak gust {units.format_value('windgustmph', max(gusts), metric, 0)}")

    feels = data.get("feelslikef")
    html_out, height = hero.hero_html({
        "temp_text": f"{units.convert('tempf', temp, metric):.0f}°",
        "kind": kind, "icon": wx_icons.now_icon(kind, 84),
        "feels": units.format_value("feelslikef", feels, metric, 0) if feels is not None else "",
        "label": short, "place": "",
        "live_state": state, "live_text": live_text,
        "alert": alert, "alert_tone": tone,
        "lo": units.convert("tempf", lo, metric) if lo is not None else None,
        "hi": units.convert("tempf", hi, metric) if hi is not None else None,
        "now": units.convert("tempf", temp, metric),
        "lo_text": units.format_value("tempf", lo, metric, 0) if lo is not None else "",
        "hi_text": units.format_value("tempf", hi, metric, 0) if hi is not None else "",
        "tiles": tiles, "trend": trend, "trend_col": trend_col, "sun_note": sun,
        "today_line": " · ".join(parts),
    })
    components.html(motion.add(html_out, s.animate), height=height)


def _temp_ring(s: Settings, data: dict) -> None:
    """The temperature ring with today's high and low, feels like, dew point and humidity."""
    temp = data.get("tempf")
    if temp is None:
        return
    today = storage.readings_between(storage.connect(), _start_of_today(s), time.time() + 1)
    temps = [r["tempf"] for _, r in today if r.get("tempf") is not None]
    html_out, height = gauges.temp_ring_html(
        temp, high=max(temps) if temps else None, low=min(temps) if temps else None,
        feels=data.get("feelslikef"), dew=data.get("dewpointf"), hum=data.get("humidity"),
        dark=theme.is_dark(), metric=units.is_metric(s.units))
    components.html(motion.add(html_out, s.animate), height=height)


SPARK_KEYS = ("tempf", "humidity", "windspeedmph", "baromrelin")
ALERT_ZONE_LIMIT = 25  # zones outlined at most, so a statewide warning can't stall the page


@st.cache_data(ttl=3600, show_spinner=False)
def _zone_rings(zone: str, contact: str) -> list:
    """Outline of one NWS warning zone, remembered for an hour. Failures are not remembered."""
    return nws.zone_rings(zone, contact)


def _alert_map(s: Settings, alerts: list[dict]) -> None:
    """Warnings drawn on their zones around the station, using NWS zone outlines fetched at run time."""
    zoned, budget = [], ALERT_ZONE_LIMIT
    for a in alerts:
        zones = []
        for zone in a.get("ugc", []):
            if budget <= 0:
                break
            budget -= 1
            try:
                zones.append((zone, _zone_rings(zone, s.nws_contact)))
            except nws.NwsError:
                continue
        zoned.append(dict(a, zones=zones))
    names = [f"{a['event']} ({a['severity']})" for a in zoned]
    choice = st.selectbox("Highlight an alert", names, index=None, placeholder="All alerts", key="alert_highlight")
    highlight = names.index(choice) if choice in names else None
    dark = theme.is_dark()
    fig = charts.figure(dark, height=360)
    for t in alert_map.traces(zoned, highlight):
        fig.add_trace(go.Scatter(x=t["xs"], y=t["ys"], mode="lines", fill="toself", fillcolor=t["color"],
                                 line=dict(color=t["color"], width=1.5), opacity=t["opacity"],
                                 name=t["name"], hoverinfo="name", showlegend=False))
    fig.add_trace(go.Scatter(x=[s.longitude], y=[s.latitude], mode="markers", name="Your location",
                             marker=dict(size=12, symbol="star", color=theme.palette(dark)["text"]),
                             hoverinfo="name", showlegend=False))
    x0, x1, y0, y1 = alert_map.view_box(s.latitude, s.longitude, span=1.0)
    fig.update_xaxes(range=[x0, x1], visible=False)
    fig.update_yaxes(range=[y0, y1], visible=False)
    fig.update_layout(margin=dict(l=0, r=0, t=8, b=0), hovermode="closest")
    charts.show(fig)
    if sum(len(a.get("ugc", [])) for a in alerts) > ALERT_ZONE_LIMIT:
        st.caption(f"Only the first {ALERT_ZONE_LIMIT} zones are outlined.")


def _pressure_change(now_inhg: float) -> float | None:
    """Pressure change over the last three hours, in inHg. None until there is a reading from about then."""
    now = time.time()
    old = [r["baromrelin"] for _, r in storage.readings_between(storage.connect(), now - 3 * 3600 - 300,
                                                               now - 3 * 3600 + 300)
           if r.get("baromrelin") is not None]
    return now_inhg - sum(old) / len(old) if old else None


def _feels_dial(s: Settings, data: dict) -> None:
    feels = data.get("feelslikef")
    if feels is None:
        return
    html_out, height = dials.feels_dial_html(feels, actual_f=data.get("tempf"), humidity=data.get("humidity"),
                                             dark=theme.is_dark(), metric=units.is_metric(s.units))
    components.html(motion.add(html_out, s.animate), height=height)


def _pressure_dial(s: Settings, data: dict) -> None:
    now_inhg = data.get("baromrelin")
    if now_inhg is None:
        return
    change = _pressure_change(now_inhg)
    if change is None:
        st.caption("The pressure trend appears after three hours of readings.")
        return
    html_out, height = dials.pressure_dial_html(now_inhg, change, dark=theme.is_dark(),
                                                metric=units.is_metric(s.units))
    components.html(motion.add(html_out, s.animate), height=height)


@st.cache_data(ttl=600, show_spinner=False)
def _recent_thinned(stamp: int, station: str) -> list:
    """One reading per ten minutes for the last 31 days, with only the measures the Live cards use. The stamp
    changes every ten minutes, which is what refreshes this cache."""
    now = time.time()
    out, last = [], None
    for ts, r in storage.readings_between(storage.connect(), now - 31 * 86400, now + 1):
        bucket = int(ts // 600)
        kept = (ts, {k: r.get(k) for k in SPARK_KEYS})
        if bucket == last:
            out[-1] = kept  # the latest reading in each ten-minute slot wins
        else:
            out.append(kept)
            last = bucket
    return out


def _glance(s: Settings, data: dict, updated: float) -> None:
    """Temperature, humidity and wind over the last 24 hours, each compared with usual for this hour."""
    metric = units.is_metric(s.units)
    now = time.time()
    rows = _recent_thinned(int(now // 600), stations.current())
    day = [(ts, r) for ts, r in rows if ts >= now - 86400]
    specs = [("tempf", "Temperature", units.unit("tempf", metric), 1.5 if metric else 3.0, charts.CHART_COLORS[3]),
             ("humidity", "Humidity", "%", 5.0, charts.CHART_COLORS[0]),
             ("windspeedmph", "Wind", units.speed_unit(metric), 5.0 if metric else 3.0, charts.CHART_COLORS[1])]
    tiles = []
    for key, label, unit_text, neutral, color in specs:
        if data.get(key) is None:
            continue
        cur = units.convert(key, data[key], metric)
        series = [units.convert(key, r[key], metric) for _, r in day if r.get(key) is not None]
        found = sparks.hourly_usual(rows + [(now, data)], key, _tz(s), now)
        if found:
            note, direction = sparks.compare_text(cur, units.convert(key, found[1], metric), unit_text, neutral)
        else:
            note, direction = "Usual for this hour builds up after five days.", None
        tiles.append(sparks.tile_html({"label": label, "value": f"{cur:.0f}", "unit": unit_text, "series": series,
                                       "color": color, "compare": note, "direction": direction}))
    if tiles:
        st.markdown(theme.section_html("Last 24 hours", updated=updated), unsafe_allow_html=True)
        st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)


@st.fragment(run_every=REFRESH_SECONDS)
def live_readings() -> None:
    """Cards and status line. Streamlit re-runs just this part every REFRESH_SECONDS."""
    s = load_settings()
    poller = start_poller()
    status = poller.status

    if not poller.is_alive():
        st.error("The background reader has stopped. Restart the app.")
    elif status.last_error:
        st.warning(status.last_error)
    _warnings(s)

    row = storage.latest(storage.connect())
    if row is None:
        st.info("Waiting for the first reading from the station. If this doesn't change within a minute, check the station IP on Setup and that the station is on the same network.")
    else:
        _, data = row
        dark = theme.is_dark()
        short, night = _now_sky(s, data)
        alerts = _live_alerts(s.latitude, s.longitude, s.nws_contact) if s.latitude is not None and s.longitude is not None else []
        _hero(s, row, short, night, alerts)
        if alerts and s.latitude is not None and s.longitude is not None:
            with st.expander("Alert map", expanded=True):
                _alert_map(s, alerts)
        _glance(s, data, row[0])
        tiles = []
        metric = units.is_metric(s.units)
        for key, lo, hi, label, fmt in [("humidity", 0, 100, "Humidity %", "{:.0f}"),
                                        ("windspeedmph", 0, 40, f"Wind {units.speed_unit(metric)}", "{:.0f}"),
                                        ("uv", 0, 11, "UV index", "{:.0f}")]:
            if data.get(key) is not None:
                tiles.append(theme.gauge_html(units.convert(key, data[key], metric),
                                              units.convert(key, lo, metric), units.convert(key, hi, metric),
                                              label, fmt, dark, animate=s.animate))
        for key in s.live_cards:
            if key in data:
                label, unit = CARD_LABELS[key]
                text = units.format_value(key, data[key], metric) if units.converts(key) else f"{data[key]:g} {unit}".strip()
                tiles.append(_tile(label, text))
        tiles.extend(_comfort_tiles(data))
        compact = st.toggle("Compact sections", key="live_compact", value=False)
        with st.expander("Details", expanded=not compact):
            _temp_ring(s, data)
            left, right = st.columns(2)
            with left:
                _feels_dial(s, data)
            with right:
                _pressure_dial(s, data)
            st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)

    dot = _status_dot(row[0]) if row else ""
    parts = []
    if status.last_ok:
        parts.append(f"Last reading {_clock(status.last_ok)}")
    if status.last_attempt:
        parts.append(f"last attempt {_clock(status.last_attempt)}")
    if status.started:
        parts.append(f"reader started {_clock(status.started)}")
    if parts:
        st.markdown(f'<div class="wl-status">{dot}{" · ".join(parts)}</div>', unsafe_allow_html=True)


def access_gate() -> bool:
    """True when the page may be shown. Once network access is on, other devices need the password."""
    if not load_settings().allow_network:
        return True
    if st.session_state.get("signed_in"):
        return True
    token = os.environ.get("WEATHERLAB_WINDOW_TOKEN", "")
    if token and st.query_params.get("wl_token") == token:
        st.session_state["signed_in"] = True
        return True
    if not auth.password_set():
        st.error("Other devices can't open Weather Lab until a password is set. Set one on the Setup page on this PC.")
        return False
    st.markdown(theme.title_html("Sign in"), unsafe_allow_html=True)
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        wait = auth.locked_for()
        if wait:
            st.error(f"Too many attempts. Try again in {wait} seconds.")
        elif auth.sign_in(password):
            auth.reset_failures()
            st.session_state["signed_in"] = True
            st.rerun()
        else:
            auth.record_failure()
            st.error("That password isn't right.")
    return False


def _status_dot(ts: float) -> str:
    state, _ = health.age_status(ts, time.time())
    return theme.status_dot(state)


def _today_vs_yesterday(s: Settings) -> None:
    """Today so far against yesterday over the same hours."""
    tz, metric = _tz(s), units.is_metric(s.units)
    db = storage.connect()
    now = datetime.now(tz)
    start = datetime.combine(now.date(), datetime.min.time(), tzinfo=tz)
    today = storage.readings_between(db, start.timestamp(), now.timestamp() + 1)
    earlier = storage.readings_between(db, (start - timedelta(days=1)).timestamp(),
                                       (now - timedelta(days=1)).timestamp() + 1)
    if not today or not earlier:
        return
    compared = history_compare.by_this_time([r for _, r in today], [r for _, r in earlier])

    def pair(key: str, label: str, decimals: int):
        t, y = compared[key]
        if t is None:
            return None
        text = f"{label} {units.format_value(key, t, metric, decimals)}"
        if y is not None:
            text += f" (yesterday by this time: {units.format_value(key, y, metric, decimals)})"
        return text

    parts = [p for p in (pair("tempf", "High so far", 0), pair("dailyrainin", "Rain today", 2),
                         pair("windgustmph", "Gust so far", 0)) if p]
    if parts:
        st.caption(" · ".join(parts))


def _dew_line(s: Settings) -> None:
    """Dew point in plain words: how muggy it feels right now."""
    latest = storage.latest(storage.connect())
    if not latest or latest[1].get("dewpointf") is None:
        return
    dew_point = latest[1]["dewpointf"]
    shown = units.format_value("dewpointf", dew_point, units.is_metric(s.units), 0)
    st.caption(f"Dew point {shown}: {dew.text(dew_point)}.")


def live_page() -> None:
    s = load_settings()
    st.markdown(theme.title_html("Live"), unsafe_allow_html=True)
    if not s.station_ip:
        st.info("Set the station IP on the Setup page.")
        return
    _today_vs_yesterday(s)
    _dew_line(s)
    live_readings()


# ---------------------------------------------------------------- Daily

def _typical_caption(db, day: date, summary: dict, metric: bool) -> None:
    """How this day compares with the same date in other years."""
    typical = history_compare.typical(history.all_daily(db), day)
    if typical["years"] < 2 or summary.get("tempf_max") is None or typical["high"] is None:
        return
    scale, unit = (5 / 9, "°C") if metric else (1, "°F")

    def word(change: float, label: str) -> str:
        amount = abs(change) * scale
        if amount < 0.5:
            return f"{label} about typical"
        return f"{label} {amount:.0f} {unit} {'above' if change > 0 else 'below'} typical"

    parts = [word(summary["tempf_max"] - typical["high"], "high")]
    if summary.get("tempf_min") is not None and typical["low"] is not None:
        parts.append(word(summary["tempf_min"] - typical["low"], "low"))
    st.caption(f"Compared with the 7 days around this date in {typical['years']} other years: " + ", ".join(parts) + ".")


def daily_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("Daily"), unsafe_allow_html=True)
    day = st.date_input("Day", value=today - timedelta(days=1), max_value=today)

    rows = daily.day_rows(db, day, tz)
    if day == today:
        summary, _ = daily.summarize_day(rows, s.latitude or 0.0, s.longitude or 0.0, s.elevation_m, tz)
        note = "Today so far"
    else:
        found = db.execute("SELECT data FROM daily WHERE date = ?", (day.isoformat(),)).fetchone()
        summary = json.loads(found[0]) if found else None
        note = ""

    if not summary:
        st.info("No summary for this day yet. A day needs at least 20 readings.")
        return

    if summary.get("estimated"):
        st.caption("This day is an estimate, built from 4-hour readings. A high or a low can fall between readings.")

    metric = units.is_metric(s.units)

    def get(key, fmt="{:g}"):
        v = summary.get(key)
        return "--" if v is None else fmt.format(v)

    def shown(key: str, summary_key: str, decimals: int) -> str:
        return units.format_value(key, summary.get(summary_key), metric, decimals)

    tiles = [
        _tile("High", shown("tempf", "tempf_max", 0), note),
        _tile("Low", shown("tempf", "tempf_min", 0)),
        _tile("Average", shown("tempf", "tempf_avg", 0)),
        _tile("Rain", shown("dailyrainin", "rain_in", 2)),
        _tile("Wind run", shown("miles", "wind_run_mi", 1)),
        _tile("Gust max", shown("windgustmph", "gust_max", 0)),
        _tile("Sun hours", f"{get('sun_hours', '{:.1f}')} h"),
        _tile("Humidity", f"{get('humidity_min', '{:.0f}')}–{get('humidity_max', '{:.0f}')}%"),
    ]
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)

    _typical_caption(db, day, summary, units.is_metric(s.units))

    latest = storage.latest(db) if day == today else None
    st.download_button("Download PDF report", data=report.daily_pdf(day.isoformat(), summary, latest[1] if latest else None, units.is_metric(s.units)),
                       file_name=f"weather_report_{day.isoformat()}.pdf", mime="application/pdf")

    dark = theme.is_dark()
    times = [datetime.fromtimestamp(ts, tz) for ts, _ in rows]
    temp = charts.figure(dark)
    temp.add_trace(go.Scatter(x=times, y=_conv("tempf", [r.get("tempf") for _, r in rows], metric),
                              name=f"Temperature ({units.unit('tempf', metric)})",
                              line=dict(color=charts.CHART_COLORS[0])))
    temp.add_trace(go.Scatter(x=times, y=_conv("tempf", [r.get("feelslikef") for _, r in rows], metric),
                              name=f"Feels like ({units.unit('tempf', metric)})",
                              line=dict(color=charts.CHART_COLORS[3], dash="dot")))
    charts.show(temp)

    wind = charts.figure(dark)
    wind.add_trace(go.Scatter(x=times, y=_conv("windspeedmph", [r.get("windspeedmph") for _, r in rows], metric),
                              name=f"Wind ({units.speed_unit(metric)})",
                              line=dict(color=charts.CHART_COLORS[1])))
    wind.add_trace(go.Scatter(x=times, y=_conv("windgustmph", [r.get("windgustmph") for _, r in rows], metric),
                              name=f"Gust ({units.speed_unit(metric)})",
                              line=dict(color=charts.CHART_COLORS[4], dash="dot")))
    charts.show(wind)


# ---------------------------------------------------------------- History

def history_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("History"), unsafe_allow_html=True)

    latest = storage.latest(db)
    live_rain = latest[1].get("dailyrainin") if latest else None
    totals = history.rain_totals(db, today, live_rain)
    st.markdown(theme.grid_html([
        _tile("Rain today", f"{totals['today']:.2f} in"),
        _tile("Last 7 days", f"{totals['last_7_days']:.2f} in"),
        _tile("This month", f"{totals['this_month']:.2f} in"),
        _tile("This year", f"{totals['this_year']:.2f} in"),
    ]), unsafe_allow_html=True)

    options = {"7 days": 7, "30 days": 30, "90 days": 90, "1 year": 365}
    choice = st.radio("Range", list(options), index=1, horizontal=True)
    n = options[choice]
    rows = history.daily_between(db, today - timedelta(days=n), today - timedelta(days=1))
    if not rows:
        st.info("No daily summaries yet. Each day's summary is written once that day's readings are in, so the first ones appear after Weather Lab has run for a day.")
    else:
        _history_charts(rows, theme.is_dark())
    _compare_periods(db, today)


def _history_charts(rows: list, dark: bool) -> None:
    metric = units.is_metric(load_settings().units)
    tu, ru = units.unit("tempf", metric), units.unit("dailyrainin", metric)
    days = [d for d, _ in rows]
    temps = charts.figure(dark)
    temps.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("tempf_max") for _, r in rows], metric),
                               name=f"High ({tu})", line=dict(color=charts.CHART_COLORS[4])))
    temps.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("tempf_min") for _, r in rows], metric),
                               name=f"Low ({tu})", line=dict(color=charts.CHART_COLORS[0])))
    charts.show(temps)

    rain = charts.figure(dark)
    rain.add_trace(go.Bar(x=days, y=_conv("dailyrainin", [r.get("rain_in", 0.0) for _, r in rows], metric),
                          name=f"Rain ({ru})", marker_color=charts.CHART_COLORS[0]))
    charts.show(rain)
    if any(r.get("indoor_tempf_avg") is not None for _, r in rows):
        indoor = charts.figure(dark)
        indoor.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("indoor_tempf_max") for _, r in rows], metric),
                                    name=f"Indoor high ({tu})", line=dict(color=charts.CHART_COLORS[4])))
        indoor.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("indoor_tempf_avg") for _, r in rows], metric),
                                    name=f"Indoor average ({tu})", line=dict(color=charts.CHART_COLORS[2])))
        indoor.add_trace(go.Scatter(x=days, y=_conv("tempf", [r.get("indoor_tempf_min") for _, r in rows], metric),
                                    name=f"Indoor low ({tu})", line=dict(color=charts.CHART_COLORS[0])))
        charts.show(indoor)
    if any(r.get("indoor_humidity_max") is not None for _, r in rows):
        damp = charts.figure(dark)
        damp.add_trace(go.Scatter(x=days, y=[r.get("indoor_humidity_max") for _, r in rows], name="Indoor humidity high (%)",
                                  line=dict(color=charts.CHART_COLORS[1])))
        damp.add_trace(go.Scatter(x=days, y=[r.get("indoor_humidity_min") for _, r in rows], name="Indoor humidity low (%)",
                                  line=dict(color=charts.CHART_COLORS[3], dash="dot")))
        charts.show(damp)


def _compare_periods(db, today: date) -> None:
    """Two date ranges side by side: totals and averages for each, and the change between them."""
    st.markdown("**Compare two periods**")
    yesterday = today - timedelta(days=1)
    c1, c2 = st.columns(2)
    with c1:
        a_start = st.date_input("First period from", value=yesterday - timedelta(days=29), max_value=yesterday, key="cmp_a_start")
        a_end = st.date_input("First period to", value=yesterday, max_value=yesterday, key="cmp_a_end")
    with c2:
        b_start = st.date_input("Second period from", value=yesterday - timedelta(days=59), max_value=yesterday, key="cmp_b_start")
        b_end = st.date_input("Second period to", value=yesterday - timedelta(days=30), max_value=yesterday, key="cmp_b_end")
    if a_end < a_start or b_end < b_start:
        st.error("An end date is before its start date.")
        return
    a = history_compare.period_stats(history.daily_between(db, a_start, a_end))
    b = history_compare.period_stats(history.daily_between(db, b_start, b_end))
    if not a["days"] and not b["days"]:
        st.info("Neither period has daily summaries yet.")
        return
    metric = units.is_metric(load_settings().units)
    # (label, key, format, reading key used for units or None, unit text when there is none)
    metrics = [("Days with data", "days", "{:.0f}", None, ""), ("Average high", "avg_high", "{:.1f}", "tempf", ""),
               ("Average low", "avg_low", "{:.1f}", "tempf", ""), ("Highest high", "max_high", "{:.0f}", "tempf", ""),
               ("Lowest low", "min_low", "{:.0f}", "tempf", ""), ("Rain total", "rain_total", "{:.2f}", "dailyrainin", ""),
               ("Rainy days", "rain_days", "{:.0f}", None, ""), ("Sun hours", "sun_hours", "{:.1f}", None, " h")]

    def shown(value, fmt, conv, unit):
        if value is None:
            return "-"
        if conv is None:
            return fmt.format(value) + unit
        return fmt.format(units.convert(conv, value, metric)) + units.suffix(conv, metric)

    body = []
    for label, key, fmt, conv, unit in metrics:
        delta = history_compare.change(a[key], b[key])
        if delta is None:
            delta_text = "-"
        else:
            change = units.convert_change(conv, delta, metric) if conv else delta
            delta_text = ("+" if delta > 0 else "") + fmt.format(change) + (units.suffix(conv, metric) if conv else unit)
        body.append([html.escape(label), html.escape(shown(a[key], fmt, conv, unit)),
                     html.escape(shown(b[key], fmt, conv, unit)), html.escape(delta_text)])
    st.markdown(_table(["", "First period", "Second period", "Change"], body, theme.is_dark()), unsafe_allow_html=True)
    st.caption("Change is the first period minus the second.")


def coverage_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    yesterday = datetime.now(tz).date() - timedelta(days=1)
    st.markdown(theme.title_html("Coverage"), unsafe_allow_html=True)
    days = dict(history.all_daily(db))
    if not days:
        st.info("Coverage appears once Weather Lab has a finished day to record.")
        return
    options = {"30 days": 30, "90 days": 90, "1 year": 365, "All": None}
    choice = st.radio("Show", list(options), index=2, horizontal=True, key="coverage_span")
    span = options[choice]
    first = min(days)
    start = first if span is None else max(first, yesterday - timedelta(days=span - 1))
    rows = coverage.coverage(days, start, yesterday)
    counted = coverage.counts(rows)
    total = len(rows)
    st.markdown(theme.grid_html([
        _tile("Exact days", str(counted[coverage.EXACT]), f"of {total} days"),
        _tile("Estimated", str(counted[coverage.ESTIMATED]), "from 4-hour readings"),
        _tile("Missing", str(counted[coverage.MISSING]), "no summary"),
        _tile("Covered", f"{coverage.percent(counted, total):.0f}%", "exact or estimated"),
    ]), unsafe_allow_html=True)
    gaps = [(day, state) for day, state in reversed(rows) if state != coverage.EXACT]
    if not gaps:
        st.success("Every day in this range has an exact summary.")
        return
    shown_gaps = gaps[:200]
    body = [[html.escape(day.strftime("%a %b %d, %Y")), html.escape(coverage.LABELS[state])]
            for day, state in shown_gaps]
    st.markdown(_table(["Day", "Status"], body, theme.is_dark()), unsafe_allow_html=True)
    if len(gaps) > len(shown_gaps):
        st.caption(f"Showing the newest 200 of {len(gaps)} days that are not exact.")


# ---------------------------------------------------------------- Records

def _heat_days_section(db, metric: bool) -> None:
    """Days at or above 100 °F and 110 °F, by year."""
    by_year = history_compare.heat_days_by_year(history.all_daily(db))
    if not by_year:
        return
    st.markdown(theme.section_html("Hot days by year"), unsafe_allow_html=True)
    body = [[html.escape(str(year)), html.escape(str(counts[100])), html.escape(str(counts[110]))]
            for year, counts in by_year.items()]
    st.markdown(_table(["Year", f"At or above {units.format_value('tempf', 100, metric, 0)}",
                        f"At or above {units.format_value('tempf', 110, metric, 0)}"], body, theme.is_dark()),
                unsafe_allow_html=True)


def _on_this_day(db, today: date) -> None:
    """The same date in earlier years: high, low and rain."""
    metric = units.is_metric(load_settings().units)
    earlier = history.same_day_before(history.all_daily(db), today)
    if not earlier:
        return
    st.markdown(theme.section_html(f"On {today:%B} {today.day} in earlier years"), unsafe_allow_html=True)
    body = [[html.escape(str(d.year)), html.escape(units.format_value("tempf", s.get("tempf_max"), metric, 0)),
             html.escape(units.format_value("tempf", s.get("tempf_min"), metric, 0)),
             html.escape(units.format_value("dailyrainin", s.get("rain_in"), metric, 2))]
            for d, s in earlier]
    st.markdown(_table(["Year", "High", "Low", "Rain"], body, theme.is_dark()), unsafe_allow_html=True)


def _record_text(r: dict, metric: bool) -> str:
    """A record in the chosen units, such as "95°F" or "35.0°C"."""
    key = history.RECORD_UNIT.get(r["key"])
    if key is None:
        return f"{r['value']:g}{r['unit']}"
    shown = units.convert(key, r["value"], metric)
    return (f"{shown:.1f}" if metric else f"{r['value']:g}") + units.suffix(key, metric)


def records_page() -> None:
    st.markdown(theme.title_html("Records"), unsafe_allow_html=True)
    items = history.records(storage.connect())
    if not items:
        st.info("Records appear once there are a few days of summaries to compare. They fill in as Weather Lab keeps collecting.")
        return
    metric = units.is_metric(load_settings().units)
    tiles = [_tile(r["label"], _record_text(r, metric),
                   r["date"].strftime("%b %d, %Y") + (" · estimate" if r.get("estimated") else "")) for r in items]
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    st.caption("Records cover only the time since this app started collecting data. Records marked estimate come from 4-hour readings.")
    _on_this_day(storage.connect(), datetime.now(_tz(load_settings())).date())
    _heat_days_section(storage.connect(), units.is_metric(load_settings().units))


# ---------------------------------------------------------------- History: rankings, rewind, climate, my year

@st.cache_data(ttl=600, show_spinner=False)
def _all_days(station: str) -> list:
    """Every daily summary as (date, summary) pairs, remembered for ten minutes."""
    return history.all_daily(storage.connect())


def _fmt(key: str, value, metric: bool, decimals: int = 0) -> str:
    """A reading in the chosen units, or a dash when there is no value."""
    return "-" if value is None else units.format_value(key, value, metric, decimals)


def _table(headers: list, rows: list, dark: bool) -> str:
    """A plain table in the theme's colours. Cell text must already be escaped."""
    p = theme.palette(dark)
    head = "".join(f'<th style="text-align:left;padding:6px 8px;font-weight:600;color:{p["muted"]}">{h}</th>'
                   for h in headers)
    body = "".join("<tr>" + "".join(f'<td style="padding:6px 8px;border-top:1px solid {p["line"]}">{c}</td>'
                                    for c in row) + "</tr>" for row in rows)
    return (f'<table style="width:100%;border-collapse:collapse;color:{p["text"]};font-size:14px">'
            f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")


RANKINGS = {  # label: (summary key, "max" or "min", units key or None, unit text, decimals)
    "Warmest days": ("tempf_max", "max", "tempf", "", 0),
    "Coldest nights": ("tempf_min", "min", "tempf", "", 0),
    "Wettest days": ("rain_in", "max", "dailyrainin", "", 2),
    "Windiest days": ("gust_max", "max", "windgustmph", "", 0),
    "Highest UV": ("uvi", "max", None, "UV", 1),
    "Sunniest days": ("sun_hours", "max", None, "hours", 1),
}


def alerts_log_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html("Alert history"), unsafe_allow_html=True)
    rows = storage.recent_alerts(storage.connect(), limit=300)
    if not rows:
        st.info("Alerts appear here once Weather Lab sends its first notification.")
        return
    query = st.text_input("Search alerts", key="alert_search").strip().lower()
    body = [[html.escape(datetime.fromtimestamp(ts, tz).strftime("%a %b %d, %I:%M %p")), html.escape(text)]
            for ts, text in rows if not query or query in text.lower()]
    if not body:
        st.info("No alerts match that search.")
        return
    st.markdown(_table(["When", "Alert"], body, theme.is_dark()), unsafe_allow_html=True)


def ask_page() -> None:
    s = load_settings()
    metric = units.is_metric(s.units)
    today = datetime.now(_tz(s)).date()
    st.markdown(theme.title_html("Ask"), unsafe_allow_html=True)
    question = st.text_input("Ask about your history", key="ask_question",
                             placeholder="for example: wettest month, or rain in March 2026")
    if not question.strip():
        st.caption("Try: " + ask.EXAMPLES + ".")
        return
    st.write(ask.answer(question, _all_days(stations.current()), today, metric))


@st.cache_data(ttl=600, show_spinner=False)
def _unusual_days(metric: bool = False, station: str = "main") -> list:
    """Days in the last year that stand out, newest first: (date, reasons)."""
    days = _all_days(stations.current())
    cutoff = date.today() - timedelta(days=365)
    found = []
    for day, summary in days:
        if day < cutoff:
            continue
        reasons = history_compare.unusual(day, summary, days, metric=metric)
        if reasons:
            found.append((day, reasons))
    return list(reversed(found))


def unusual_page() -> None:
    st.markdown(theme.title_html("Unusual days"), unsafe_allow_html=True)
    metric = units.is_metric(load_settings().units)
    if metric:
        st.caption("A day is listed when its high or low is 5.6 °C or more from the usual value for that date, "
                   "or when it had 25 mm or more of rain. Temperature comparisons need at least two earlier years. "
                   "Temperatures are in °C.")
    else:
        st.caption("A day is listed when its high or low is 10 °F or more from the usual value for that date, "
                   "or when it had 1 inch or more of rain. Temperature comparisons need at least two earlier years. "
                   "Temperatures are in °F.")
    found = _unusual_days(metric, stations.current())
    if not found:
        st.info("Nothing stands out in the last year.")
        return
    body = [[html.escape(day.strftime("%a %b %d, %Y")), html.escape("; ".join(reasons))] for day, reasons in found]
    st.markdown(_table(["Day", "Why it stands out"], body, theme.is_dark()), unsafe_allow_html=True)


def rain_events_page() -> None:
    s = load_settings()
    tz = _tz(s)
    metric = units.is_metric(s.units)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("Rain events"), unsafe_allow_html=True)
    options = {"7 days": 7, "30 days": 30}
    choice = st.radio("Range", list(options), index=1, horizontal=True, key="rain_events_range")
    start = datetime.combine(today - timedelta(days=options[choice]), datetime.min.time(), tzinfo=tz).timestamp()
    end = datetime.combine(today + timedelta(days=1), datetime.min.time(), tzinfo=tz).timestamp()
    found = rain_events.events(storage.readings_between(db, start, end))
    if not found:
        st.info("No rain in this range.")
        return
    wettest = max(found, key=lambda e: e["inches"])
    total = sum(e["inches"] for e in found)
    st.markdown(theme.grid_html([
        _tile("Rain events", str(len(found))),
        _tile("Total", units.format_value("dailyrainin", total, metric, 2)),
        _tile("Wettest event", units.format_value("dailyrainin", wettest["inches"], metric, 2),
              datetime.fromtimestamp(wettest["start"], tz).strftime("%b %d, %I:%M %p")),
    ]), unsafe_allow_html=True)
    body = []
    for e in reversed(found):
        minutes = max(1, round((e["end"] - e["start"]) / 60))
        length = f"{minutes // 60} h {minutes % 60} min" if minutes >= 60 else f"{minutes} min"
        peak = units.convert("dailyrainin", e["peak_rate"], metric)
        peak_text = f"{peak:.{1 if metric else 2}f} {units.unit('dailyrainin', metric)}/hr"
        body.append([html.escape(datetime.fromtimestamp(e["start"], tz).strftime("%a %b %d, %I:%M %p")),
                     html.escape(length), html.escape(units.format_value("dailyrainin", e["inches"], metric, 2)),
                     html.escape(peak_text)])
    st.markdown(_table(["Started", "Length", "Rain", "Peak rate"], body, theme.is_dark()), unsafe_allow_html=True)


def rankings_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    st.markdown(theme.title_html("Rankings"), unsafe_allow_html=True)
    days = _all_days(stations.current())
    if not days:
        st.info("Rankings appear once there are daily summaries. Each day's summary is written once that day's readings are in.")
        return
    choice = st.selectbox("Rank the days by", list(RANKINGS), key="rank_choice")
    key, kind, unit_key, unit_text, decimals = RANKINGS[choice]
    top = yearly.ranking(days, key, kind, 10)
    if not top:
        st.info("No days have that measure yet.")
        return
    rows = []
    for i, (day, value) in enumerate(top, 1):
        text = _fmt(unit_key, value, metric, decimals) if unit_key else f"{value:.{decimals}f} {unit_text}".strip()
        rows.append([str(i), day.strftime("%a %b %d, %Y"), text])
    st.markdown(_table(["#", "Day", choice], rows, dark), unsafe_allow_html=True)


def rewind_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    today = datetime.now(_tz(s)).date()
    st.markdown(theme.title_html("Rewind"), unsafe_allow_html=True)
    days = _all_days(stations.current())
    picked = st.date_input("Day and month to look up", value=today, max_value=today, key="rewind_day")
    rows = yearly.on_this_day(days, picked.month, picked.day)
    if not rows:
        st.info(f"No summaries for {picked.strftime('%B %d')} yet.")
        return
    tiles = []
    for day, sm in rows:
        note = f"Rain {_fmt('dailyrainin', sm['rain_in'], metric, 2)}" if sm.get("rain_in") is not None else ""
        value = f"{_fmt('tempf', sm.get('tempf_max'), metric)} / {_fmt('tempf', sm.get('tempf_min'), metric)}"
        tiles.append(_tile(str(day.year), value, note))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    with_high = [(day, sm) for day, sm in rows if sm.get("tempf_max") is not None]
    fig = charts.figure(dark, height=300)
    fig.add_trace(go.Bar(x=[str(day.year) for day, _ in with_high],
                         y=[units.convert("tempf", sm["tempf_max"], metric) for _, sm in with_high],
                         name=f"High ({units.unit('tempf', metric)})", marker_color=charts.CHART_COLORS[3]))
    charts.show(fig)


def _year_over_year(dark: bool, metric: bool) -> None:
    """Daily highs for two years drawn over each other, so this year can be compared with last year."""
    days = _all_days(stations.current())
    years = sorted({d.year for d, _ in days})
    if len(years) < 2:
        return
    st.markdown(theme.section_html("Daily highs, one year against another"), unsafe_allow_html=True)
    left, right = st.columns(2)
    with left:
        year_a = st.selectbox("First year", years, index=len(years) - 1, key="yoy_a")
    with right:
        year_b = st.selectbox("Second year", years, index=len(years) - 2, key="yoy_b")
    fig = charts.figure(dark, height=340)
    for i, year in enumerate([year_a, year_b]):
        pts = [(date(2000, d.month, d.day), summary.get("tempf_max")) for d, summary in days if d.year == year]
        fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[units.convert("tempf", p[1], metric) for p in pts],
                                 name=str(year), line=dict(color=charts.CHART_COLORS[i * 3])))
    fig.update_xaxes(tickformat="%b")
    charts.show(fig)


def climate_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    st.markdown(theme.title_html("Climate charts"), unsafe_allow_html=True)
    table = yearly.monthly(_all_days(stations.current()))
    if not table:
        st.info("Monthly charts appear once there are daily summaries. Each day's summary is written once that day's readings are in.")
        return
    years = sorted(table)
    months = [calendar.month_abbr[m] for m in range(1, 13)]

    def cell(year: int, month: int, field: str):
        return table.get(year, {}).get(month, {}).get(field)

    temp_unit = units.unit("tempf", metric)
    heat = charts.figure(dark, height=max(260, 40 * len(years) + 90))
    heat.add_trace(go.Heatmap(
        z=[[units.convert("tempf", cell(y, m, "temp"), metric) for m in range(1, 13)] for y in years],
        x=months, y=[str(y) for y in years], colorscale="RdYlBu_r", colorbar=dict(title=temp_unit)))
    heat.update_yaxes(autorange="reversed")
    st.markdown(theme.section_html(f"Average temperature by month ({temp_unit})"), unsafe_allow_html=True)
    charts.show(heat)

    rain = charts.figure(dark, height=340)
    for year in years:
        rain.add_trace(go.Bar(x=months, name=str(year),
                              y=[units.convert("dailyrainin", cell(year, m, "rain"), metric) for m in range(1, 13)]))
    rain.update_layout(barmode="group")
    st.markdown(theme.section_html(f"Rain by month ({units.unit('dailyrainin', metric)})"), unsafe_allow_html=True)
    charts.show(rain)
    _year_over_year(dark, metric)


def my_year_page() -> None:
    s = load_settings()
    metric, dark = units.is_metric(s.units), theme.is_dark()
    st.markdown(theme.title_html("My year"), unsafe_allow_html=True)
    days = _all_days(stations.current())
    years = sorted({day.year for day, _ in days}, reverse=True)
    if not years:
        st.info("A year in review appears once there are daily summaries.")
        return
    year = st.selectbox("Year", years, key="my_year_pick")
    summary = yearly.year_summary(days, year, hot_f=100.4 if metric else 100.0, freeze_f=32.0)
    tiles = [_tile("Days with data", str(summary["days"])),
             _tile("Rain total", _fmt("dailyrainin", summary["rain"], metric, 2)),
             _tile("Rainy days", str(summary["rainy_days"]))]
    if summary["hottest"]:
        day, value = summary["hottest"]
        tiles.append(_tile("Hottest day", _fmt("tempf", value, metric), day.strftime("%b %d")))
    if summary["coldest"]:
        day, value = summary["coldest"]
        tiles.append(_tile("Coldest low", _fmt("tempf", value, metric), day.strftime("%b %d")))
    if summary["windiest"]:
        day, value = summary["windiest"]
        tiles.append(_tile("Windiest gust", _fmt("windgustmph", value, metric), day.strftime("%b %d")))
    tiles.append(_tile("Days at 38°C or hotter" if metric else "Days at 100°F or hotter", str(summary["hot_days"])))
    tiles.append(_tile("Days at or below freezing", str(summary["freezing"])))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    monthly_rain = yearly.monthly(days).get(year, {})
    if monthly_rain:
        months = sorted(monthly_rain)
        fig = charts.figure(dark, height=300)
        fig.add_trace(go.Bar(x=[calendar.month_abbr[m] for m in months],
                             y=[units.convert("dailyrainin", monthly_rain[m]["rain"], metric) for m in months],
                             name=f"Rain ({units.unit('dailyrainin', metric)})", marker_color=charts.CHART_COLORS[0]))
        charts.show(fig)


# ---------------------------------------------------------------- Forecast

@st.cache_data(ttl=86400, show_spinner=False)
def _points(lat: float, lon: float, contact: str) -> dict:
    return nws.points(lat, lon, contact)


@st.cache_data(ttl=600, show_spinner=False)
def _alerts(lat: float, lon: float, contact: str) -> list[dict]:
    return nws.alerts(lat, lon, contact)


@st.cache_data(ttl=1800, show_spinner=False)
def _daily(url: str, contact: str) -> list[dict]:
    return nws.forecast_daily(url, contact)


@st.cache_data(ttl=1800, show_spinner=False)
def _hourly(url: str, contact: str) -> list[dict]:
    return nws.forecast_hourly(url, contact)


def _alert_box(a: dict) -> str:
    color = nws.SEVERITY_COLORS.get(a["severity"], nws.SEVERITY_COLORS["Unknown"])
    expires = f"Until {html.escape(a['expires'][:16].replace('T', ' '))}" if a["expires"] else ""
    return (f'<div class="wl-tile" style="border-left:4px solid {color};border-radius:8px;margin-bottom:8px">'
            f'<div class="wl-label" style="color:{color}">{html.escape(a["severity"].upper())}</div>'
            f'<div class="wl-value" style="font-size:16px">{html.escape(a["event"])}</div>'
            f'<div class="wl-label">{html.escape(a["headline"])}</div>'
            f'<div class="wl-label">{expires}</div></div>')


def _forecast_accuracy(db, s: Settings) -> None:
    """How far the saved forecast highs were from what actually happened."""
    metric = units.is_metric(s.units)
    scale, unit = (5 / 9, "°C") if metric else (1, "°F")

    def delta(x: float) -> str:
        return f"{x * scale:.1f} {unit}"

    forecasts = storage.forecast_highs(db)
    actuals = {d: summary["tempf_max"] for d, summary in history.all_daily(db) if summary.get("tempf_max") is not None}
    rows = forecast_check.compare(forecasts, actuals)[:60]
    stats = forecast_check.accuracy(rows)
    st.markdown(theme.section_html("How accurate the forecast has been"), unsafe_allow_html=True)
    error = start_poller().status.forecast_error
    if error:
        st.caption(f"Couldn't save the forecast: {error}")
    if not stats["days"]:
        st.caption("This check starts once Weather Lab has saved a forecast and a day has finished. Forecasts are saved every three hours.")
        return
    sign = "+" if stats["bias"] > 0 else ""
    st.markdown(theme.grid_html([
        _tile("Average miss", delta(stats["mae"]), f"last {stats['days']} days"),
        _tile("Forecast bias", sign + delta(stats["bias"]), "plus means it ran high"),
    ]), unsafe_allow_html=True)
    body = [[html.escape(d.strftime("%a %b %d")), html.escape(units.format_value("tempf", f, metric, 0)),
             html.escape(units.format_value("tempf", a, metric, 0)), html.escape(delta(diff))]
            for d, f, a, diff in rows[:14]]
    st.markdown(_table(["Day", "Forecast high", "Actual high", "Forecast minus actual"], body, theme.is_dark()),
                unsafe_allow_html=True)


def _rain_accuracy(db, s: Settings) -> None:
    """How often rain was forecast, and how often it actually fell."""
    pops = storage.forecast_pops(db)
    rained = {d: (summary.get("rain_in") or 0.0) >= 0.01 for d, summary in history.all_daily(db)}
    stats = forecast_check.rain_summary(pops, rained)
    if not stats["wet_days"] and not stats["dry_days"]:
        return
    st.markdown(theme.section_html("How accurate the rain chance has been"), unsafe_allow_html=True)
    st.markdown(theme.grid_html([
        _tile("Forecast 50% or more", f"{stats['wet_rained']} of {stats['wet_days']}", "days it rained"),
        _tile("Forecast under 50%", f"{stats['dry_rained']} of {stats['dry_days']}", "days it rained"),
    ]), unsafe_allow_html=True)


def forecast_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html("Forecast"), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        st.info("Set your latitude and longitude on the Setup page.")
        return
    contact = s.nws_contact

    try:
        alerts = _alerts(s.latitude, s.longitude, contact)
        if alerts:
            st.markdown("".join(_alert_box(a) for a in alerts), unsafe_allow_html=True)
        else:
            st.markdown(theme.grid_html([_tile("Weather alerts", "None active")]), unsafe_allow_html=True)
        pts = _points(s.latitude, s.longitude, contact)
        periods = _daily(pts["forecast"], contact)
        hourly = _hourly(pts["forecastHourly"], contact) if pts.get("forecastHourly") else []
    except nws.NwsError as exc:
        st.error(str(exc))
        return

    metric = units.is_metric(s.units)
    now = datetime.now(tz)
    views = forecast_view.overview_html(hourly, s.latitude, s.longitude, tz, metric, len(alerts), now)
    views += forecast_view.days_html(periods, tz, metric, now.date())
    if views:
        st.markdown(forecast_view.STYLE + views, unsafe_allow_html=True)
    _forecast_accuracy(storage.connect(), s)
    _rain_accuracy(storage.connect(), s)


# ---------------------------------------------------------------- Air

def air_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html("Air quality"), unsafe_allow_html=True)
    if not secrets.get_key("airnow"):
        st.info("Add a free AirNow API key on the Setup page to see air quality.")
        return
    if s.latitude is None or s.longitude is None:
        st.info("Set your latitude and longitude on the Setup page.")
        return

    poller = start_poller()
    row = storage.latest_aqi(storage.connect())
    if row is None:
        st.info("No air quality reading yet. Weather Lab checks AirNow about every 30 minutes, and AirNow updates about once an hour.")
        if poller.status.aqi_error:
            st.warning(poller.status.aqi_error)
        return

    ts, data = row
    risk = data.get("risk", "")
    color = RISK_COLORS.get(risk, "#6b7280")
    aqi_tile = (f'<div class="wl-tile" style="border-left:4px solid {color};border-radius:8px">'
                f'<div class="wl-label">Air quality index</div>'
                f'<div class="wl-value">{html.escape(str(data.get("aqi", "--")))}</div>'
                f'<div class="wl-label" style="color:{color}">{html.escape(str(data.get("category", "")))}</div>'
                f'<div class="wl-label">{html.escape(str(data.get("station", "")))} · updated {_clock(ts)}</div></div>')
    tiles = [aqi_tile]
    for name, key in airquality.POLLUTANTS.items():
        if data.get(key) is not None:
            tiles.append(_tile(name, f"{data[key]:g}"))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)
    if poller.status.aqi_error:
        st.warning(poller.status.aqi_error)


# ---------------------------------------------------------------- Lightning

def lightning_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    now = datetime.now(tz)
    metric = units.is_metric(s.units)
    st.markdown(theme.title_html("Lightning"), unsafe_allow_html=True)
    start_of_day = datetime.combine(now.date(), datetime.min.time(), tzinfo=tz).timestamp()
    today = storage.strikes_between(db, start_of_day, now.timestamp())
    last = storage.latest_strike(db)

    if last is None:
        st.info("No lightning recorded yet. Strikes appear here when the station reports them.")
    else:
        last_ts, last_mi = last
        when = datetime.fromtimestamp(last_ts, tz).strftime("%b %d, %H:%M")
        closest = min((d for _, d in today), default=None)
        st.markdown(theme.grid_html([
            _tile("Last strike", units.format_value("miles", last_mi, metric, 1), when),
            _tile("Strikes today", str(len(today)), "seen while the app runs"),
            _tile("Closest today", units.format_value("miles", closest, metric, 1)),
        ]), unsafe_allow_html=True)

    if today:
        st.markdown("**Today**")
        st.table([{"time": datetime.fromtimestamp(ts, tz).strftime("%H:%M"),
                   f"Distance ({units.unit('miles', metric)})": round(units.convert("miles", d, metric), 1)}
                  for ts, d in reversed(today[-20:])])
    st.caption("Counts only strikes the app saw while it was running. Distances follow the switch on the Setup page.")

    st.subheader("History")
    span_choice = st.radio("Range", ["30 days", "1 year"], index=0, horizontal=True, key="lightning_range")
    span = 30 if span_choice == "30 days" else 365
    since = datetime.combine(now.date() - timedelta(days=span - 1), datetime.min.time(), tzinfo=tz).timestamp()
    by_day = lightning_history.per_day(storage.strikes_between(db, since, now.timestamp()), tz)
    if not by_day:
        st.info("No strikes in this range.")
    else:
        dark = theme.is_dark()
        days = [d for d, _, _ in by_day]
        counts_fig = charts.figure(dark)
        counts_fig.add_trace(go.Bar(x=days, y=[c for _, c, _ in by_day], name="Strikes",
                                    marker_color=charts.CHART_COLORS[2]))
        charts.show(counts_fig)
        closest_fig = charts.figure(dark)
        closest_fig.add_trace(go.Scatter(x=days, y=[units.convert("miles", m, metric) for _, _, m in by_day],
                                         name=f"Closest strike ({units.unit('miles', metric)})",
                                         mode="markers+lines", line=dict(color=charts.CHART_COLORS[4])))
        charts.show(closest_fig)


# ---------------------------------------------------------------- Fire

def _fire_day_note(f: dict, metric: bool) -> str:
    """Temperature, humidity and wind for one forecast day, in the chosen units."""
    if not metric:
        return f"{f['temperature']}°F · {f['humidity']}% · {f['wind_speed']} mph"
    import re
    temp = f"{units.convert('tempf', f['temperature'], True):.0f} °C"
    wind = re.sub(r"\d+(?:\.\d+)?", lambda m: f"{float(m.group(0)) * units.speed_factor(True):.0f}",
                  str(f["wind_speed"]).replace(" mph", "").replace("mph", ""))
    return f"{temp} · {f['humidity']}% · {wind} km/h"


def fire_page() -> None:
    db = storage.connect()
    st.markdown(theme.title_html("Fire weather"), unsafe_allow_html=True)
    rec = storage.latest_fire(db)
    if rec is None:
        st.info("Fire weather appears once the station has sent readings for an hour. It updates every hour.")
        return
    st.markdown(theme.grid_html([
        _tile("Fire Weather Index", f"{rec['fwi']:.1f}", f"as of {rec['timestamp'][11:16]}"),
        _tile("FFMC", f"{rec['ffmc']:.1f}", "fine fuels"),
        _tile("DMC", f"{rec['dmc']:.1f}", "duff layer"),
        _tile("DC", f"{rec['dc']:.1f}", "deep drought"),
        _tile("ISI", f"{rec['isi']:.1f}", "spread index"),
        _tile("BUI", f"{rec['bui']:.1f}", "build-up index"),
        _tile("Days since rain", str(rec["days_since_rain"])),
    ]), unsafe_allow_html=True)

    forecast = rec.get("forecast") or []
    if len(forecast) > 1:
        st.markdown("**Forecast**")
        st.markdown(theme.grid_html([
            _tile(f["day"], f"{f['fwi']:.1f}", _fire_day_note(f, units.is_metric(load_settings().units)))
            for f in forecast[1:]
        ]), unsafe_allow_html=True)
    else:
        st.caption("No forecast yet. It comes from the National Weather Service, so it covers the United States only.")
    st.caption("Approximate. It uses the latest reading instead of the usual 1 pm observation, assumes no rain in "
               "the forecast, and uses day-length values for about 30° north.")


# ---------------------------------------------------------------- Reports

def reports_page() -> None:
    s = load_settings()
    today = datetime.now(_tz(s)).date()
    db = storage.connect()
    st.markdown(theme.title_html("Reports"), unsafe_allow_html=True)
    kind = st.radio("Report", ["Monthly", "Yearly"], horizontal=True)
    year = st.number_input("Year", min_value=2000, max_value=today.year, value=today.year, step=1)
    if kind == "Monthly":
        names = [datetime(2000, m, 1).strftime("%B") for m in range(1, 13)]
        month = st.selectbox("Month", range(1, 13), index=today.month - 1, format_func=lambda m: names[m - 1])
        first = date(int(year), month, 1)
        last = date(int(year) + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
        rows = history.daily_between(db, first, last)
        if not rows:
            st.info("No daily summaries for that month yet.")
            return
        st.download_button("Download monthly report", data=report.monthly_pdf(int(year), month, rows, units.is_metric(load_settings().units)),
                           file_name=f"weather_report_{int(year)}_{month:02d}.pdf", mime="application/pdf")
    else:
        rows = history.daily_between(db, date(int(year), 1, 1), date(int(year), 12, 31))
        if not rows:
            st.info("No daily summaries for that year yet.")
            return
        st.download_button("Download yearly report", data=report.yearly_pdf(int(year), rows, units.is_metric(load_settings().units)),
                           file_name=f"weather_report_{int(year)}.pdf", mime="application/pdf")


# ---------------------------------------------------------------- Import

def _import_flow(title: str, file_types: list[str], default_units: str, intro: str) -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html(title), unsafe_allow_html=True)
    st.write(intro)
    up = st.file_uploader("File", type=file_types, key=f"{title}-file")
    if up is None:
        return
    try:
        headers, rows = importer.read_file(up.getvalue(), up.name)
    except importer.ImportProblem as exc:
        st.error(str(exc))
        return
    if not headers or not rows:
        st.error("The file has no rows to import.")
        return

    time_guess = importer.guess_time_column(headers)
    time_col = st.selectbox("Time column", headers,
                            index=headers.index(time_guess) if time_guess else 0, key=f"{title}-time")
    units = st.radio("Units in this file", ["Imperial (°F, mph, inHg, in)", "Metric (°C, km/h, hPa, mm)"],
                     index=0 if default_units == "imperial" else 1, horizontal=True, key=f"{title}-units")
    units_key = "metric" if units.startswith("Metric") else "imperial"

    guessed = importer.guess_mapping(headers, time_col)
    st.caption("Match each column to a reading. Choose Ignore to skip a column.")
    options = ["Ignore", *importer.READING_KEYS]
    mapping = {}
    for h in headers:
        if h == time_col:
            continue
        choice = st.selectbox(h, options, index=options.index(guessed.get(h, "Ignore")), key=f"{title}-map-{h}")
        if choice != "Ignore":
            mapping[h] = choice
    if not mapping:
        st.warning("Match at least one column to a reading.")
        return
    if len(set(mapping.values())) != len(mapping):
        st.error("Two columns are matched to the same reading. Change one of them to Ignore.")
        return

    try:
        readings = importer.build_readings(rows, time_col, mapping, tz, units_key)
    except importer.ImportProblem as exc:
        st.error(str(exc))
        return
    first = datetime.fromtimestamp(min(ts for ts, _ in readings), tz)
    last = datetime.fromtimestamp(max(ts for ts, _ in readings), tz)
    st.write(f"Found {len(readings)} readings from {first:%b %d, %Y} to {last:%b %d, %Y}.")
    if st.button("Import readings", key=f"{title}-go"):
        with st.spinner("Importing and rebuilding daily summaries..."):
            result = importer.store(storage.connect(), readings, s.latitude or 0.0, s.longitude or 0.0,
                                    s.elevation_m, tz)
        st.success(f"Imported {result['inserted']} readings across {result['days']} days. "
                   f"{result['skipped']} were already stored.")


def csv_import_page() -> None:
    _import_flow("CSV Import", ["csv"], "imperial",
                 "Upload a CSV file of past readings. Columns are matched to readings automatically. "
                 "Check the matches, then import. Only the file you choose is read.")


def excel_import_page() -> None:
    _import_flow("Excel Import", ["xlsx"], "imperial",
                 "Upload an Excel (.xlsx) file of past readings. The first sheet is used. "
                 "Columns are matched automatically. Check the matches, then import.")


def weather_underground_page() -> None:
    _import_flow("Weather Underground", ["csv"], "imperial",
                 "Upload a history CSV downloaded from Weather Underground. Its column names are matched "
                 "automatically, and its units are imperial by default.")


# ---------------------------------------------------------------- Export

def _backups_section(s: Settings) -> None:
    """Daily database backups: the on/off setting, how many copies are kept, and a button to back up now."""
    folder = backup.folder_for(storage.db_path())
    st.markdown("**Database backups**")
    enabled = st.checkbox("Back up the database once a day", value=s.backup_enabled, key="backup_on")
    keep = int(st.number_input("Backups to keep", min_value=1, max_value=365, value=int(s.backup_keep), step=1,
                               key="backup_keep"))
    if enabled != s.backup_enabled or keep != s.backup_keep:
        save_settings(replace(s, backup_enabled=enabled, backup_keep=keep))
    copy_to = st.text_input("Also copy each backup to this folder (optional)", value=s.backup_copy_folder,
                            key="backup_copy", help="For example a USB drive or a synced cloud folder.")
    if copy_to.strip() != s.backup_copy_folder.strip():
        save_settings(replace(s, backup_copy_folder=copy_to.strip()))
    error = start_poller().status.backup_error
    if error:
        st.warning(error)
    items = backup.backups(folder)
    if items:
        newest = datetime.fromtimestamp(items[-1].stat().st_mtime)
        st.caption(f"{len(items)} kept. Newest: {newest:%b %d, %Y %H:%M}. Saved in {folder}.")
    else:
        st.caption(f"No backups yet. They are saved in {folder}.")
    if st.button("Back up now"):
        path = backup.make_backup(storage.db_path(), folder, datetime.now())
        backup.prune(folder, keep)
        try:
            backup.copy_to_folder(path, copy_to, keep)
        except OSError as exc:
            st.warning(f"Couldn't copy the backup to that folder: {exc}")
        st.success(f"Saved {path.name}.")
    if items:
        pick = st.selectbox("Backup to restore", list(reversed(items)), format_func=lambda p: p.name, key="restore_pick")
        sure = st.checkbox("Replace the current data with this backup", key="restore_sure")
        if st.button("Restore", disabled=not sure):
            try:
                safety = backup.restore(pick, storage.db_path(), folder, datetime.now())
            except (OSError, sqlite3.Error) as exc:
                st.error(f"Couldn't restore: {exc}")
            else:
                st.success(f"Restored {pick.name}. The data from before the restore is saved as {safety.name}. "
                           "Restart Weather Lab so every page shows the restored data.")


def _daily_export(db, today: date) -> None:
    """Download one row per day: the highs, lows, rain, wind and sun for the range you choose."""
    st.markdown("**Daily summaries as a spreadsheet file**")
    st.caption("Values are in US units: degrees Fahrenheit, inches, miles per hour, miles and hours.")
    start = st.date_input("Daily summaries from", value=today - timedelta(days=365), max_value=today, key="daily_csv_from")
    end = st.date_input("Daily summaries to", value=today - timedelta(days=1), max_value=today, key="daily_csv_to")
    if end < start:
        st.error("The end date is before the start date.")
        return
    rows = history.daily_between(db, start, end)
    if not rows:
        st.info("No daily summaries in that range.")
        return
    st.download_button("Download daily summaries (CSV)", data=history.daily_csv(rows),
                       file_name=f"weather_daily_{start.isoformat()}_{end.isoformat()}.csv", mime="text/csv")


def export_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("Export"), unsafe_allow_html=True)
    _daily_export(db, today)
    st.divider()
    st.markdown("**Readings as CSV**")
    st.write("Download readings as a CSV file. It uses the same format as the CSV Import page, so you can "
             "import it on another computer. Times are in the timezone on the Setup page.")
    start = st.date_input("From", value=today - timedelta(days=30), max_value=today)
    end = st.date_input("To", value=today, max_value=today)
    if end < start:
        st.error("The end date is before the start date.")
        return
    start_ts = datetime.combine(start, datetime.min.time(), tzinfo=tz).timestamp()
    end_ts = datetime.combine(end + timedelta(days=1), datetime.min.time(), tzinfo=tz).timestamp()
    rows = storage.readings_between(db, start_ts, end_ts)
    if not rows:
        st.info("No readings in that range. Try a wider range, or check that the station has been reporting.")
        return
    st.write(f"{len(rows)} readings ready.")
    st.download_button("Download CSV", data=importer.export_csv(rows, tz),
                       file_name=f"weather_readings_{start.isoformat()}_{end.isoformat()}.csv", mime="text/csv")


# ---------------------------------------------------------------- Sensors

def sensors_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    st.markdown(theme.title_html("Sensors"), unsafe_allow_html=True)
    now = time.time()
    rows = health.window(db, now - 24 * 3600, now)
    if not rows:
        st.info("No readings in the last 24 hours yet. Check the station's connection on the Live page.")
        return

    last_ts = rows[-1][0]
    status, age_text = health.age_status(last_ts, now)
    gap_list = health.gaps(rows)
    st.markdown(theme.grid_html([
        _tile("Completeness (24 h)", f"{health.completeness(rows, 24):.0f}%"),
        _tile("Last reading", age_text.capitalize(),
              {"ok": "Good", "slow": "Delayed", "silent": "Offline", "none": ""}[status]),
        _tile("Gaps over 5 min", str(len(gap_list))),
    ]), unsafe_allow_html=True)

    tiles = []
    for sensor in health.sensors(rows):
        seen = (health.clock(sensor["last_seen"], tz) if sensor["last_seen"] else "never")
        tiles.append(_tile(sensor["label"], f"{sensor['present_pct']:.0f}%", f"last seen {seen}"))
    st.markdown(theme.grid_html(tiles), unsafe_allow_html=True)

    if gap_list:
        st.markdown("**Recent gaps**")
        st.table([{"from": health.clock(a, tz), "to": health.clock(b, tz),
                   "minutes": round((b - a) / 60)} for a, b in gap_list[-10:]])


# ---------------------------------------------------------------- main

# ---------------------------------------------------------------- Heat, wind, sun, tropics, radar

RADAR_RIDGE = "https://radar.weather.gov/ridge/standard/"
WIND_PERIODS = {"Last 24 hours": 1, "Last 7 days": 7, "Last 30 days": 30}


def _start_of_today(s: Settings) -> float:
    return datetime.now(_tz(s)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()


def _degrees(x, unit: str = "°F", fmt: str = ".0f") -> str:
    return "--" if x is None else f"{format(x, fmt)}{unit}"


def heat_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    metric = units.is_metric(s.units)
    db = storage.connect()
    st.markdown(theme.title_html("Heat safety"), unsafe_allow_html=True)
    latest = storage.latest(db)
    if latest is None:
        st.info("No readings yet. Heat safety fills in once the station has reported.")
        return
    _, data = latest
    now = heat_safety.status(data.get("tempf"), data.get("humidity"))
    today = storage.readings_between(db, _start_of_today(s), time.time() + 1)
    series = [(ts, r.get("tempf"), heat_safety.heat_index(r.get("tempf"), r.get("humidity"))) for ts, r in today]
    peak = max((x for x in series if x[2] is not None), key=lambda x: x[2], default=None)
    st.markdown(theme.grid_html([
        _tile("Heat index now", units.format_value("heat_index", now["heat_index"], metric, 0), now["level"]),
        _tile("Air temperature", units.format_value("tempf", data.get("tempf"), metric, 0), "right now"),
        _tile("Highest heat index today", units.format_value("heat_index", peak[2] if peak else None, metric, 0),
              _clock(peak[0]) if peak else "no data yet"),
    ]), unsafe_allow_html=True)
    if now["advice"]:
        show = st.warning if now["level"] in ("Extreme caution", "Danger", "Extreme danger") else st.info
        show(now["advice"])
    fig = charts.figure(dark)
    xs = [datetime.fromtimestamp(ts, _tz(s)) for ts, _, _ in series]
    fig.add_scatter(x=xs, y=[units.convert("tempf", t, metric) for _, t, _ in series], name="Air temperature", mode="lines",
                    line=dict(color=charts.CHART_COLORS[0]))
    fig.add_scatter(x=xs, y=[units.convert("heat_index", h, metric) for _, _, h in series], name="Heat index", mode="lines",
                    line=dict(color=charts.CHART_COLORS[1]))
    charts.show(fig)
    st.caption("Heat index combines air temperature and humidity. This is general guidance, not medical advice.")


def wind_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    metric = units.is_metric(s.units)
    db = storage.connect()
    st.markdown(theme.title_html("Wind"), unsafe_allow_html=True)
    period = st.segmented_control("Period", list(WIND_PERIODS), default="Last 24 hours",
                                  key="wind_period", label_visibility="collapsed") or "Last 24 hours"
    end = time.time()
    rows = [r for _, r in storage.readings_between(db, end - WIND_PERIODS[period] * 86400, end + 1)]
    counts, total = wind_rose.rose(rows)
    if total == 0:
        st.info("No wind readings for this period yet.")
        return
    speeds = [r["windspeedmph"] for r in rows if r.get("windspeedmph") is not None]
    gusts = [r["windgustmph"] for r in rows if r.get("windgustmph") is not None]
    st.markdown(theme.grid_html([
        _tile("Average wind", units.format_value("windspeedmph", sum(speeds) / len(speeds), metric, 1)),
        _tile("Strongest gust", units.format_value("windgustmph", max(gusts) if gusts else None, metric, 0)),
        _tile("Most common direction", wind_rose.dominant(counts)),
    ]), unsafe_allow_html=True)
    pct = wind_rose.percentages(counts, total)
    fig = charts.figure(dark, height=480)
    for i in range(len(wind_rose.SPEED_BINS)):
        fig.add_barpolar(r=pct[i], theta=wind_rose.NAMES, name=wind_rose.label(i, metric),
                         marker_color=charts.CHART_COLORS[i % len(charts.CHART_COLORS)])
    fig.update_layout(polar=dict(barmode="stack", angularaxis=dict(direction="clockwise", rotation=90),
                                 radialaxis=dict(ticksuffix="%")))
    charts.show(fig)
    st.caption("Each wedge shows how often the wind came from that direction, coloured by speed.")


def sun_page() -> None:
    s = load_settings()
    dark = theme.is_dark()
    db = storage.connect()
    st.markdown(theme.title_html("Sun and UV"), unsafe_allow_html=True)
    latest = storage.latest(db)
    if latest is None:
        st.info("No readings yet. Sun and UV fill in once the station has reported.")
        return
    _, data = latest
    end = time.time()
    week = storage.readings_between(db, end - 7 * 86400, end + 1)
    today_start = _start_of_today(s)
    sun_week = [(ts, r.get("solarradiation")) for ts, r in week]
    sun_today = [x for x in sun_week if x[0] >= today_start]
    uv_today = [(ts, r.get("uv")) for ts, r in week if ts >= today_start]
    uv_peak = max((u for _, u in uv_today if u is not None), default=None)
    uv_now = data.get("uv")
    st.markdown(theme.grid_html([
        _tile("UV index now", "--" if uv_now is None else f"{uv_now:.1f}"),
        _tile("UV peak today", "--" if uv_peak is None else f"{uv_peak:.1f}"),
        _tile("Sunshine today", f"{sun_uv.sunshine_hours(sun_today):.1f} h"),
        _tile("Sunshine, last 7 days", f"{sun_uv.sunshine_hours(sun_week):.1f} h"),
    ]), unsafe_allow_html=True)
    st.subheader("Sunburn time at this UV index")
    st.table([{"Skin type": k, "Minutes until sunburn": "--" if m is None else f"{m:.0f}"}
              for k in sun_uv.MED_J_M2 for m in [sun_uv.burn_minutes(uv_now, k)]])
    fig = charts.figure(dark)
    fig.add_scatter(x=[datetime.fromtimestamp(ts, _tz(s)) for ts, _ in uv_today], y=[u for _, u in uv_today],
                    mode="lines", name="UV index", line=dict(color=charts.CHART_COLORS[2]))
    charts.show(fig)
    st.caption("Estimates from the station's UV reading. They assume full sun with no shade and no sunscreen.")


def _moving(x: dict, metric: bool) -> str:
    """Direction and speed a storm is moving, in the chosen units."""
    if x.get("move_mph") is None:
        return x["move"] or "--"
    speed = round(units.convert("windspeedmph", x["move_mph"], metric))
    return f"{x['move_dir']} at {speed} {units.speed_unit(metric)}"


def tropics_page() -> None:
    s = load_settings()
    metric = units.is_metric(s.units)
    st.markdown(theme.title_html("Tropics"), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        st.info("Set your latitude and longitude on the Setup page to see how far each storm is from you.")
        return
    cache = tropics.refresh((s.latitude, s.longitude), storage.db_path().parent / "tropics.json")
    if not cache.get("checked"):
        st.warning(f"Couldn't reach the National Hurricane Center ({cache.get('error') or 'no answer'}). Try again later.")
        return
    if cache.get("ok"):
        st.caption(f"Checked the National Hurricane Center at {cache['checked']}.")
    else:
        st.caption(f"Couldn't reach the National Hurricane Center just now, so this is the list from {cache['checked']}.")
    storms = cache.get("storms", [])
    if not storms:
        st.success("The National Hurricane Center has no active tropical storms or hurricanes right now.")
        return
    st.dataframe([{"Storm": x["name"], "Type": x["class"], "Wind": units.format_value("windspeedmph", x["wind_mph"], metric, 0),
                   "Distance": units.format_value("miles", x["miles"], metric, 0), "From you": x["direction"], "Moving": _moving(x, metric),
                   "Updated": x["updated"]} for x in storms], hide_index=True)
    fig = go.Figure()
    fig.add_trace(go.Scattermap(lat=[s.latitude], lon=[s.longitude], mode="markers+text", marker=dict(size=14),
                                text=["You"], textposition="bottom center", name="You"))
    fig.add_trace(go.Scattermap(lat=[x["lat"] for x in storms], lon=[x["lon"] for x in storms],
                                mode="markers+text", marker=dict(size=16, color="#f59e0b"),
                                text=[x["name"] for x in storms], textposition="top center", name="Storms"))
    lats = [x["lat"] for x in storms] + [s.latitude]
    lons = [x["lon"] for x in storms] + [s.longitude]
    spread = max(max(lats) - min(lats), max(lons) - min(lons))
    fig.update_layout(map=dict(style="open-street-map", center=dict(lat=(max(lats) + min(lats)) / 2,
                                                                    lon=(max(lons) + min(lons)) / 2),
                               zoom=3 if spread > 20 else 4),
                      margin=dict(l=0, r=0, t=0, b=0), height=420, showlegend=False)
    charts.show(fig)


@st.cache_data(ttl=86400, show_spinner=False)
def _radar_station(lat: float, lon: float, contact: str) -> str:
    return nws.points(lat, lon, contact).get("radar", "")


def radar_page() -> None:
    s = load_settings()
    st.markdown(theme.title_html("Radar"), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        st.info("Set your latitude and longitude on the Setup page to show the radar for your area.")
        return
    station = ""
    try:
        station = _radar_station(s.latitude, s.longitude, s.nws_contact)
    except nws.NwsError as exc:
        st.warning(str(exc))
    views = {"US radar": RADAR_RIDGE + "CONUS_loop.gif"}
    if station:
        views = {"Local radar": RADAR_RIDGE + f"{station}_loop.gif", **views}
    default = next(iter(views))
    choice = st.segmented_control("View", list(views), default=default, key="radar_view",
                                  label_visibility="collapsed") or default
    st.image(views[choice], caption="Green is light rain; yellow and red are heavy. Pictures come from the National Weather Service.")
    if station:
        st.link_button("Open the full local radar", f"https://radar.weather.gov/station/{station.lower()}/standard")
    else:
        st.link_button("Open the full radar", "https://radar.weather.gov/")


def _alert_rules_section() -> None:
    s = load_settings()
    st.subheader("Alert rules")
    st.caption("Weather Lab shows a Windows notification when a reading crosses one of these rules. "
               "Each rule repeats at most once an hour.")
    metric = units.is_metric(s.units)
    rules = list(s.alert_rules)
    if not rules:
        st.caption("No rules yet.")
    for i, rule in enumerate(rules):
        left, right = st.columns([5, 1])
        left.write(alert_rules.describe(rule, metric))
        if right.button("Remove", key=f"rule-remove-{i}"):
            save_settings(replace(s, alert_rules=rules[:i] + rules[i + 1:]))
            st.rerun()
    labels = {label: key for key, (label, _) in alert_rules.METRICS.items()}
    with st.form("new-rule"):
        name = st.text_input("Name", placeholder="Extreme heat")
        watch = st.selectbox("Watch", list(labels))
        op = st.selectbox("When it is", list(alert_rules.OPS), format_func=alert_rules.OPS.get)
        value = st.number_input(f"Value ({'°C, km/h or mm' if metric else '°F, mph or inches'})",
                                value=round(units.convert("tempf", 110.0, metric), 1), step=1.0,
                                key=f"rule_value_{'c' if metric else 'f'}")
        if st.form_submit_button("Add rule"):
            key = labels[watch]
            rule = {"name": name.strip() or watch, "metric": key, "op": op,
                    "value": round(units.to_us(key, float(value), metric), 2)}
            problem = alert_rules.valid_rule(rule)
            if problem:
                st.error(problem)
            else:
                save_settings(replace(s, alert_rules=rules + [rule]))
                st.rerun()
    recent = start_poller().status.recent_alerts[:5]
    if recent:
        st.markdown("**Recent alerts**")
        for ts, text in recent:
            st.caption(f"{_clock(ts)}  {text}")


# ---------------------------------------------------------------- Status

@st.cache_data(ttl=300, show_spinner=False)
def _gateway_sensors(ip: str) -> list[dict] | None:
    """Battery and signal for each paired sensor, or None when the station can't be read."""
    try:
        return gateway_sensors.read(ip)
    except (OSError, ValueError):
        return None


def whats_new_page() -> None:
    st.markdown(theme.title_html("What's New"), unsafe_allow_html=True)
    for entry in whats_new.ENTRIES:
        st.markdown(f"**Version {entry['version']}** · {entry['date']}")
        st.markdown("\n".join(f"- {item}" for item in entry["items"]))


def status_page() -> None:
    s = load_settings()
    db = storage.connect()
    poller = start_poller()
    now = time.time()
    st.markdown(theme.title_html("Status"), unsafe_allow_html=True)

    latest = storage.latest(db)
    last_ts = latest[0] if latest else None
    reporting, age_text = health.age_status(last_ts, now)
    feed_errors = [e for e in (poller.status.last_error, poller.status.aqi_error, poller.status.cwop_error, poller.status.wu_error, poller.status.pws_error, poller.status.wc_error, poller.status.sensor_error) if e]
    if poller.status.skipped_log:
        with st.expander(f"Skipped readings ({poller.status.skipped} since Weather Lab started)"):
            for ts, reason in poller.status.skipped_log[:20]:
                st.write(f"{time.strftime('%b %d, %H:%M', time.localtime(ts))}: {reason}")

    ip = s.station_ip.strip()
    raw = _gateway_sensors(ip) if ip else []
    sensors = []
    for sensor in raw or []:
        battery, battery_text = gateway_sensors.battery_state(sensor["batt"])
        signal, signal_text = gateway_sensors.signal_state(sensor["signal"], sensor["rssi"])
        sensors.append({"name": sensor["name"], "battery": battery, "signal": signal,
                        "battery_text": battery_text, "signal_text": signal_text})
    ok, problems = station_status.summary(reporting, feed_errors, sensors)

    if ok:
        st.success("Everything looks normal.")
    else:
        st.warning("Needs attention:")
        st.markdown("\n".join(f"- {p}" for p in problems))
    st.markdown(theme.grid_html([
        _tile("Last reading", age_text.capitalize(),
              {"ok": "Good", "slow": "Delayed", "silent": "Offline", "none": ""}[reporting]),
        _tile("Sensors paired", "--" if raw is None or not ip else str(len(sensors))),
        _tile("Problems", str(len(problems))),
    ]), unsafe_allow_html=True)

    if not ip:
        st.info("Set the station IP on the Setup page to see sensor battery and signal.")
    elif raw is None:
        st.caption("Battery and signal aren't available right now. The station may be off or offline.")
    elif sensors:
        st.subheader("Sensors")
        st.table([{"Sensor": x["name"], "Battery": x["battery_text"] or "--",
                   "Radio signal": x["signal_text"] or "--"} for x in sensors])
    else:
        st.caption("No paired sensors were found.")
    st.caption("This page is checked on every visit. Battery and signal refresh about every five minutes.")


def health_check_page() -> None:
    """Whether the collector, database, disk, backups, notifications and settings are all working."""
    import os
    import shutil
    from pathlib import Path
    s = load_settings()
    poller = start_poller()
    now = time.time()
    db_file = storage.db_path()
    db = storage.connect()
    latest = storage.latest(db)
    backups = backup.backups(backup.folder_for(db_file))
    copy = s.backup_copy_folder.strip()
    settings_dir = settings_path().parent
    try:
        import plyer  # noqa: F401
        notifications_ok = True
    except ImportError:
        notifications_ok = False
    facts = {
        "poller_alive": poller.is_alive(),
        "latest_reading_ts": latest[0] if latest else None,
        "last_poll_ok": poller.status.last_ok,
        "last_poll_error": poller.status.last_error,
        "db_exists": db_file.exists(),
        "db_bytes": db_file.stat().st_size if db_file.exists() else 0,
        "disk_free_bytes": shutil.disk_usage(db_file.parent).free,
        "backup_enabled": s.backup_enabled,
        "backup_newest_ts": backups[-1].stat().st_mtime if backups else None,
        "backup_error": poller.status.backup_error,
        "copy_folder": copy or None,
        "copy_folder_ok": bool(copy) and Path(copy).is_dir() and os.access(copy, os.W_OK),
        "settings_writable": (not settings_dir.exists()) or os.access(settings_dir, os.W_OK),
        "notifications_ok": notifications_ok,
        "forecast_error": poller.status.forecast_error,
        "aqi_error": poller.status.aqi_error,
        "airnow_key": bool(secrets.get_key("airnow")),
        "allow_network": s.allow_network,
        "update_available": poller.status.update_available,
    }
    checks = health_check.evaluate(facts, now)
    st.markdown(theme.title_html("Health check"), unsafe_allow_html=True)
    if any(c["state"] in ("warn", "fail") for c in checks):
        st.warning(health_check.summary(checks))
    else:
        st.success(health_check.summary(checks))
    icons = {"ok": "✅ OK", "warn": "⚠️ Check", "fail": "❌ Problem", "info": "ℹ️ Info"}
    st.table([{"Check": c["name"], "Status": icons[c["state"]], "Details": c["detail"]} for c in checks])
    st.caption("Checked each time this page opens.")


# ---------------------------------------------------------------- Astronomy

def _local_time(dt, tz) -> str:
    return "--" if dt is None else dt.astimezone(tz).strftime("%I:%M %p").lstrip("0")


def astronomy_page() -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html("Astronomy"), unsafe_allow_html=True)
    if s.latitude is None or s.longitude is None:
        st.info("Set your location on the Setup page to see sunrise, sunset and the moon.")
        return

    now = datetime.now(timezone.utc)
    today = now.astimezone(tz).date()
    rise, set_ = astro.sun_times(s.latitude, s.longitude, today)
    if rise is None or set_ is None:
        length = "--"
    else:
        minutes = round((set_ - rise).total_seconds() / 60)
        length = f"{minutes // 60} h {minutes % 60} min"
    moon = astro.moon_phase(now)
    full = astro.next_phase(now, astro.FULL_AGE).astimezone(tz)
    new = astro.next_phase(now, 0).astimezone(tz)
    st.markdown(theme.grid_html([
        _tile("Sunrise", _local_time(rise, tz)),
        _tile("Sunset", _local_time(set_, tz)),
        _tile("Day length", length),
        _tile("Moon", moon["name"], f"{moon['illumination']:.0f}% lit"),
        _tile("Next full moon", f"{full:%b %d}"),
        _tile("Next new moon", f"{new:%b %d}"),
    ]), unsafe_allow_html=True)

    st.subheader("Next 7 days")
    rows = []
    for offset in range(7):
        day = today + timedelta(days=offset)
        day_rise, day_set = astro.sun_times(s.latitude, s.longitude, day)
        rows.append({"Date": f"{day:%a %b %d}", "Sunrise": _local_time(day_rise, tz),
                     "Sunset": _local_time(day_set, tz)})
    st.table(rows)
    st.caption(f"Times are in {s.timezone}. Sun times use the standard NOAA method, accurate to about a minute. "
               "Moon dates can be off by about a day.")


# ---------------------------------------------------------------- Rain calendar

def _month_html(year: int, month: int, rain: dict, p: dict, metric: bool = False) -> str:
    cell = f"padding:4px 0;border:1px solid {p['line']};text-align:center;font-size:12px;"
    head = "".join(f'<th style="{cell}color:{p["muted"]};font-weight:600">{d}</th>' for d in "SMTWTFS")
    body = []
    for week in rain_calendar.month_cells(year, month, rain):
        cells = []
        for item in week:
            if item is None:
                cells.append(f'<td style="{cell}"></td>')
                continue
            day, value = item
            shade = ""
            detail = ""
            if value is not None:
                if value > 0:
                    pct = min(100, 25 + value * 30)
                    shade = f"background:color-mix(in srgb, {p['accent']} {pct:.0f}%, transparent);"
                shown = units.convert("dailyrainin", value, metric)
                detail = f'<br><span style="font-size:11px;color:{p["muted"]}">{shown:.{1 if metric else 2}f}</span>'
            cells.append(f'<td style="{cell}{shade}">{day}{detail}</td>')
        body.append(f'<tr>{"".join(cells)}</tr>')
    return (f'<div style="margin-bottom:12px"><div class="wl-label">{calendar.month_name[month]}</div>'
            f'<table style="width:100%;border-collapse:collapse"><tr>{head}</tr>{"".join(body)}</table></div>')


def _year_heatmap(year: int, rain: dict, p: dict, dark: bool, metric: bool = False) -> go.Figure:
    jan1 = date(year, 1, 1)
    days = 366 if calendar.isleap(year) else 365
    offset = (jan1.weekday() + 1) % 7  # Sunday is row 0
    weeks = (days + offset - 1) // 7 + 1
    z = [[None] * weeks for _ in range(7)]
    text = [[""] * weeks for _ in range(7)]
    tick_cols, tick_text = [], []
    for i in range(days):
        day = jan1 + timedelta(days=i)
        col, row = divmod(i + offset, 7)
        value = rain.get(day)
        z[row][col] = value
        text[row][col] = f"{day:%b %d}: " + ("no data" if value is None else
                                             units.format_value("dailyrainin", value, metric, 1 if metric else 2))
        if day.day == 1:
            tick_cols.append(col)
            tick_text.append(calendar.month_abbr[day.month])
    peak = max((v for d, v in rain.items() if d.year == year and v is not None), default=0) or 1
    fig = charts.figure(dark, height=240)
    fig.add_trace(go.Heatmap(z=z, text=text, hoverinfo="text", zmin=0, zmax=peak, showscale=False,
                             colorscale=[[0, p["surface"]], [1, p["accent"]]], xgap=2, ygap=2))
    fig.update_xaxes(showgrid=False, tickmode="array", tickvals=tick_cols, ticktext=tick_text)
    fig.update_yaxes(showgrid=False, tickmode="array", tickvals=list(range(7)),
                     ticktext=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"], autorange="reversed")
    return fig


def rain_calendar_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    dark = theme.is_dark()
    p = theme.palette(dark, s.color_scheme)
    metric = units.is_metric(s.units)
    st.markdown(theme.title_html("Rain calendar"), unsafe_allow_html=True)
    rain = {day: data.get("rain_in") for day, data in history.all_daily(db)}
    if not any(v is not None for v in rain.values()):
        st.info("The rain calendar fills in once there are daily summaries. Each day's rain is added after that day's readings are in.")
        return

    totals, rainy = rain_calendar.year_totals(rain)
    current = datetime.now(tz).year
    years = sorted(set(totals) | {current})
    year = st.selectbox("Year", years, index=years.index(current), key="rain-year")
    this_year = {d: v for d, v in rain.items() if d.year == year and v is not None}
    wettest = max(this_year.items(), key=lambda kv: kv[1], default=None)
    st.markdown(theme.grid_html([
        _tile(f"Rain in {year}", units.format_value("dailyrainin", totals.get(year, 0.0), metric, 2)),
        _tile("Rainy days", str(rainy.get(year, 0))),
        _tile("Wettest day", "--" if wettest is None else units.format_value("dailyrainin", wettest[1], metric, 2),
              "" if wettest is None else f"{wettest[0]:%b %d}"),
    ]), unsafe_allow_html=True)

    st.subheader("Year at a glance")
    charts.show(_year_heatmap(year, rain, p, dark, metric))
    st.subheader("Month by month")
    st.caption(f"Each day shows its rain in {'millimetres' if metric else 'inches'}. Darker days got more rain.")
    for first in (1, 4, 7, 10):
        cols = st.columns(3)
        for col, month in zip(cols, range(first, first + 3)):
            with col:
                st.markdown(_month_html(year, month, rain, p, metric), unsafe_allow_html=True)

    st.subheader("Year totals")
    rain_dec = 1 if metric else 2
    st.table([{"Year": y, f"Rain ({units.unit('dailyrainin', metric)})":
               f"{units.convert('dailyrainin', totals[y], metric):.{rain_dec}f}", "Rainy days": rainy.get(y, 0)}
              for y in sorted(totals, reverse=True)])


# ---------------------------------------------------------------- Replay

def _shown(reading: dict, key: str, metric: bool, unit: str = "") -> str:
    value = reading.get(key)
    if value is None:
        return "--"
    if units.converts(key):
        return units.format_value(key, value, metric)
    return f"{value:g}{unit}"


def replay_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    metric = units.is_metric(s.units)
    st.markdown(theme.title_html("Replay"), unsafe_allow_html=True)
    today = datetime.now(tz).date()
    day = st.date_input("Day", value=today, max_value=today, key="replay-day")
    start, end = replay.day_bounds(day, tz)
    rows = storage.readings_between(db, start, end)
    if not rows:
        st.info(f"No readings for {day:%b %d, %Y}. Pick another day.")
        return
    if len(rows) > 1:
        index = st.slider("Move through the day", 0, len(rows) - 1, len(rows) - 1,
                          key=f"replay-{day.isoformat()}", label_visibility="collapsed")
    else:
        index = 0
    ts, reading = rows[index]
    when = datetime.fromtimestamp(ts, tz)
    st.caption(f"Showing {when:%a %b %d, %Y at %I:%M %p}. Drag the slider to move through the day.")
    st.markdown(theme.grid_html([
        _tile("Outdoor", _shown(reading, "tempf", metric)),
        _tile("Humidity", _shown(reading, "humidity", metric, "%")),
        _tile("Wind", _shown(reading, "windspeedmph", metric)),
        _tile("Gust", _shown(reading, "windgustmph", metric)),
        _tile("Rain today", _shown(reading, "dailyrainin", metric)),
        _tile("Pressure", _shown(reading, "baromrelin", metric)),
    ]), unsafe_allow_html=True)

    fig = charts.figure(theme.is_dark())
    fig.add_scatter(x=[datetime.fromtimestamp(t, tz) for t, _ in rows],
                    y=[units.convert("tempf", r.get("tempf"), metric) for _, r in rows],
                    mode="lines", name="Outdoor", line=dict(color=charts.CHART_COLORS[3]))
    fig.add_scatter(x=[when], y=[units.convert("tempf", reading.get("tempf"), metric)], mode="markers",
                    name="Selected time", marker=dict(size=12, color=charts.CHART_COLORS[4]))
    fig.update_yaxes(title_text=units.unit("tempf", metric))
    charts.show(fig)


# ---------------------------------------------------------------- Ecowitt export import

def ecowitt_import_page() -> None:
    db = storage.connect()
    st.markdown(theme.title_html("Ecowitt export"), unsafe_allow_html=True)
    st.write("Upload one or more history exports from ecowitt.net (.xlsx): daily, 5-minute or 4-hour. Only days Weather "
             "Lab doesn't have yet are added; days already stored are never changed. The values must be in US units "
             "(°F, mph, inches).")
    up = st.file_uploader("File", type=["xlsx"], key="ecowitt-file", accept_multiple_files=True)
    if not up:
        return
    try:
        days = ecowitt_import.days_from_files([io.BytesIO(f.getvalue()) for f in up])
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Couldn't read that file. Export the daily history from ecowitt.net as an .xlsx file.")
        return
    stored = {day for day, _ in history.all_daily(db)}
    new = sorted(day for day in days if day not in stored)
    st.write(f"The file has {len(days)} days, from {min(days):%b %d, %Y} to {max(days):%b %d, %Y}. "
             f"{len(new)} are new and {len(days) - len(new)} are already stored.")
    estimated = sum(1 for day in new if days[day].get("estimated"))
    if estimated:
        st.caption(f"{estimated} of the new days are estimates from 4-hour readings. A high or a low can fall between "
                   "readings, so those values can be a few degrees off.")
    if new and st.button(f"Import {len(new)} days", key="ecowitt-go"):
        with st.spinner("Importing..."):
            added = ecowitt_import.store_days(db, {day: days[day] for day in new})
        st.success(f"Added {added} days. They show on the Daily and Records pages.")


PAGE_ICONS = {"Live": "🌤️", "Sensors": "🛰️", "Status": "✅", "Health check": "🩺", "Alert history": "📜", "What's New": "🆕", "Settings": "🎛️", "Daily": "🗓️", "History": "📈",
              "Records": "🏆", "Coverage": "🧭", "Rankings": "🏅", "Rewind": "⏪", "Climate charts": "🌡️", "My year": "📅", "Rain calendar": "🌧️", "Replay": "🎬", "Rain events": "💧", "Ask": "🔎", "Unusual days": "🧐", "Reports": "📄",
              "Forecast": "🔮", "Heat": "🥵", "Wind": "💨", "Sun": "☀️", "Astronomy": "🔭",
              "Air": "😷", "Fire": "🚒", "Lightning": "⚡", "Tropics": "🌀", "Radar": "📡",
              "Import": "📥", "Export": "📤", "Setup": "⚙️"}
ICON_SIZE = "1.6rem"  # sidebar emoji size, same as the dashboard
SIDEBAR_CSS = f"""<style>
[data-testid="stSidebarNavLink"] [data-testid="stIconEmoji"],
[data-testid="stSidebarNavLink"] [data-testid="stSidebarNavLinkIcon"],
[data-testid="stSidebarNavLink"] span[role="img"] {{ font-size: {ICON_SIZE} !important; line-height: 1 !important; }}
[data-testid="stSidebarNavLink"] {{ gap: .6rem; }}
</style>"""


def _import_page() -> None:
    pages = {"CSV": csv_import_page, "Excel": excel_import_page,
             "Weather Underground": weather_underground_page,
             "Ecowitt export": ecowitt_import_page}
    source = st.radio("Import from", list(pages), horizontal=True)
    pages[source]()


PAGE_FUNCS = {"Live": live_page, "Sensors": sensors_page, "Status": status_page, "Health check": health_check_page, "Alert history": alerts_log_page, "What's New": whats_new_page, "Settings": settings_page, "Daily": daily_page,
              "History": history_page, "Records": records_page, "Coverage": coverage_page, "Rain events": rain_events_page, "Ask": ask_page, "Unusual days": unusual_page, "Rankings": rankings_page, "Rewind": rewind_page,
              "Climate charts": climate_page, "My year": my_year_page, "Rain calendar": rain_calendar_page,
              "Replay": replay_page, "Reports": reports_page, "Forecast": forecast_page, "Heat": heat_page,
              "Wind": wind_page, "Sun": sun_page, "Astronomy": astronomy_page, "Air": air_page,
              "Fire": fire_page, "Lightning": lightning_page, "Tropics": tropics_page, "Radar": radar_page,
              "Import": _import_page, "Export": export_page, "Setup": setup_page}


def _sections() -> dict:
    """The sidebar sections and their pages, as Streamlit page objects."""
    return {group: [st.Page(PAGE_FUNCS[name], title=name, icon=PAGE_ICONS[name], default=(name == "Live"))
                    for name in names]
            for group, names in GROUPS.items()}


def _jump_box(all_pages: dict) -> None:
    """Type part of a page name to go straight to it."""
    def go() -> None:
        choice = st.session_state.get("jump_to_page")
        st.session_state["jump_to_page"] = None
        if choice in all_pages:
            st.switch_page(all_pages[choice])
    st.sidebar.selectbox("Jump to page", sorted(all_pages), index=None, placeholder="Type to search pages",
                         key="jump_to_page", on_change=go)


def _sidebar_status() -> None:
    """One line under the menu: is the station reporting, with the exact time on hover."""
    try:
        latest = storage.latest(storage.connect())
        state, text = health.age_status(latest[0] if latest else None, time.time())
    except Exception:
        return
    icon, label = {"ok": ("🟢", "Feeds current"), "slow": ("🟠", "Readings delayed"),
                   "silent": ("🔴", "Station not reporting"), "none": ("⚪", "No readings yet")}[state]
    st.sidebar.markdown(f'<div title="{html.escape(text, quote=True)}" style="font-size:13px;padding:4px 8px">'
                        f'{icon} {label}</div>', unsafe_allow_html=True)


HEAD_SCRIPT = """<script>
(function () {
  try {
    var head = window.parent.document.head;
    var tags = [
      ['link', {rel: 'manifest', href: '/app/static/manifest.webmanifest'}],
      ['link', {rel: 'apple-touch-icon', href: '/app/static/apple-touch-icon.png'}],
      ['meta', {name: 'apple-mobile-web-app-capable', content: 'yes'}],
      ['meta', {name: 'apple-mobile-web-app-title', content: 'Weather Lab'}],
      ['meta', {name: 'theme-color', content: '#0b3d91'}]
    ];
    tags.forEach(function (t) {
      var key = t[1].rel || t[1].name;
      if (head.querySelector('[data-weatherlab="' + key + '"]')) { return; }
      var el = window.parent.document.createElement(t[0]);
      Object.keys(t[1]).forEach(function (k) { el.setAttribute(k, t[1][k]); });
      el.setAttribute('data-weatherlab', key);
      head.appendChild(el);
    });
  } catch (e) {}
})();
</script>"""


def _install_app_head() -> None:
    """Adds the app icon and home-screen settings, so Weather Lab can be added to a phone's home screen."""
    components.html(HEAD_SCRIPT, height=0)


def _select_station() -> None:
    """Sets the station for this run: the one picked in the sidebar, or the first one if that station is gone."""
    pending = st.session_state.pop("pending_station", None)
    if pending:
        st.session_state["station_pick"] = pending
    if st.session_state.get("station_pick") not in stations.ids():
        st.session_state["station_pick"] = stations.MAIN
    stations.set_current(st.session_state["station_pick"])


def _station_picker() -> None:
    """The station the pages show. Shown once a second station has been added."""
    options = stations.all_stations()
    if len(options) < 2:
        return
    names = {r["id"]: r["name"] for r in options}
    st.sidebar.selectbox("Station", list(names), format_func=lambda sid: names.get(sid, sid), key="station_pick")


def stations_page() -> None:
    """Add, rename or remove weather stations. Each one keeps its own readings, settings, alerts and backups."""
    st.markdown(theme.title_html("Stations"), unsafe_allow_html=True)
    st.caption("Each station keeps its own readings, settings, phone topic and backups. Pick a station in the sidebar "
               "to see it. A new station starts with default settings, so set its Ecowitt address and location under "
               "Setup and Settings after you add it.")
    rows = stations.all_stations()
    st.table([{"Station": r["name"], "Folder": str(stations.folder(r["id"])),
               "Showing now": "✅" if r["id"] == stations.current() else ""} for r in rows])

    st.subheader("Add a station")
    with st.form("add_station", clear_on_submit=True):
        name = st.text_input("Name", placeholder="Back garden")
        if st.form_submit_button("Add station"):
            if not name.strip():
                st.error("Give the station a name.")
            else:
                row = stations.add_station(name)
                st.session_state["pending_station"] = row["id"]
                st.rerun()

    if len(rows) > 1:
        st.subheader("Rename or remove")
        pick = st.selectbox("Station", [r["id"] for r in rows], format_func=stations.name_of, key="station_manage")
        new_name = st.text_input("New name", value=stations.name_of(pick), key=f"rename_{pick}")
        if st.button("Save name"):
            stations.rename_station(pick, new_name)
            st.rerun()
        if pick != stations.MAIN:
            st.caption(f"Removing a station stops its collector. Its folder ({stations.folder(pick)}) is kept, so "
                       "adding a station with the same name brings its readings back.")
            if st.button("Remove station"):
                stations.remove_station(pick)
                if stations.current() == pick:
                    st.session_state["pending_station"] = stations.MAIN
                st.rerun()


PAGE_ICONS["Stations"] = "📍"
PAGE_FUNCS["Stations"] = stations_page


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    _select_station()
    cfg = load_settings()
    st.markdown(theme.css(theme.is_dark(), cfg.color_scheme, cfg.compact, cfg.large_text), unsafe_allow_html=True)
    st.markdown(SIDEBAR_CSS, unsafe_allow_html=True)
    autofit.install()
    _install_app_head()
    start_poller()
    with stations.using(stations.MAIN):
        allowed = access_gate()
    if not allowed:
        return
    sections = _sections()
    _station_picker()
    nav = st.navigation(sections, position="sidebar")
    _jump_box({page.title: page for group in sections.values() for page in group})
    _sidebar_status()
    nav.run()
    st.caption(f"{APP_NAME} version {APP_VERSION}")


main()
