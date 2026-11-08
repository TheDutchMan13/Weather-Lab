"""Sun and moon from your location: sunrise, sunset, solar noon, golden hour, twilight, moonrise, moonset and moon
phase. Works offline.

Sun times use the NOAA sunrise equation (about a minute accurate). Moonrise and moonset use the Astronomical
Almanac's low-precision moon position (a few minutes accurate). Moon phases use the mean synodic month, so the
dates can be off by about a day.
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


def _solar(lat, lon, day):
    """The sun's transit (solar noon) as a UTC datetime, and its declination in radians, for a date."""
    noon = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)
    n = round(_jd(noon) - 2451545.0)
    jstar = n - lon / 360
    m = math.radians((357.5291 + 0.98560028 * jstar) % 360)
    c = 1.9148 * math.sin(m) + 0.02 * math.sin(2 * m) + 0.0003 * math.sin(3 * m)
    lam = math.radians((math.degrees(m) + c + 180 + 102.9372) % 360)
    transit = 2451545.0 + jstar + 0.0053 * math.sin(m) - 0.0069 * math.sin(2 * lam)
    decl = math.asin(math.sin(lam) * math.sin(math.radians(23.4397)))
    return transit, decl


def sun_times(lat, lon, day, altitude=-0.833):
    """(morning, evening) as UTC datetimes: when the sun's centre crosses `altitude` degrees. The default is sunrise
    and sunset. (None, None) when the sun doesn't reach that height, or stays above it, that day."""
    transit, decl = _solar(lat, lon, day)
    phi = math.radians(lat)
    cos_w = (math.sin(math.radians(altitude)) - math.sin(phi) * math.sin(decl)) / (math.cos(phi) * math.cos(decl))
    if cos_w > 1 or cos_w < -1:
        return None, None
    w = math.degrees(math.acos(cos_w))
    return _from_jd(transit - w / 360), _from_jd(transit + w / 360)


def solar_noon(lat, lon, day):
    """When the sun is highest, as a UTC datetime."""
    return _from_jd(_solar(lat, lon, day)[0])


def noon_altitude(lat, lon, day):
    """How many degrees above the horizon the sun gets at solar noon."""
    decl = math.degrees(_solar(lat, lon, day)[1])
    return 90 - abs(lat - decl)


def golden_hour(lat, lon, day):
    """When the evening golden hour starts (the sun 6 degrees above the horizon), or None."""
    return sun_times(lat, lon, day, 6.0)[1]


def twilight_end(lat, lon, day):
    """When civil twilight ends in the evening (the sun 6 degrees below the horizon), or None."""
    return sun_times(lat, lon, day, -6.0)[1]


def day_length(lat, lon, day):
    """Seconds of daylight, or None when the sun doesn't rise or set that day."""
    rise, set_ = sun_times(lat, lon, day)
    return None if rise is None or set_ is None else (set_ - rise).total_seconds()


def _sind(x):
    return math.sin(math.radians(x))


def _cosd(x):
    return math.cos(math.radians(x))


def moon_position(jd):
    """The moon's right ascension and declination in radians, and its horizontal parallax in degrees, from the
    Astronomical Almanac's low-precision formulas (about a third of a degree)."""
    t = (jd - 2451545.0) / 36525.0
    lon = (218.32 + 481267.881 * t + 6.29 * _sind(135.0 + 477198.87 * t) - 1.27 * _sind(259.3 - 413335.36 * t)
           + 0.66 * _sind(235.7 + 890534.22 * t) + 0.21 * _sind(269.9 + 954397.74 * t)
           - 0.19 * _sind(357.5 + 35999.05 * t) - 0.11 * _sind(186.5 + 966404.03 * t))
    lat = (5.13 * _sind(93.3 + 483202.02 * t) + 0.28 * _sind(228.2 + 960400.89 * t)
           - 0.28 * _sind(318.3 + 6003.15 * t) - 0.17 * _sind(217.6 - 407332.21 * t))
    par = (0.9508 + 0.0518 * _cosd(135.0 + 477198.87 * t) + 0.0095 * _cosd(259.3 - 413335.36 * t)
           + 0.0078 * _cosd(235.7 + 890534.22 * t) + 0.0028 * _cosd(269.9 + 954397.74 * t))
    l = _cosd(lat) * _cosd(lon)
    m = 0.9175 * _cosd(lat) * _sind(lon) - 0.3978 * _sind(lat)
    n = 0.3978 * _cosd(lat) * _sind(lon) + 0.9175 * _sind(lat)
    return math.atan2(m, l) % (2 * math.pi), math.asin(n), par


