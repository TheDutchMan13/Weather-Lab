"""First-run setup (0.37.60): find the station, say where it is, done. Shown on Home until the station address is set,
and again from Settings, Station, Run setup again. Each step saves as it goes, so leaving halfway keeps what was set."""

from dataclasses import replace
from zoneinfo import available_timezones

import streamlit as st

from weatherlab import discover, geocode, parse, plain_errors, units
from weatherlab.settings import load_settings, save_settings, valid_ip

STEPS = ["Station", "Location", "Done"]


def start() -> None:
    """Open the wizard at step 1 (from Settings)."""
    st.session_state["wiz_active"] = True
    st.session_state["wiz_step"] = 0


def active() -> bool:
    return bool(st.session_state.get("wiz_active")) or not load_settings().station_ip.strip()


def _go(step: int) -> None:
    st.session_state["wiz_active"] = True
    st.session_state["wiz_step"] = step
    st.rerun()


def _progress(step: int) -> None:
    cols = st.columns(len(STEPS))
    for i, (col, name) in enumerate(zip(cols, STEPS)):
        mark = "✓" if i < step else str(i + 1)
        tone = "#16a34a" if i < step else ("#3b82f6" if i == step else "#9ca3af")
        col.markdown(f"<div style='border-bottom:3px solid {tone};padding:4px 0;font-size:14px'>"
                     f"<b>{mark}</b> {name}</div>", unsafe_allow_html=True)


def show() -> None:
    step = int(st.session_state.get("wiz_step", 0))
    if step == 0 and load_settings().station_ip.strip() and not st.session_state.get("wiz_active"):
        step = 1
    with st.container(border=True):
        st.markdown("### Welcome to Weather Lab")
        st.caption("Two short steps and your readings start arriving.")
        _progress(step)
        [_station, _location, _done][min(step, 2)]()


def _station() -> None:
    s = load_settings()
    st.markdown("**1. Find your station**")
    st.caption("Weather Lab reads an Ecowitt gateway such as the GW2000 on your home network.")
    if st.button("Find it on my network", key="wiz_find", type="primary"):
        with st.spinner("Looking on your network. This takes a few seconds."):
            st.session_state["wiz_found"] = discover.find()
        if not st.session_state["wiz_found"]:
            st.warning("No station answered on this network. It may be asleep, on another network range, or on Wi-Fi "
                       "this PC isn't on. Type its address below: it's on the gateway's screen in the Ecowitt app, or in "
                       "your router's list of devices.")
    for ip in st.session_state.get("wiz_found", []):
        if st.button(f"Use {ip}", key=f"wiz_use_{ip}"):
            st.session_state["wiz_ip"] = ip
            st.rerun()
    ip = st.text_input("Station address", value=st.session_state.get("wiz_ip", s.station_ip),
                       placeholder="for example 192.168.1.224", key="wiz_ip_box").strip()
    if st.button("Test and continue", key="wiz_test"):
        if not valid_ip(ip):
            st.error("That isn't an address like 192.168.1.224. Check it and try again.")
            return
        try:
            reading = parse.clean(parse.parse_livedata(parse.fetch(ip)))
        except (OSError, ValueError) as exc:
            st.session_state["wiz_failed_ip"] = ip
            st.session_state["wiz_failed_text"] = plain_errors.station(ip, exc)
        else:
            save_settings(replace(load_settings(), station_ip=ip))
            shown = units.format_value("tempf", reading.get("tempf"), units.is_metric(s.units), 1)
            st.session_state["wiz_note"] = f"Connected to {ip}. Outdoor temperature reads {shown}."
            _go(1)
    if st.session_state.get("wiz_failed_ip") == ip and ip:
        st.error(st.session_state.get("wiz_failed_text", ""))
        if st.button("Save this address anyway", key="wiz_anyway",
                     help="Weather Lab keeps trying. Readings start when the station answers."):
            save_settings(replace(load_settings(), station_ip=ip))
            st.session_state["wiz_note"] = f"Saved {ip}. Readings start as soon as the station answers."
            _go(1)


def _location() -> None:
    s = load_settings()
    if st.session_state.get("wiz_note"):
        st.success(st.session_state["wiz_note"])
    st.markdown("**2. Where is it?**")
    st.caption("Used for sunrise and sunset, forecasts, weather warnings, air quality and daily summaries.")
    place = st.text_input("Town, city or ZIP code", key="wiz_place", placeholder="for example Springfield, IL")
    if st.button("Search", key="wiz_search") and place.strip():
        try:
            st.session_state["wiz_places"] = geocode.search(place)
            if not st.session_state["wiz_places"]:
                st.warning("No place found by that name. Try the nearest town, or enter the numbers yourself below.")
        except geocode.GeocodeError as exc:
            st.session_state["wiz_places"] = []
            st.error(f"{exc} Enter the numbers yourself below, or try again later.")
    places = st.session_state.get("wiz_places") or []
    picked = None
    if places:
        labels = [f"{p['label']} · {p['lat']:.2f}, {p['lon']:.2f} · {p['timezone']}" for p in places]
        i = st.radio("Pick your place", range(len(places)), format_func=lambda k: labels[k], key="wiz_pick")
        picked = places[i]
    st.caption("Only the place name is sent, to Open-Meteo's free place search.")
    zones = sorted(available_timezones())
    with st.expander("Enter the numbers yourself", expanded=not places and s.latitude is not None):
        lat = st.number_input("Latitude", -90.0, 90.0, float(s.latitude or 0.0), format="%.5f", key="wiz_lat")
        lon = st.number_input("Longitude", -180.0, 180.0, float(s.longitude or 0.0), format="%.5f", key="wiz_lon")
        tz = st.selectbox("Time zone", zones, index=zones.index(s.timezone) if s.timezone in zones else zones.index("UTC"),
                          key="wiz_tz")
        manual = st.checkbox("Use these numbers", value=not places and s.latitude is not None, key="wiz_manual")
    back, go = st.columns([1, 1])
    if back.button("Back", key="wiz_back"):
        _go(0)
    if go.button("Save and continue", key="wiz_save", type="primary"):
        if picked and not manual:
            new = replace(s, latitude=picked["lat"], longitude=picked["lon"],
                          timezone=picked["timezone"] if picked["timezone"] in zones else s.timezone,
                          elevation_m=picked["elevation"] if picked["elevation"] is not None else s.elevation_m)
        elif manual and not (lat == 0.0 and lon == 0.0):
            new = replace(s, latitude=lat, longitude=lon, timezone=tz)
        else:
            st.error("Search for your place and pick it, or tick Use these numbers after entering them.")
            return
        save_settings(new)
        _go(2)


def _done() -> None:
    s = load_settings()
    st.markdown("**3. You're set**")
    where = f"{s.latitude:.2f}, {s.longitude:.2f} ({s.timezone})" if s.latitude is not None else "not set yet"
    st.markdown(f"Station **{s.station_ip or 'not set'}** · location **{where}**")
    st.caption("Readings arrive within a minute. Optional next, all in Settings: phone alerts, the Android app, "
               "and uploads to Weather Underground or CWOP. Run this again from Settings, Station.")
    if st.button("Go to Home", key="wiz_finish", type="primary"):
        for key in ("wiz_active", "wiz_step", "wiz_found", "wiz_ip", "wiz_note", "wiz_places", "wiz_failed_ip", "wiz_failed_text"):
            st.session_state.pop(key, None)
        st.rerun()
