"""Comfort index formulas: heat index, wind chill, and humidex.

Copied from the dashboard's update_records.py (heat_index_f, humidex_c, wind_chill_f).
See SOURCES.md.
"""

import math


def heat_index_f(t, rh):
    """Heat index in °F from air temperature (°F) and relative humidity (%). None if no data."""
    if t is None or rh is None:
        return None
    if t < 80:
        return t
    hi = (-42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh - 6.83783e-3 * t * t
          - 5.481717e-2 * rh * rh + 1.22874e-3 * t * t * rh + 8.5282e-4 * t * rh * rh - 1.99e-6 * t * t * rh * rh)
    if rh < 13 and 80 <= t <= 112:
        hi -= ((13 - rh) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
    elif rh > 85 and 80 <= t <= 87:
        hi += ((rh - 85) / 10) * ((87 - t) / 5)
    return hi


def humidex_c(t_f, dew_f):
    """Humidex in °C from air temperature and dew point (both °F)."""
    if t_f is None or dew_f is None:
        return None
    t, td = (t_f - 32) / 1.8, (dew_f - 32) / 1.8
    e = 6.11 * math.exp(5417.7530 * (1 / 273.16 - 1 / (273.15 + td)))
    return t + 0.5555 * (e - 10)


def wind_chill_f(t, v):
    """Wind chill in °F. Returns the air temperature when wind chill does not apply."""
    if t is None:
        return None
    if v is None or t > 50 or v <= 3:
        return t
    return 35.74 + 0.6215 * t - 35.75 * v ** 0.16 + 0.4275 * t * v ** 0.16