def _moon_edge(lat, lon, when):
    """Degrees the moon's upper edge is above the horizon, allowing for parallax and refraction. Zero at rise and set."""
    jd = _jd(when)
    ra, dec, par = moon_position(jd)
    lst = math.radians((280.46061837 + 360.98564736629 * (jd - 2451545.0) + lon) % 360)
    phi = math.radians(lat)
    h = math.asin(math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(lst - ra))
    return math.degrees(h) - par * math.cos(h) + 0.5667 + 0.2725 * par


def moon_rise_set(lat, lon, day, tz):
    """(moonrise, moonset) as UTC datetimes for the calendar day in `tz`. Either is None when it doesn't happen that day."""
    start = datetime(day.year, day.month, day.day, tzinfo=tz).astimezone(timezone.utc)
    end = datetime(day.year, day.month, day.day, tzinfo=tz) + timedelta(days=1)
    end = end.astimezone(timezone.utc)
    step = timedelta(minutes=5)
    rise = set_ = None
    prev_t, prev_v = start, _moon_edge(lat, lon, start)
    t = start + step
    while prev_t < end:
        t = min(t, end)
        v = _moon_edge(lat, lon, t)
        if (prev_v < 0) != (v < 0):
            frac = prev_v / (prev_v - v)
            crossing = prev_t + (t - prev_t) * frac
            if v >= 0 and rise is None:
                rise = crossing
            elif v < 0 and set_ is None:
                set_ = crossing
        prev_t, prev_v = t, v
        t = prev_t + step
        if prev_t >= end:
            break
    return rise, set_


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


def moon_waxing(when):
    """True while the moon is growing (new moon to full moon)."""
    return moon_age(when) < FULL_AGE


def next_phase(when, target_age):
    """When the moon next reaches target_age (0 for new moon, FULL_AGE for full moon)."""
    days = (target_age - moon_age(when)) % SYNODIC
    return when + timedelta(days=days)


# ---------------------------------------------------------------- one call for the pages


def length_text(seconds, short=False):
    """10 h 44 min, or 10 h 44 m when short (for a small tile)."""
    if seconds is None:
        return "--"
    minutes = round(seconds / 60)
    return f"{minutes // 60} h {minutes % 60} {'m' if short else 'min'}"


def change_text(seconds):
    """How today's daylight compares with yesterday's: "1 min 5 s shorter than yesterday"."""
    if seconds is None:
        return ""
    whole = round(abs(seconds))
    if whole == 0:
        return "the same as yesterday"
    mins, secs = divmod(whole, 60)
    amount = (f"{mins} min " if mins else "") + (f"{secs} s" if secs or not mins else "")
    return f"{amount.strip()} {'longer' if seconds > 0 else 'shorter'} than yesterday"


def moon_label(when):
    """What to call the moon in a table: the phase name at the key phases, otherwise how much is lit."""
    phase = moon_phase(when)
    if phase["name"] in ("New moon", "Full moon", "First quarter", "Last quarter"):
        return phase["name"]
    return f"{phase['illumination']:.0f}% lit"


def overview(lat, lon, tz, now, days=14):
    """Everything the Astronomy pages show, as local datetimes. `now` is a UTC datetime."""
    today = now.astimezone(tz).date()

    def local(dt):
        return None if dt is None else dt.astimezone(tz)

    rise, set_ = sun_times(lat, lon, today)
    length = day_length(lat, lon, today)
    before = day_length(lat, lon, today - timedelta(days=1))
    progress = None
    if rise is not None and set_ is not None and rise <= now <= set_:
        progress = (now - rise).total_seconds() / (set_ - rise).total_seconds()
    phase = moon_phase(now)
    moon_up, moon_down = moon_rise_set(lat, lon, today, tz)
    rows = []
    for offset in range(days):
        day = today + timedelta(days=offset)
        d_rise, d_set = sun_times(lat, lon, day)
        noon = datetime(day.year, day.month, day.day, 12, tzinfo=tz).astimezone(timezone.utc)
        rows.append({"date": day, "sunrise": local(d_rise), "sunset": local(d_set),
                     "length": day_length(lat, lon, day), "moon": moon_label(noon)})
    return {
        "today": today,
        "sunrise": local(rise), "sunset": local(set_),
        "length": length, "change": None if length is None or before is None else length - before,
        "progress": progress,
        "noon": local(solar_noon(lat, lon, today)),
        "noon_altitude": noon_altitude(lat, lon, today),
        "golden_hour": local(golden_hour(lat, lon, today)),
        "twilight_end": local(twilight_end(lat, lon, today)),
        "moon": {"name": phase["name"], "illumination": phase["illumination"], "age": phase["age"],
                 "waxing": moon_waxing(now), "rise": local(moon_up), "set": local(moon_down),
                 "next_full": local(next_phase(now, FULL_AGE)), "next_new": local(next_phase(now, 0))},
        "days": rows,
    }
