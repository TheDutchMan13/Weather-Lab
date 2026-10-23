"""Pages under System: status, health check, What's New, setup, settings and stations."""

import streamlit as st
import time
from dataclasses import replace
from weatherlab import alert_rules, auth, autostart, backup, discover, errlog, gateway_sensors, health, health_check, mqtt_publish, network, parse, push, pwsweather, secrets, station_status, stations, storage, theme, units, updates, weathercloud, whats_new, wunderground
from weatherlab.config import APP_VERSION, CARD_LABELS
from weatherlab.settings import Settings, load_settings, save_settings, settings_path, valid_ip
from zoneinfo import available_timezones
from weatherlab.screens.common import _clock, _tile, clear_key_button, confirm_button, empty_card, start_poller


# ---------------------------------------------------------------- Setup
def _password_section() -> None:
    st.markdown(theme.section_html("Password for other devices"), unsafe_allow_html=True)
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
    if auth.password_set() and confirm_button("Remove password", "rm_password",
                                              "Weather Lab will open without asking for a password.",
                                              "Yes, remove password"):
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
    st.markdown(theme.section_html("Appearance"), unsafe_allow_html=True)
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
    st.markdown(theme.section_html("Startup"), unsafe_allow_html=True)
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
    st.markdown(theme.section_html("Phone notifications with the ntfy app"), unsafe_allow_html=True)
    st.caption("Install the free ntfy app on your phone, then add the topic below to it. Alerts reach the phone "
               "while this PC is on and online. Anyone who knows the topic can read the alerts, so keep it private.")
    server = st.text_input("ntfy server (leave blank for ntfy.sh)", value=s.ntfy_server, key="ph_server",
                           help="Only change this if you run your own ntfy server.")
    if server.strip() != s.ntfy_server.strip():
        save_settings(replace(s, ntfy_server=server.strip()))
    topic = secrets.get_key(push.TOPIC_KEY)
    if topic:
        st.code(topic, language=None)
    left, middle = st.columns(2)
    if left.button("Make a new topic", help="Replaces the current topic. Add the new one to the ntfy app."):
        secrets.set_key(push.TOPIC_KEY, push.new_topic())
        st.rerun()
    if middle.button("Send a test", disabled=not topic):
        if push.send(server.strip(), topic, "Weather Lab", "Test alert from Weather Lab."):
            st.success("Sent. Check the ntfy app on your phone.")
        else:
            st.warning("Couldn't send it. Check the internet connection and the server address.")
    if confirm_button("Remove topic", "rm_topic", "Your phone stops getting alerts until you add a new topic.",
                      "Yes, remove topic", disabled=not topic):
        secrets.set_key(push.TOPIC_KEY, "")
        st.rerun()


def _updates_section(s: Settings) -> None:
    """Looks for a newer version at the address the user gives, and can download and run its installer."""
    st.markdown(theme.section_html("Updates"), unsafe_allow_html=True)
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
    st.markdown(theme.page_head("Settings", "Appearance, alerts, phone alerts, updates and startup."), unsafe_allow_html=True)
    look_tab, alerts_tab, phone_tab, updates_tab, start_tab = st.tabs(
        ["Appearance", "Alerts", "Phone alerts", "Updates", "Startup"])
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
    with start_tab:
        _startup_section()


def _service_status(enabled: bool, error: str, last: float | None, verb: str = "sent") -> str:
    """The short status on an upload's card, such as On, last sent 16:12:04."""
    if not enabled:
        return "Off"
    if error:
        return "On, needs attention"
    if last:
        return f"On, last {verb} {_clock(last)}"
    return "On, waiting for the first send"


def _upload_note(error: str, last: float | None, action: str) -> None:
    """Under an upload's settings: the problem it last reported, or when it last sent readings."""
    if error:
        st.warning(error)
    elif last:
        st.caption(f"Last {action} {_clock(last)}")


