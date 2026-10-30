"""Canadian Fire Weather Index (FWI) from the station's latest reading and the NWS hourly forecast.

The equations are the dashboard's import_fire_weather.py, unchanged (see SOURCES.md). Changes for
Weather Lab:
- No hardcoded location, time zone, or NWS grid point. The forecast comes from the user's own
  /points lookup (nws.py), and the time zone comes from Settings.
- The moisture codes are saved in the database (the fire table) instead of fwi_state.json.
- Days since rain comes from the stored daily summaries.

Approximations (same as the dashboard):
- Today's values use the latest reading in place of the usual 1 pm observation.
- Forecast rain is assumed to be zero.
- Day length (DMC) and day-length factor (DC) are the standard values for about 30 degrees north.
  Elsewhere the moisture codes are a little off in summer and winter.
"""

import math
import re
from datetime import date, datetime, timedelta

DEFAULT_CODES = {"ffmc": 85.0, "dmc": 6.0, "dc": 15.0}

# Standard day length (DMC) and day-length factor (DC) by month, about 30 degrees north
DAY_LENGTH = {1: 6.5, 2: 7.5, 3: 9.0, 4: 12.8, 5: 13.9, 6: 13.9,
              7: 12.4, 8: 10.9, 9: 9.4, 10: 8.0, 11: 7.0, 12: 6.0}
DAY_FACTOR = {1: -1.6, 2: -1.6, 3: -1.6, 4: 0.9, 5: 3.8, 6: 5.8,
              7: 6.4, 8: 5.0, 9: 2.4, 10: 0.4, 11: -1.6, 12: -1.6}

MPH_TO_KMH = 1.609344
IN_TO_MM = 25.4


# ---------------------------------------------------------------- FWI system (from the dashboard)

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def ffmc_step(prev, temp, rh, wind, rain):
    """Fine Fuel Moisture Code. temp in C, rh in %, wind in km/h, rain in mm over 24 h."""
    mo = 147.2 * (101 - prev) / (59.5 + prev)
    if rain > 0.5:
        rf = rain - 0.5
        mr = mo + 42.5 * rf * math.exp(-100 / (251 - mo)) * (1 - math.exp(-6.93 / rf))
        if mo > 150:
            mr += 0.0015 * (mo - 150) ** 2 * math.sqrt(rf)
        mo = min(mr, 250.0)

    ed = (0.942 * rh ** 0.679 + 11 * math.exp((rh - 100) / 10)
          + 0.18 * (21.1 - temp) * (1 - math.exp(-0.115 * rh)))
    ew = (0.618 * rh ** 0.753 + 10 * math.exp((rh - 100) / 10)
          + 0.18 * (21.1 - temp) * (1 - math.exp(-0.115 * rh)))

    if mo > ed:
        ko = 0.424 * (1 - (rh / 100) ** 1.7) + 0.0694 * math.sqrt(wind) * (1 - (rh / 100) ** 8)
        m = ed + (mo - ed) * 10 ** (-ko * 0.581 * math.exp(0.0365 * temp))
    elif mo < ew:
        kl = (0.424 * (1 - ((100 - rh) / 100) ** 1.7)
              + 0.0694 * math.sqrt(wind) * (1 - ((100 - rh) / 100) ** 8))
        m = ew - (ew - mo) * 10 ** (-kl * 0.581 * math.exp(0.0365 * temp))
    else:
        m = mo

    return clamp(59.5 * (250 - m) / (147.2 + m), 0.0, 101.0)


def dmc_step(prev, temp, rh, rain, month):
    """Duff Moisture Code."""
    pr = prev
    if rain > 1.5:
        re_ = 0.92 * rain - 1.27
        mo = 20 + math.exp(5.6348 - prev / 43.43)
        if prev <= 33:
            b = 100 / (0.5 + 0.3 * prev)
        elif prev <= 65:
            b = 14 - 1.3 * math.log(prev)
        else:
            b = 6 * math.log(prev - 1)
        mr = mo + 1000 * re_ / (48.77 + b * re_)
        pr = max(244.72 - 43.43 * math.log(mr - 20), 0.0)

    k = 0.0 if temp < -1.1 else 1.894 * (temp + 1.1) * (100 - rh) * DAY_LENGTH[month] * 1e-6
    return max(pr + 100 * k, 0.0)


def dc_step(prev, temp, rain, month):
    """Drought Code."""
    dr = prev
    if rain > 2.8:
        rd = 0.83 * rain - 1.27
        qr = 800 * math.exp(-prev / 400) + 3.937 * rd
        dr = max(400 * math.log(800 / qr), 0.0)

    v = max(0.36 * (temp + 2.8) + DAY_FACTOR[month], 0.0) if temp > -2.8 else 0.0
    return max(dr + 0.5 * v, 0.0)


