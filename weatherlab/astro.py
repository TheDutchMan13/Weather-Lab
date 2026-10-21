"""Sun and moon from your location: sunrise, sunset and moon phase. Works offline.

Sun times use the NOAA sunrise equation (about a minute accurate). Moon phases use the mean synodic month,
so the dates can be off by about a day.
"""

import math
from datetime import datetime, timedelta, timezone

SYNODIC = 29.530588853  # days in one lunar cycle
FULL_AGE = 14.765294  # age in days at full moon
NEW_MOON_REF = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)
J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


def _jd(dt):
    return 2451545.0 + (dt - J2000).total_seconds() / 86400


def _from_jd(jd):
    return J2000 + timedelta(days=jd - 2451545.0)


def sun_times(lat, lon, day):
    """(sunrise, sunset) as UTC datetimes for a date. (None, None) when the sun doesn't rise or set that day."""
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
    n = round(_jd(noon) - 2451545.0)
    jstar = n - lon / 360
    m = math.radians((357.5291 + 0.98560028 * jstar) % 360)
    c = 1.9148 * math.sin(m) + 0.02 * math.sin(2 * m) + 0.0003 * math.sin(3 * m)
    lam = math.radians((math.degrees(m) + c + 180 + 102.9372) % 360)
    transit = 2451545.0 + jstar + 0.0053 * math.sin(m) - 0.0069 * math.sin(2 * lam)
    decl = math.asin(math.sin(lam) * math.sin(math.radians(23.4397)))
    phi = math.radians(lat)
    cos_w = (math.sin(math.radians(-0.833)) - math.sin(phi) * math.sin(decl)) / (math.cos(phi) * math.cos(decl))
    if cos_w > 1 or cos_w < -1:
        return None, None
    w = math.degrees(math.acos(cos_w))
    return _from_jd(transit - w / 360), _from_jd(transit + w / 360)


def moon_age(when):
    """Days since the reference new moon, within one cycle."""
    return ((when - NEW_MOON_REF).total_seconds() / 86400) % SYNODIC


def _name(age):
    if age < 1.85 or age >= SYNODIC - 1.85:
        return "New moon"
    if age < 7.38:
        return "Waxing crescent"
    if age < 9.23:
        return "First quarter"
    if age < 13.8:
        return "Waxing gibbous"
    if age < 16.6:
        return "Full moon"
    if age < 22.15:
        return "Waning gibbous"
    if age < 24.0:
        return "Last quarter"
    return "Waning crescent"


def moon_phase(when):
    """{"name", "illumination" (percent lit), "age" (days into the cycle)} for a UTC datetime."""
    age = moon_age(when)
    lit = (1 - math.cos(2 * math.pi * age / SYNODIC)) / 2 * 100
    return {"name": _name(age), "illumination": lit, "age": age}


def next_phase(when, target_age):
    """When the moon next reaches target_age (0 for new moon, FULL_AGE for full moon)."""
    days = (target_age - moon_age(when)) % SYNODIC
    return when + timedelta(days=days)