def setup_page() -> None:
    st.markdown(theme.page_head("Setup", "Where the station is, and the optional services that use it."), unsafe_allow_html=True)
    s = load_settings()
    _station_tools(s)
    (station_tab, air_tab, uploads_tab, network_tab) = st.tabs(["Station", "Air", "Uploads", "Access"])

    with station_tab:
        st.markdown(theme.section_html("Where the station is"), unsafe_allow_html=True)
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
        st.markdown(theme.section_html("Forecast requests"), unsafe_allow_html=True)
        contact = st.text_input("Contact email (optional)", value=s.nws_contact,
                                help="Sent to the National Weather Service with forecast requests.")
        if s.latitude is None or s.longitude is None:
            st.caption("Set your latitude and longitude so sun hours and forecasts can be calculated.")

    with air_tab:
        st.markdown(theme.section_html("Air quality (optional)"), unsafe_allow_html=True)
        has_key = bool(secrets.get_key("airnow"))
        airnow_key = st.text_input(
            "AirNow API key", type="password",
            placeholder="Saved in Windows Credential Manager" if has_key else "Paste your free AirNow key",
            help="Get a free key from the AirNow API website. It is stored in Windows Credential Manager, not in a file.")
        remove_key = clear_key_button("airnow", "AirNow key", has_key)
        st.markdown(theme.section_html("Lightning"), unsafe_allow_html=True)
        km = st.checkbox("The station's lightning distance is in kilometres", value=s.lightning_value_is_km,
                         help="Some GW2000 firmware labels kilometres as miles. Turn this on if the distances look too small.")

    with uploads_tab:
        st.caption("Each service is off by default. Keys are stored in Windows Credential Manager.")
        poll = start_poller().status

        with st.expander(f"CWOP · {_service_status(s.cwop_enabled, poll.cwop_error, poll.cwop_last)}"):
            cwop_on = st.checkbox(
                "Send my readings to CWOP",
                value=s.cwop_enabled,
                help="The Citizen Weather Observer Program shows your station on public weather maps such as aprs.fi. "
                     "Your station's location becomes public. Off by default.",
            )
            cwop_call = st.text_input("CWOP callsign", value=s.cwop_callsign,
                                      placeholder="for example CW1234 or your amateur callsign")
            if cwop_on:
                _upload_note(poll.cwop_error, poll.cwop_last, "sent to CWOP")

        with st.expander(f"Weather Underground · {_service_status(s.wu_enabled, poll.wu_error, poll.wu_last)}"):
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
            remove_wu_key = clear_key_button("wu", "Weather Underground key", wu_key_saved)
            if wu_on:
                _upload_note(poll.wu_error, poll.wu_last, "sent to Weather Underground")

        with st.expander(f"PWSweather · {_service_status(s.pws_enabled, poll.pws_error, poll.pws_last)}"):
            pws_on = st.checkbox("Send my readings to PWSweather", value=s.pws_enabled,
                                 help="PWSweather shows your station on its public map. Get the station ID and key from your "
                                      "PWSweather account. Off by default.")
            pws_id = st.text_input("PWSweather station ID", value=s.pws_station_id)
            pws_key_saved = bool(secrets.get_key(pwsweather.KEY_NAME))
            pws_key = st.text_input("PWSweather station key", type="password",
                                    placeholder="Saved in Windows Credential Manager" if pws_key_saved else "Paste your station key")
            remove_pws_key = clear_key_button("pws", "PWSweather key", pws_key_saved)
            if pws_on:
                _upload_note(poll.pws_error, poll.pws_last, "sent to PWSweather")

        with st.expander(f"Weathercloud · {_service_status(s.weathercloud_enabled, poll.wc_error, poll.wc_last)}"):
            wc_on = st.checkbox("Send my readings to Weathercloud", value=s.weathercloud_enabled,
                                help="Weathercloud shows your station on its public map. Get the device ID and key from your "
                                     "Weathercloud account. Off by default.")
            wc_id = st.text_input("Weathercloud device ID", value=s.weathercloud_id)
            wc_key_saved = bool(secrets.get_key(weathercloud.KEY_NAME))
            wc_key = st.text_input("Weathercloud device key", type="password",
                                   placeholder="Saved in Windows Credential Manager" if wc_key_saved else "Paste your device key")
            remove_wc_key = clear_key_button("wc", "Weathercloud key", wc_key_saved)
            if wc_on:
                _upload_note(poll.wc_error, poll.wc_last, "sent to Weathercloud")

        with st.expander(f"Home Assistant over MQTT · {_service_status(s.mqtt_enabled, poll.mqtt_error, poll.mqtt_last, 'published')}"):
            mqtt_on = st.checkbox("Send my readings to an MQTT broker", value=s.mqtt_enabled,
                                  help="Use this with Home Assistant's Mosquitto add-on or another broker on your network. "
                                       "Off by default.")
            mqtt_host = st.text_input("Broker address", value=s.mqtt_host, placeholder="for example 192.168.1.20")
            mqtt_port = st.number_input("Broker port", min_value=1, max_value=65535, value=int(s.mqtt_port), step=1)
            mqtt_user = st.text_input("Broker username", value=s.mqtt_user)
            mqtt_pass_saved = bool(secrets.get_key(mqtt_publish.KEY_NAME))
            mqtt_pass = st.text_input("Broker password", type="password",
                                      placeholder="Saved in Windows Credential Manager" if mqtt_pass_saved
                                      else "Leave blank if the broker has no password")
            remove_mqtt_pass = clear_key_button("mqtt", "MQTT password", mqtt_pass_saved)
            mqtt_prefix = st.text_input("Topic prefix", value=s.mqtt_prefix,
                                        help="Each reading is sent to a topic under this prefix, for example weatherlab/home/temperature.")
            mqtt_discovery = st.checkbox("Add the sensors to Home Assistant automatically", value=s.mqtt_discovery,
                                         help="Sends Home Assistant discovery messages once an hour. Turn this off if you add the sensors yourself.")
            if mqtt_on:
                _upload_note(poll.mqtt_error, poll.mqtt_last, "published to MQTT")

    with network_tab:
        st.markdown(theme.section_html("Phones and devices"), unsafe_allow_html=True)
        allow_network = st.checkbox(
            "Let phones and devices on my network open Weather Lab", value=s.allow_network,
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
                st.caption("Away from home: install Tailscale on this PC and your phone. The address appears here "
                           "once Tailscale is running.")
            _password_section()

    typed_keys = [airnow_key, wu_key, pws_key, wc_key, mqtt_pass]
    removed_keys = [remove_key, remove_wu_key, remove_pws_key, remove_wc_key, remove_mqtt_pass]
    changes = [
        s.station_ip != ip.strip(), s.timezone != tz, (s.latitude or 0.0) != lat, (s.longitude or 0.0) != lon,
        s.elevation_m != elev, s.nws_contact != contact.strip(), s.lightning_value_is_km != km,
        s.cwop_enabled != cwop_on, s.cwop_callsign != cwop_call.strip().upper(),
        s.wu_enabled != wu_on, s.wu_station_id != wu_id.strip(),
        s.pws_enabled != pws_on, s.pws_station_id != pws_id.strip(),
        s.weathercloud_enabled != wc_on, s.weathercloud_id != wc_id.strip(),
        s.mqtt_enabled != mqtt_on, s.mqtt_host != mqtt_host.strip(), s.mqtt_port != int(mqtt_port),
        s.mqtt_user != mqtt_user.strip(), s.mqtt_prefix != mqtt_prefix.strip().strip("/"),
        s.mqtt_discovery != mqtt_discovery, s.allow_network != allow_network,
    ]
    waiting = sum(changes) + sum(1 for k in typed_keys if k.strip()) + sum(1 for r in removed_keys if r)
    with st.container(key="setup_save"):
        if waiting:
            st.caption(f"{waiting} unsaved change{'' if waiting == 1 else 's'}")
        save_clicked = st.button("Save", type="primary")
    with st.expander("About this page"):
        st.write("Changes wait in the save bar until you press Save. Keys and passwords are stored in Windows "
                 f"Credential Manager, not in files. Settings are saved to {settings_path()}.")
    if save_clicked:
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
        if mqtt_on and not mqtt_host.strip():
            st.error("Enter the MQTT broker address to turn MQTT on.")
            return
        if mqtt_on:
            try:
                mqtt_publish.check_prefix(mqtt_prefix)
            except mqtt_publish.MqttError as exc:
                st.error(str(exc))
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
            if remove_mqtt_pass:
                secrets.set_key(mqtt_publish.KEY_NAME, "")
            elif mqtt_pass.strip():
                secrets.set_key(mqtt_publish.KEY_NAME, mqtt_pass.strip())
        except Exception as exc:
            st.error(f"Couldn't save the keys: {exc}")
            return
        save_settings(replace(s, station_ip=ip, latitude=lat, longitude=lon, elevation_m=elev,
                               timezone=tz, nws_contact=contact.strip(),
                               lightning_value_is_km=km, cwop_enabled=cwop_on,
                               cwop_callsign=cwop_call.strip().upper(), wu_enabled=wu_on,
                               wu_station_id=wu_id.strip(), pws_enabled=pws_on,
                               pws_station_id=pws_id.strip(), weathercloud_enabled=wc_on,
                               weathercloud_id=wc_id.strip(), mqtt_enabled=mqtt_on,
                               mqtt_host=mqtt_host.strip(), mqtt_port=int(mqtt_port),
                               mqtt_user=mqtt_user.strip(), mqtt_prefix=mqtt_prefix.strip().strip("/"),
                               mqtt_discovery=mqtt_discovery, allow_network=allow_network))
        st.success(f"Saved to {settings_path()}")


def _notifications_section(s: Settings) -> None:
    """Sensor warnings and the morning summary, plus a button to check that Windows notifications show."""
    st.markdown(theme.section_html("Notifications"), unsafe_allow_html=True)
    sensors_on = st.checkbox("Warn about low sensor batteries and weak signal", value=s.sensor_alerts, key="notify_sensors")
    digest_on = st.checkbox("Send a short summary each morning about yesterday", value=s.digest_enabled, key="notify_digest")
    hour = int(st.number_input("Morning summary time (hour, 0 to 23)", min_value=0, max_value=23,
                               value=int(s.digest_hour), step=1, key="notify_hour"))
    weekly_on = st.checkbox("Also send a summary of the last 7 days on Mondays", value=s.weekly_digest, key="notify_weekly")
    offline_on = st.checkbox("Warn when the station stops sending readings", value=s.offline_alerts, key="notify_offline")
    frost_on = st.checkbox("Warn about freezing nights in the forecast", value=s.frost_alerts, key="notify_frost")
    metric = units.is_metric(s.units)
    frost_shown = float(st.number_input(
        f"Freeze warning when the forecast low is at or below ({'°C' if metric else '°F'})",
        min_value=round(units.convert("tempf", 20.0, metric), 1), max_value=round(units.convert("tempf", 45.0, metric), 1),
        value=round(units.convert("tempf", float(s.frost_threshold_f), metric), 1), step=1.0,
        key=f"notify_frost_{'c' if metric else 'f'}"))
    frost_f = round(units.to_us("tempf", frost_shown, metric), 1)
    if (sensors_on, digest_on, hour, offline_on, frost_on, frost_f, weekly_on) != (
            s.sensor_alerts, s.digest_enabled, s.digest_hour, s.offline_alerts, s.frost_alerts,
            round(s.frost_threshold_f, 1), s.weekly_digest):
        save_settings(replace(s, sensor_alerts=sensors_on, digest_enabled=digest_on, digest_hour=hour,
                              offline_alerts=offline_on, frost_alerts=frost_on, frost_threshold_f=frost_f,
                              weekly_digest=weekly_on))
    if st.button("Send a test notification"):
        if alert_rules.notify("Weather Lab", "This is a test notification from Weather Lab."):
            st.success("Sent. If nothing appears, check that Windows notifications are on for this app.")
        else:
            st.warning("Couldn't show a Windows notification here. Alerts are still listed in the app.")


def _quiet_section(s: Settings) -> None:
    """Quiet hours, the stuck-sensor check and the lightning notice."""
    st.markdown(theme.section_html("Quiet hours and more checks"), unsafe_allow_html=True)
    quiet_on = st.checkbox("Quiet hours: hold back non-urgent notifications", value=s.quiet_enabled, key="quiet_on",
                           help="Sensor warnings, stuck-sensor warnings and the morning summary wait until quiet hours end. "
                                "Station offline, freeze and lightning notices still sound.")
    start = int(st.number_input("Quiet from (hour, 0 to 23)", min_value=0, max_value=23, value=int(s.quiet_start),
                                step=1, key="quiet_start"))
    end = int(st.number_input("Quiet until (hour, 0 to 23)", min_value=0, max_value=23, value=int(s.quiet_end),
                              step=1, key="quiet_end"))
    stuck_on = st.checkbox("Warn when outdoor temperature or humidity stops changing", value=s.stuck_alerts, key="stuck_on")
    health_on = st.checkbox("Warn me when disk space runs out or a backup fails", value=s.health_alerts, key="health_on")
    light_on = st.checkbox("Notify me when lightning is close", value=s.lightning_alerts, key="light_on")
    miles = float(st.number_input("Lightning notice within (miles)", min_value=1.0, max_value=25.0,
                                  value=float(s.lightning_alert_miles), step=1.0, key="light_miles"))
    if (quiet_on, start, end, stuck_on, health_on, light_on, miles) != (
            s.quiet_enabled, s.quiet_start, s.quiet_end, s.stuck_alerts, s.health_alerts, s.lightning_alerts,
            s.lightning_alert_miles):
        save_settings(replace(s, quiet_enabled=quiet_on, quiet_start=start, quiet_end=end, stuck_alerts=stuck_on,
                              health_alerts=health_on,
                              lightning_alerts=light_on, lightning_alert_miles=miles))


def _alert_extras_section(s: Settings) -> None:
    """UV, air quality and fire danger notices, rain start and stop, and the optional version check address."""
    st.markdown(theme.section_html("Other warnings"), unsafe_allow_html=True)
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
    nws_on = st.checkbox("National Weather Service warnings and advisories (US only)", value=s.nws_alerts, key="ex_nws",
                         help="Sends each new warning or advisory for your location once, to this PC and your phone.")
    current = (uv_on, uv_level, aqi_on, aqi_level, fire_on, fire_level, rain_on, nws_on)
    saved = (s.uv_alerts, s.uv_alert_level, s.aqi_alerts, s.aqi_alert_level, s.fire_alerts, s.fire_alert_fwi,
             s.rain_notices, s.nws_alerts)
    if current != saved:
        save_settings(replace(s, uv_alerts=uv_on, uv_alert_level=uv_level, aqi_alerts=aqi_on, aqi_alert_level=aqi_level,
                              fire_alerts=fire_on, fire_alert_fwi=fire_level, rain_notices=rain_on, nws_alerts=nws_on))


def _alert_rules_section() -> None:
    s = load_settings()
    st.markdown(theme.section_html("Alert rules"), unsafe_allow_html=True)
    st.caption("Weather Lab sends a notification when a rule's conditions hold. A rule repeats at most once an hour, "
               "unless it escalates: then it becomes more serious the longer it lasts.")
    metric = units.is_metric(s.units)
    rules = list(s.alert_rules)
    if not rules:
        st.caption("No rules yet.")
    for i, rule in enumerate(rules):
        st.write(alert_rules.describe(rule, metric))
        if confirm_button("Remove this rule", f"rule-remove-{i}", "This rule stops sending alerts.", "Yes, remove rule"):
            save_settings(replace(s, alert_rules=rules[:i] + rules[i + 1:]))
            st.rerun()
    labels = {label: key for key, (label, _) in alert_rules.METRICS.items()}
    names = list(labels)
    unit_text = "°C, km/h or mm" if metric else "°F, mph or inches"
    default_value = round(units.convert("tempf", 110.0, metric), 1)
    with st.form("new-rule"):
        st.markdown("**What to watch**")
        name = st.text_input("Name", placeholder="Extreme heat")
        watch = st.selectbox("Watch", names, help="Pressure falling and temperature falling are changes per hour.")
        op = st.selectbox("When it is", list(alert_rules.OPS), format_func=alert_rules.OPS.get)
        value = st.number_input(f"Value ({unit_text})", value=default_value, step=1.0,
                                key=f"rule_value_{'c' if metric else 'f'}")
        with st.expander("Add a second condition"):
            second = st.checkbox("Use a second condition")
            watch2 = st.selectbox("Second condition: watch", names, key="rule_watch2")
            op2 = st.selectbox("Second condition: when it is", list(alert_rules.OPS), format_func=alert_rules.OPS.get,
                               key="rule_op2")
            value2 = st.number_input("Second condition: value", value=default_value, step=1.0,
                                     key=f"rule_value2_{'c' if metric else 'f'}")
            combine = st.selectbox("With a second condition", ["Both must be true", "Either can be true"])
        with st.expander("When it applies"):
            window = st.selectbox("Only apply", list(alert_rules.WINDOWS), format_func=alert_rules.WINDOWS.get)
            months = st.multiselect("Months", list(range(1, 13)), format_func=lambda m: alert_rules.MONTH_NAMES[m - 1],
                                    help="Used only when Only apply is set to chosen months.")
            escalate = st.checkbox("Escalate while it lasts",
                                   help="A Warning after an hour, and Severe after three hours, repeated every three hours.")
        if st.form_submit_button("Add rule"):
            conditions = [{"metric": labels[watch], "op": op,
                           "value": alert_rules.to_us_value(labels[watch], float(value), metric)}]
            if second:
                conditions.append({"metric": labels[watch2], "op": op2,
                                   "value": alert_rules.to_us_value(labels[watch2], float(value2), metric)})
            rule = {"name": name.strip() or watch, "conditions": conditions,
                    "combine": "OR" if combine == "Either can be true" else "AND",
                    "window": window, "months": sorted(months), "escalate": escalate}
            problem = alert_rules.valid_rule(rule)
            if problem:
                st.error(problem)
            else:
                save_settings(replace(s, alert_rules=rules + [rule]))
                st.rerun()
    recent = start_poller().status.recent_alerts[:5]
    if recent:
        st.markdown(theme.section_html("Recent alerts"), unsafe_allow_html=True)
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
    st.markdown(theme.page_head("What's New", "What changed in each version, newest first."), unsafe_allow_html=True)
    for i, entry in enumerate(whats_new.ENTRIES):
        note = f"{entry['date']} · latest" if i == 0 else entry["date"]
        with st.container(border=True):
            st.markdown(theme.section_html(f"Version {entry['version']}", note), unsafe_allow_html=True)
            st.markdown("\n".join(f"- {item}" for item in entry["items"]))


def status_page() -> None:
    s = load_settings()
    db = storage.connect()
    poller = start_poller()
    now = time.time()
    st.markdown(theme.page_head("Status", "Whether the station is reporting, and the battery and signal of each sensor."), unsafe_allow_html=True)

    latest = storage.latest(db)
    last_ts = latest[0] if latest else None
    reporting, age_text = health.age_status(last_ts, now)
    feed_errors = [e for e in (poller.status.last_error, poller.status.aqi_error, poller.status.cwop_error, poller.status.wu_error, poller.status.pws_error, poller.status.wc_error, poller.status.mqtt_error, poller.status.sensor_error) if e]
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
        empty_card("Set the station IP on the Setup page to see sensor battery and signal.")
    elif raw is None:
        st.caption("Battery and signal aren't available right now. The station may be off or offline.")
    elif sensors:
        st.markdown(theme.section_html("Sensors"), unsafe_allow_html=True)
        theme.table([{"Sensor": x["name"], "Battery": x["battery_text"] or "--",
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
        "nws_on": s.nws_alerts,
        "nws_error": poller.status.nws_error,
        "reports_on": s.auto_reports,
        "report_error": poller.status.report_error,
        "archive_days": s.archive_after_days,
        "archive_error": poller.status.archive_error,
        "recent_errors": errlog.recent(now - 86400),
    }
    checks = health_check.evaluate(facts, now)
    st.markdown(theme.page_head("Health check", "Whether everything Weather Lab needs to run is working."), unsafe_allow_html=True)
    counts = {state: sum(1 for c in checks if c["state"] == state) for state in ("ok", "warn", "fail", "info")}
    for col, (label, state) in zip(st.columns(4), [("OK", "ok"), ("Check", "warn"), ("Problem", "fail"), ("Info", "info")]):
        col.metric(label, counts[state])
    if any(c["state"] in ("warn", "fail") for c in checks):
        st.warning(health_check.summary(checks))
    else:
        st.success(health_check.summary(checks))
    words = {"ok": "OK", "warn": "Check", "fail": "Problem", "info": "Info"}
    for title, rows in health_check.grouped(checks):
        st.markdown(theme.section_html(title), unsafe_allow_html=True)
        theme.table([{"Check": c["name"], "Status": theme.state_html(c["state"], words[c["state"]]),
                      "Details": c["detail"]} for c in rows], html_cols=("Status",))
    st.caption("Checked each time this page opens.")
    _backup_test(db_file)


def _backup_test(db_file) -> None:
    """Open the newest backup and check it reads back. A backup nobody has opened is only a guess that it works."""
    items = backup.backups(backup.folder_for(db_file))
    st.markdown(theme.section_html("Test the newest backup"), unsafe_allow_html=True)
    if not items:
        st.caption("There are no backups yet. The first one is made on the next hourly check.")
        return
    st.caption(f"Newest: {items[-1].name}. The test opens a copy read-only and changes nothing.")
    if st.button("Test the newest backup", key="backup_test"):
        ok, text = backup.verify(items[-1])
        (st.success if ok else st.error)(text)


def stations_page() -> None:
    """Add, rename or remove weather stations. Each one keeps its own readings, settings, alerts and backups."""
    st.markdown(theme.page_head("Stations", "Add, rename or remove stations. Each keeps its own data and alerts."), unsafe_allow_html=True)
    st.caption("Each station keeps its own readings, settings, phone topic and backups. Pick a station in the sidebar "
               "to see it. A new station starts with default settings, so set its Ecowitt address and location under "
               "Setup and Settings after you add it.")
    rows = stations.all_stations()
    theme.table([{"Station": r["name"], "Folder": str(stations.folder(r["id"])),
                  "Showing now": "Yes" if r["id"] == stations.current() else ""} for r in rows])

    st.markdown(theme.section_html("Add a station"), unsafe_allow_html=True)
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
        st.markdown(theme.section_html("Rename or remove"), unsafe_allow_html=True)
        pick = st.selectbox("Station", [r["id"] for r in rows], format_func=stations.name_of, key="station_manage")
        new_name = st.text_input("New name", value=stations.name_of(pick), key=f"rename_{pick}")
        if st.button("Save name"):
            stations.rename_station(pick, new_name)
            st.rerun()
        if pick != stations.MAIN:
            st.caption(f"Removing a station stops its collector. Its folder ({stations.folder(pick)}) is kept, so "
                       "adding a station with the same name brings its readings back.")
            if confirm_button("Remove station", "rm_station",
                              "The station stops collecting readings. Its folder is kept.", "Yes, remove station"):
                stations.remove_station(pick)
                if stations.current() == pick:
                    st.session_state["pending_station"] = stations.MAIN
                st.rerun()