def fwi_indices(ffmc, dmc, dc, wind):
    """Initial Spread Index, Build-Up Index and Fire Weather Index. wind in km/h."""
    m = 147.2 * (101 - ffmc) / (59.5 + ffmc)
    ff = 91.9 * math.exp(-0.1386 * m) * (1 + m ** 5.31 / 4.93e7)
    isi = 0.208 * math.exp(0.05039 * wind) * ff

    denom = dmc + 0.4 * dc
    if dmc <= 0.4 * dc:
        bui = 0.8 * dmc * dc / denom if denom > 0 else 0.0
    else:
        bui = dmc - (1 - 0.8 * dc / denom) * (0.92 + (0.0114 * dmc) ** 1.7)
    bui = max(bui, 0.0)

    fd = 0.626 * bui ** 0.809 + 2 if bui <= 80 else 1000 / (25 + 108.64 * math.exp(-0.023 * bui))
    b = 0.1 * isi * fd
    fwi = math.exp(2.72 * (0.434 * math.log(b)) ** 0.647) if b > 1 else b
    return fwi, isi, bui


def roll_day(codes, temp_c, rh, wind_kmh, rain_mm, month):
    """Advance the moisture codes by one day and return them with the day's indices."""
    ffmc = ffmc_step(codes["ffmc"], temp_c, rh, wind_kmh, rain_mm)
    dmc = dmc_step(codes["dmc"], temp_c, rh, rain_mm, month)
    dc = dc_step(codes["dc"], temp_c, rain_mm, month)
    fwi, isi, bui = fwi_indices(ffmc, dmc, dc, wind_kmh)
    return {"ffmc": ffmc, "dmc": dmc, "dc": dc, "isi": isi, "bui": bui, "fwi": fwi}


# ---------------------------------------------------------------- Weather Lab additions

def f_to_c(f: float) -> float:
    return (f - 32) * 5 / 9


def starting_codes(today_iso: str, state: dict) -> dict:
    """Moisture codes at the start of today. Every run on the same day starts from the same codes."""
    if state.get("date") == today_iso and "base" in state:
        return dict(state["base"])
    if "today" in state:
        return {k: state["today"][k] for k in ("ffmc", "dmc", "dc")}
    return dict(DEFAULT_CODES)


def days_since_rain(daily_rows: list[tuple[str, float | None]], today: date, rain_today_in: float) -> int:
    """Days since the last day with more than 0.01 in of rain. daily_rows are (date, rain_in), newest first.
    Returns 30 when no stored day had rain, as the dashboard does."""
    if rain_today_in and rain_today_in > 0.01:
        return 0
    for day_iso, rain in daily_rows:
        if rain is not None and rain > 0.01:
            return (today - date.fromisoformat(day_iso)).days
    return 30


def forecast_noon(hourly: list[dict], tz) -> dict:
    """Temperature, humidity, and wind for each forecast day, from the hour nearest 1 pm local time.
    Input is nws.forecast_hourly output. Wind ranges like '5 to 10 mph' use the higher number."""
    best = {}
    for p in hourly:
        if str(p.get("unit", "F")).upper() != "F":
            continue
        temp, rh = p.get("temperature"), p.get("humidity")
        winds = [int(n) for n in re.findall(r"\d+", str(p.get("wind") or ""))]
        if temp is None or rh is None or not winds:
            continue
        try:
            start = datetime.fromisoformat(p["start"]).astimezone(tz)
        except (KeyError, ValueError):
            continue
        distance = abs(start.hour - 13)
        day = start.date()
        if day not in best or distance < best[day][0]:
            best[day] = (distance, {"temp_f": float(temp), "humidity": float(rh), "wind_mph": float(max(winds))})
    return {day: values for day, (_, values) in best.items()}


def build(obs: dict, state: dict, now: datetime, forecast_by_day: dict) -> dict:
    """One saved record: today's indices plus up to six forecast days (rain assumed zero).
    obs has temp_f, humidity, wind_mph, rain_in, days_since_rain."""
    today = now.date()
    today_iso = today.isoformat()
    base = starting_codes(today_iso, state)
    codes = roll_day(base, f_to_c(obs["temp_f"]), obs["humidity"],
                     obs["wind_mph"] * MPH_TO_KMH, obs["rain_in"] * IN_TO_MM, today.month)

    forecast = [{"day": "Today", "date": today_iso, "fwi": round(codes["fwi"], 1)}]
    prev = codes
    for i in range(1, 7):
        day = today + timedelta(days=i)
        w = forecast_by_day.get(day)
        if w is None:
            break
        c = roll_day(prev, f_to_c(w["temp_f"]), w["humidity"], w["wind_mph"] * MPH_TO_KMH, 0.0, day.month)
        forecast.append({"day": day.strftime("%a"), "date": day.isoformat(), "fwi": round(c["fwi"], 1),
                         "temperature": round(w["temp_f"]), "humidity": round(w["humidity"]),
                         "wind_speed": round(w["wind_mph"])})
        prev = c

    return {
        "date": today_iso,
        "base": base,
        "today": {k: codes[k] for k in ("ffmc", "dmc", "dc")},
        "fwi": round(codes["fwi"], 2),
        "ffmc": round(codes["ffmc"], 2),
        "dmc": round(codes["dmc"], 2),
        "dc": round(codes["dc"], 2),
        "isi": round(codes["isi"], 2),
        "bui": round(codes["bui"], 2),
        "temperature": obs["temp_f"],
        "humidity": obs["humidity"],
        "wind_speed": obs["wind_mph"],
        "rain_in": obs["rain_in"],
        "days_since_rain": obs["days_since_rain"],
        "timestamp": now.isoformat(),
        "forecast": forecast,
    }
