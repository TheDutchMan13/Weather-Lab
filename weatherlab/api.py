"""A small read-only JSON API for companion apps, such as the Android app. Off by default.

It runs only while Weather Lab is open, and only when "Let phones and devices" is on. Every request needs the token
from Settings, sent as "Authorization: Bearer <token>". The token is stored as a SHA-256 hash in Windows Credential
Manager, so the app keeps no copy of it in plain text. Too many wrong tokens lock the API for ten minutes.

Endpoints (all GET, all JSON, version 1):
  /api/v1/status    app and station status
  /api/v1/current   the latest reading, in the units chosen in Settings, with the plain-language words for dew point, wind direction and UV
  /api/v1/today     today's high, low and rain so far
  /api/v1/alerts    the 20 most recent alerts
  /api/v1/history   the last 24 hours of temperature, one point about every half hour
  /api/v1/tiles     what the Home page tiles need: 24-hour lines for humidity, wind, gust, pressure, solar, indoor temperature and humidity, UV, rain and dew point, today's peaks and the pressure trend
  /api/v1/measure/<reading>/<1|7|30>  one reading over 1, 7 or 30 days with its high, low and average (for tapping a Live tile)
  /api/v1/week      high, low and rain for the last 7 days, today included
  /api/v1/storm     the last lightning strike, strikes in the last 10 and 30 minutes and today, and a simple trend
  /api/v1/charts/7  (or /30, /all) a daily high, low, average, rain and gust for each of the last 7 (or 30, or all) days, with the rain totals
  /api/v1/days      the last 60 days with data, newest first: high, low and rain
  /api/v1/days/2026-10-20  (or /yesterday) every figure kept for that one day
  /api/v1/records   the all-time highs and lows, with the day each happened
  /api/v1/records/analysis  summary numbers, the heat, cold, wind and rain event lists, and the daily-high distribution (for Records and analysis)
  /api/v1/rankings  the top 10 days for warmest, coolest, coldest nights, wettest, windiest, UV and sunniest
  /api/v1/rain/calendar/2026-10  rain for each day of a month, and the totals for every year
  /api/v1/rain/events  the wet spells of the last 60 days
  /api/v1/wind/1  (or /7, /30, /all) where the wind came from and how strong
  /api/v1/lightning/days  strikes per day for the last 30 days, with the closest
  /api/v1/sun  UV, sunshine hours, sunrise and sunset, and sunburn times
  /api/v1/heat  heat index now, today's peak, hot days this year and the heat safety levels
  /api/v1/station  how complete the data is, gaps, each sensor, and battery and signal when the station can be reached
  /api/v1/whatsnew  what each Weather Lab version added
  /api/v1/briefing  today at a glance: expected high against yesterday and last year, last night's low, heat, UV, rain chance, wind and things worth knowing
  /api/v1/forecast  the National Weather Service forecast for the station's location
  /api/v1/onthisday/10-23  (or /today) that calendar day in every year with data
  /api/v1/compare  months of the last three years side by side, rain to date, hot days by year
  /api/v1/month/2026-10  a month card: averages, extremes, rain and every day
  /api/v1/year/2026  a year in review
  /api/v1/milestones  first and last freeze, 90 and 100 degree day of each year
  /api/v1/anomalies  readings from the last 24 hours far outside the last month
  /api/v1/alerts/history  alerts from the last 14 days
  /api/v1/forecast/accuracy  how close the forecast highs were
  /api/v1/export/daily  every daily summary as CSV text
  /api/v1/rewind/2026-10-20  one past day, every 10 minutes
  /api/v1/airport  the station next to the nearest airport observation
  /api/v1/tropics  tropical storms from the National Hurricane Center, with distance from home
  /api/v1/radar  radar image addresses for the station's location
  /api/v1/air  AirNow air quality (only when an AirNow key is set)
  /api/v1/push  the phone-alert server and topic
"""

import hashlib
import hmac
import json
import secrets as pysecrets
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

from weatherlab import secrets as keystore
from weatherlab import api_pages
from weatherlab import history as history_db
from weatherlab import dew, history_series, nws, record_board, records_events, stations, storage, sun_uv, units
from weatherlab.config import APP_VERSION

VERSION = 1
KEY = "api-token"
PORT = 8600
MAX_FAILURES = 20
LOCK_SECONDS = 600

_lock = threading.Lock()
_server = None
_running_port = None
_error = ""
_failures = 0
_locked_until = 0.0


# ------------------------------------------------------------------ tokens

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_set() -> bool:
    return bool(keystore.get_key(KEY))


def create_token() -> str:
    """A new random token. Only its hash is kept, so the token is shown once, when it is made."""
    token = pysecrets.token_urlsafe(24)
    keystore.set_key(KEY, hash_token(token))
    return token


def clear_token() -> None:
    keystore.set_key(KEY, "")


def token_ok(authorization: str | None) -> bool:
    stored = keystore.get_key(KEY)
    if not stored or not authorization or not authorization.startswith("Bearer "):
        return False
    supplied = authorization[len("Bearer "):].strip()
    return bool(supplied) and hmac.compare_digest(hash_token(supplied), stored)


def _locked() -> int:
    return max(0, int(_locked_until - time.time()))


def _record(ok: bool) -> None:
    global _failures, _locked_until
    if ok:
        _failures = 0
        return
    _failures += 1
    if _failures >= MAX_FAILURES:
        _failures = 0
        _locked_until = time.time() + LOCK_SECONDS


# ------------------------------------------------------------------ data

def _tz(s) -> ZoneInfo:
    try:
        return ZoneInfo(s.timezone)
    except Exception:
        return ZoneInfo("UTC")


def status(db, s, now: float) -> dict:
    latest = storage.latest(db)
    return {"app_version": APP_VERSION, "api_version": VERSION,
            "station": stations.name_of(stations.current()),
            "latest_reading_age_seconds": int(now - latest[0]) if latest else None}


def _convert_all(data: dict, metric: bool) -> dict:
    out = {}
    for key, value in data.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if units.converts(key):
            out[key] = {"value": round(units.convert(key, value, metric), 2), "unit": units.unit(key, metric)}
        else:
            out[key] = {"value": value, "unit": ""}
    return out


def words_for(data: dict) -> dict:
    """The plain-language wording for a reading, written once here so the apps never keep their own copies.

    Only words that can be worked out are included: "dew_point" (muggy), "wind_direction" (SSW), "uv" (high).
    """
    out = {}
    if data.get("dewpointf") is not None:
        out["dew_point"] = dew.text(data["dewpointf"])
    if data.get("winddir") is not None:
        out["wind_direction"] = nws.compass(data["winddir"])
    if data.get("uv") is not None:
        out["uv"] = sun_uv.uv_word(data["uv"])
    return out


def current(db, s, now: float) -> dict:
    latest = storage.latest(db)
    metric = units.is_metric(s.units)
    if latest is None:
        return {"reading": None, "metric": metric}
    ts, data = latest
    return {"reading": {"ts": ts, "age_seconds": int(now - ts), "values": _convert_all(data, metric),
                        "words": words_for(data)},
            "metric": metric}


def today(db, s, now: float) -> dict:
    tz = _tz(s)
    local = datetime.fromtimestamp(now, tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    rows = [r for _, r in storage.readings_between(db, start, now + 1)]
    metric = units.is_metric(s.units)
    temps = [r["tempf"] for r in rows if r.get("tempf") is not None]
    rain = [r["dailyrainin"] for r in rows if r.get("dailyrainin") is not None]

    def shown(key, value):
        # Rain keeps two decimals: in whole tenths, 0.05 in of rain would show as 0.1.
        digits = 2 if key == "dailyrainin" else 1
        return None if value is None else {"value": round(units.convert(key, value, metric), digits),
                                           "unit": units.unit(key, metric)}
    return {"date": local.date().isoformat(), "readings": len(rows),
            "high": shown("tempf", max(temps) if temps else None),
            "low": shown("tempf", min(temps) if temps else None),
            "rain": shown("dailyrainin", rain[-1] if rain else None),
            "metric": metric}


def alerts(db) -> dict:
    return {"alerts": [{"ts": ts, "text": text} for ts, text in storage.recent_alerts(db, limit=20)]}


def history(db, s, now: float) -> dict:
    """Temperature for the last 24 hours as [timestamp, value] pairs, in the units chosen in Settings."""
    metric = units.is_metric(s.units)
    rows = storage.readings_sampled(db, now - 24 * 3600, now + 1, every_s=1800)
    points = [[ts, round(units.convert("tempf", r["tempf"], metric), 1)] for ts, r in rows if r.get("tempf") is not None]
    latest = storage.latest(db)
    if latest and latest[1].get("tempf") is not None and (not points or latest[0] > points[-1][0]) \
            and latest[0] >= now - 24 * 3600:
        points.append([latest[0], round(units.convert("tempf", latest[1]["tempf"], metric), 1)])
    return {"hours": 24, "unit": units.unit("tempf", metric), "metric": metric, "points": points}


TILE_SERIES = ("humidity", "windspeedmph", "windgustmph", "baromrelin", "solarradiation",
               "tempinf", "humidityin", "uv", "rainratein", "dailyrainin", "dewpointf")
TILE_PEAKS = ("windgustmph", "uv", "solarradiation")


def _pressure_word(change: float) -> str:
    return ("rising fast" if change > 0.06 else "rising" if change > 0.02 else
            "falling fast" if change < -0.06 else "falling" if change < -0.02 else "steady")


def tiles(db, s, now: float) -> dict:
    """What the Android Live tiles show besides the latest reading: a 24-hour line for each measure, today's peaks
    and how the pressure has changed over the last three hours. Values are in the units chosen in Settings."""
    metric = units.is_metric(s.units)
    rows = storage.readings_sampled(db, now - 24 * 3600, now + 1, every_s=1800)
    series = {k: [[ts, round(units.convert(k, r[k], metric), 2)] for ts, r in rows if r.get(k) is not None]
              for k in TILE_SERIES}
    tz = _tz(s)
    start = datetime.fromtimestamp(now, tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    day = [r for _, r in storage.readings_between(db, start, now + 1)]
    peaks = {}
    for k in TILE_PEAKS:
        values = [r[k] for r in day if r.get(k) is not None]
        peaks[k] = round(units.convert(k, max(values), metric), 1) if values else None
    pressure = None
    latest = storage.latest(db)
    if latest and latest[1].get("baromrelin") is not None:
        old = [r["baromrelin"] for _, r in storage.readings_between(db, now - 3 * 3600 - 300, now - 3 * 3600 + 300)
               if r.get("baromrelin") is not None]
        if old:
            change = latest[1]["baromrelin"] - sum(old) / len(old)
            pressure = {"word": _pressure_word(change), "change": round(units.convert_change("baromrelin", change, metric), 3)}
    return {"hours": 24, "metric": metric, "series": series, "peaks": peaks, "pressure": pressure}


HISTORY_KEYS = ("tempf", "feelslikef", "dewpointf", "humidity", "windspeedmph", "windgustmph", "baromrelin", "uv",
                "solarradiation", "dailyrainin", "rainratein", "tempinf", "humidityin")
_HISTORY_BUCKET = {1: 600, 7: 1800, 30: 7200}  # seconds per point, to keep the answer small for a phone
_HISTORY_UNIT = {"humidity": "%", "humidityin": "%", "solarradiation": "W/m\u00b2", "uv": ""}


def measure_history(db, s, now: float, key: str, days: int) -> dict:
    """One reading over the last 1, 7 or 30 days as [timestamp, value] pairs, in the units chosen in Settings."""
    if key not in HISTORY_KEYS or days not in _HISTORY_BUCKET:
        return {"error": "Use /api/v1/measure/<reading>/<1, 7 or 30>."}
    metric = units.is_metric(s.units)
    raw = [(ts, r[key]) for ts, r in storage.readings_between(db, now - days * 86400, now + 1) if r.get(key) is not None]
    points = [[ts, round(units.convert(key, v, metric), 2)] for ts, v in history_series.thin(raw, _HISTORY_BUCKET[days])]
    values = [p[1] for p in points]
    return {"key": key, "days": days, "metric": metric, "unit": _HISTORY_UNIT.get(key, units.unit(key, metric)),
            "points": points,
            "high": max(values) if values else None, "low": min(values) if values else None,
            "average": round(sum(values) / len(values), 2) if values else None}


def week(db, s, now: float) -> dict:
    """The last 7 local days, oldest first. Finished days come from the daily summaries; today is live."""
    tz = _tz(s)
    metric = units.is_metric(s.units)
    live = today(db, s, now)
    first = datetime.fromtimestamp(now, tz).date() - timedelta(days=6)
    days = []
    for i in range(7):
        day = first + timedelta(days=i)
        iso = day.isoformat()
        if iso == live["date"]:
            high = live["high"]["value"] if live["high"] else None
            low = live["low"]["value"] if live["low"] else None
            rain = live["rain"]["value"] if live["rain"] else None
        else:
            row = db.execute("SELECT data FROM daily WHERE date = ?", (iso,)).fetchone()
            data = json.loads(row[0]) if row else {}

            def shown(key, value):
                digits = 2 if key == "dailyrainin" else 1
                return None if value is None else round(units.convert(key, value, metric), digits)
            high, low = shown("tempf", data.get("tempf_max")), shown("tempf", data.get("tempf_min"))
            rain = shown("dailyrainin", data.get("rain_in"))
        days.append({"date": iso, "high": high, "low": low, "rain": rain})
    return {"days": days, "metric": metric, "temp_unit": units.unit("tempf", metric),
            "rain_unit": units.unit("dailyrainin", metric)}


def _trend(strikes: list, now: float) -> str:
    """none, overhead, approaching, receding or steady, from the strikes in the last 30 minutes (distances in miles)."""
    recent = [(ts, d) for ts, d in strikes if ts >= now - 1800]
    if not recent:
        return "none"
    if recent[-1][1] <= 1.0:
        return "overhead"
    newer = [d for ts, d in recent if ts >= now - 600]
    older = [d for ts, d in recent if now - 1200 <= ts < now - 600]
    if newer and older:
        change = sum(newer) / len(newer) - sum(older) / len(older)
        if change <= -1.0:
            return "approaching"
        if change >= 1.0:
            return "receding"
    return "steady"


def storm(db, s, now: float) -> dict:
    """Lightning from the stored strikes, with distances in the units chosen in Settings."""
    tz = _tz(s)
    metric = units.is_metric(s.units)
    midnight = datetime.fromtimestamp(now, tz).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    strikes = storage.strikes_between(db, now - 1800, now + 1)
    last = storage.latest_strike(db)

    def dist(miles):
        return {"value": round(units.convert("miles", miles, metric), 1), "unit": units.unit("miles", metric)}
    return {
        "last_strike": None if last is None else {"ts": last[0], "age_seconds": max(0, int(now - last[0])),
                                                  "distance": dist(last[1])},
        "strikes_10m": sum(1 for ts, _ in strikes if ts >= now - 600),
        "strikes_30m": len(strikes),
        "strikes_today": len(storage.strikes_between(db, midnight, now + 1)),
        "trend": _trend(strikes, now),
        "metric": metric,
    }


# ------------------------------------------------------------------ charts, days, records

# (daily summary key, label, units key or None, unit text when there is no units key)
DAY_FIELDS = [
    ("tempf_max", "High", "tempf", ""), ("tempf_min", "Low", "tempf", ""), ("tempf_avg", "Average", "tempf", ""),
    ("heat_index_max", "Heat index high", "tempf", ""),
    ("humidity_max", "Humidity high", None, "%"), ("humidity_min", "Humidity low", None, "%"),
    ("rain_in", "Rain", "dailyrainin", ""), ("rainrate_max", "Rain rate peak", "rainratein", ""),
    ("gust_max", "Highest gust", "windgustmph", ""), ("wind_max", "Highest sustained wind", "windspeedmph", ""),
    ("wind_run_mi", "Wind run", "miles", ""),
    ("baro_max", "Pressure high", "baromrelin", ""), ("baro_min", "Pressure low", "baromrelin", ""),
    ("uvi", "UV index", None, ""), ("sun_hours", "Sun hours", None, "h"),
]
_DIGITS = {"dailyrainin": 2, "baromrelin": 2, "rainratein": 2}


def _shown(key: str | None, value, metric: bool):
    if value is None:
        return None
    if key is None:
        return round(value, 1)
    return round(units.convert(key, value, metric), _DIGITS.get(key, 1))


def _today_summary(db, s, now: float) -> tuple[str, dict]:
    """(today's date, a daily-style summary from the readings so far)."""
    live = today(db, s, now)
    data = {}
    if live["high"]:
        data["tempf_max"] = _raw(live["high"], "tempf", units.is_metric(s.units))
    if live["low"]:
        data["tempf_min"] = _raw(live["low"], "tempf", units.is_metric(s.units))
    if live["rain"]:
        data["rain_in"] = _raw(live["rain"], "dailyrainin", units.is_metric(s.units))
    return live["date"], data


def _raw(shown: dict, key: str, metric: bool) -> float:
    """Back to stored (US) units from an API value."""
    value = shown["value"]
    if not metric or key not in units.METRIC_UNIT:
        return value
    return (value * 9 / 5 + 32) if key == "tempf" else value / units._FACTOR[key]


ALL_DAYS_CAP = 1500  # "all" stops here so the reply stays small


def charts(db, s, now: float, days: int | None) -> dict:
    """A daily series for the last 7 or 30 local days (None = every day kept), oldest first. Days without a summary are None.

    Also carries the rain totals (today, last 7 days, this month, this year) for the Daily page."""
    tz = _tz(s)
    metric = units.is_metric(s.units)
    last = datetime.fromtimestamp(now, tz).date()
    if days is None:
        every_day = history_db.all_daily(db)
        first = every_day[0][0] if every_day else last
        first = max(first, last - timedelta(days=ALL_DAYS_CAP - 1))
        days = (last - first).days + 1
    else:
        first = last - timedelta(days=days - 1)
    held = {d.isoformat(): data for d, data in history_db.daily_between(db, first, last)}
    live_date, live = _today_summary(db, s, now)
    held[live_date] = {**held.get(live_date, {}), **live}
    every = 3600 if days <= 7 else 10800
    start = datetime.combine(first, datetime.min.time(), tzinfo=tz).timestamp()
    points = [] if days > 30 else [[ts, round(units.convert("tempf", r["tempf"], metric), 1)]
              for ts, r in storage.readings_sampled(db, start, now + 1, every_s=every) if r.get("tempf") is not None]
    totals = history_db.rain_totals(db, last, held.get(live_date, {}).get("rain_in"))
    out = []
    for i in range(days):
        iso = (first + timedelta(days=i)).isoformat()
        d = held.get(iso, {})
        out.append({"date": iso, "high": _shown("tempf", d.get("tempf_max"), metric),
                    "low": _shown("tempf", d.get("tempf_min"), metric),
                    "avg": _shown("tempf", d.get("tempf_avg"), metric),
                    "rain": _shown("dailyrainin", d.get("rain_in"), metric),
                    "gust": _shown("windgustmph", d.get("gust_max"), metric)})
    return {"days": out, "temp_points": points, "metric": metric, "temp_unit": units.unit("tempf", metric),
            "rain_unit": units.unit("dailyrainin", metric), "wind_unit": units.unit("windgustmph", metric),
            "rain_totals": {k: _shown("dailyrainin", v, metric) for k, v in totals.items()}}


def days_list(db, s, now: float) -> dict:
    """The last 60 days that have data, newest first, with the high, low and rain."""
    tz = _tz(s)
    metric = units.is_metric(s.units)
    last = datetime.fromtimestamp(now, tz).date()
    rows = history_db.daily_between(db, last - timedelta(days=59), last)
    held = {d.isoformat(): data for d, data in rows}
    live_date, live = _today_summary(db, s, now)
    if live:
        held[live_date] = {**held.get(live_date, {}), **live}
    out = [{"date": iso, "high": _shown("tempf", d.get("tempf_max"), metric),
            "low": _shown("tempf", d.get("tempf_min"), metric), "rain": _shown("dailyrainin", d.get("rain_in"), metric)}
           for iso, d in sorted(held.items(), reverse=True)]
    return {"days": out, "metric": metric, "temp_unit": units.unit("tempf", metric),
            "rain_unit": units.unit("dailyrainin", metric)}


def day_detail(db, s, now: float, which: str) -> dict:
    """Every figure kept for one day: 'yesterday' or a date such as 2026-10-20."""
    tz = _tz(s)
    metric = units.is_metric(s.units)
    last = datetime.fromtimestamp(now, tz).date()
    if which == "yesterday":
        day = last - timedelta(days=1)
    else:
        try:
            day = datetime.strptime(which, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Use a date like 2026-10-20, or yesterday."}
    iso = day.isoformat()
    row = db.execute("SELECT data FROM daily WHERE date = ?", (iso,)).fetchone()
    data = json.loads(row[0]) if row else {}
    if iso == last.isoformat():
        data = {**data, **_today_summary(db, s, now)[1]}
    if not data:
        return {"date": iso, "found": False, "metric": metric, "values": []}
    values = []
    for key, label, ukey, text in DAY_FIELDS:
        if data.get(key) is None:
            continue
        values.append({"key": key, "label": label, "value": _shown(ukey, data[key], metric),
                       "unit": units.unit(ukey, metric) if ukey else text})
    return {"date": iso, "found": True, "estimated": bool(data.get("estimated")),
            "partial": iso == last.isoformat(), "metric": metric, "values": values}


def records_list(db, s, now: float) -> dict:
    """All-time highs and lows from the daily summaries, with the day each happened."""
    metric = units.is_metric(s.units)
    out = []
    for item in history_db.records(db):
        ukey = history_db.RECORD_UNIT.get(item["key"])
        out.append({"key": item["key"], "label": item["label"], "value": _shown(ukey, item["value"], metric),
                    "unit": units.unit(ukey, metric) if ukey else item["unit"].strip(),
                    "date": item["date"].isoformat(), "estimated": item["estimated"]})
    return {"records": out, "metric": metric}


def records_analysis(db, s, now: float) -> dict:
    """Numbers and lists for the Records and analysis page (0.37.20): summary, extreme events, daily-high distribution."""
    metric = units.is_metric(s.units)
    days = history_db.all_daily(db)
    sm = records_events.summary(days)
    ev = records_events.events(days)

    def pick(found, ukey, limit=15):
        return [{"date": d.isoformat(), "value": _shown(ukey, v, metric)} for d, v in found[:limit]]

    def one(pair, ukey):
        return None if pair is None else {"value": _shown(ukey, pair[0], metric), "date": pair[1].isoformat()}

    return {
        "metric": metric,
        "units": {"temp": units.unit("tempf", metric), "gust": units.unit("windgustmph", metric),
                  "rain": units.unit("dailyrainin", metric)},
        "summary": {"days100": sm["days_100"], "days110": sm["days_110"], "hottest": one(sm["hottest"], "tempf"),
                    "gust": one(sm["gust"], "windgustmph"), "rainTotal": _shown("dailyrainin", sm["rain_total"], metric),
                    "rainDays": sm["rain_days"]},
        "counts": {k: len(v) for k, v in ev.items()},
        "events": {"heat": pick(ev["heat"], "tempf"), "cold": pick(ev["cold"], "tempf"),
                   "wind": pick(ev["wind"], "windgustmph"), "rain": pick(ev["rain"], "dailyrainin")},
        "limits": {"heat": _shown("tempf", records_events.HEAT_F, metric), "cold": _shown("tempf", records_events.COLD_F, metric),
                   "wind": _shown("windgustmph", records_events.WIND_MPH, metric),
                   "rain": _shown("dailyrainin", records_events.RAIN_IN, metric)},
        "distribution": [{"from": _shown("tempf", b, metric), "count": c} for b, c in records_events.distribution(days)],
        "board": _board(days, s, now, metric),
    }


def _board(days, s, now: float, metric: bool) -> list:
    """The records board grouped as on the Windows page: [{title, rows: [{label, value, unit, when, new, high}]}]."""
    today = datetime.fromtimestamp(now, ZoneInfo(s.timezone)).date()
    out = []
    for title, rows in record_board.board(days, today)["groups"]:
        shown = []
        for r in rows:
            if r["unit_key"]:
                value = round(units.convert(r["unit_key"], r["value"], metric), r["dec"])
                unit = units.unit(r["unit_key"], metric)
            else:
                value, unit = round(r["value"], r["dec"]), r["plain"].strip()
            shown.append({"label": r["label"], "value": value, "unit": unit, "when": r["when"],
                          "new": r["new"], "high": r["high"]})
        out.append({"title": title, "rows": shown})
    return out


# ------------------------------------------------------------------ routing

def route(path: str, authorization: str | None, db, s, now: float) -> tuple[int, dict]:
    """(HTTP status, body). Checks the token and the lock first, then the path."""
    if _locked():
        return 429, {"error": f"Too many wrong tokens. Try again in {_locked()} seconds."}
    if not token_ok(authorization):
        _record(False)
        return 401, {"error": "Sign in with the token from Weather Lab's Settings."}
    _record(True)
    builders = {"/api/v1/status": lambda: status(db, s, now),
                "/api/v1/current": lambda: current(db, s, now),
                "/api/v1/today": lambda: today(db, s, now),
                "/api/v1/alerts": lambda: alerts(db),
                "/api/v1/history": lambda: history(db, s, now),
                "/api/v1/tiles": lambda: tiles(db, s, now),
                "/api/v1/week": lambda: week(db, s, now),
                "/api/v1/storm": lambda: storm(db, s, now)}
    clean = path.rstrip("/") or "/"
    builders["/api/v1/days"] = lambda: days_list(db, s, now)
    builders["/api/v1/records"] = lambda: records_list(db, s, now)
    builders["/api/v1/records/analysis"] = lambda: records_analysis(db, s, now)
    if clean in ("/api/v1/charts/7", "/api/v1/charts/30", "/api/v1/charts/all"):
        tail = clean.rsplit("/", 1)[1]
        builders[clean] = lambda: charts(db, s, now, None if tail == "all" else int(tail))
    builders.update({"/api/v1/rankings": lambda: api_pages.rankings(db, s, now),
                     "/api/v1/rain/events": lambda: api_pages.rain_event_list(db, s, now),
                     "/api/v1/lightning/days": lambda: api_pages.lightning_days(db, s, now),
                     "/api/v1/sun": lambda: api_pages.sun(db, s, now),
                     "/api/v1/heat": lambda: api_pages.heat(db, s, now),
                     "/api/v1/station": lambda: api_pages.station(db, s, now),
                     "/api/v1/whatsnew": lambda: api_pages.whats_new_list(db, s, now),
                     "/api/v1/forecast": lambda: api_pages.forecast(db, s, now),
                     "/api/v1/briefing": lambda: api_pages.briefing_page(db, s, now)})
    if clean in ("/api/v1/wind/1", "/api/v1/wind/7", "/api/v1/wind/30", "/api/v1/wind/all"):
        tail = clean.rsplit("/", 1)[1]
        builders[clean] = lambda: api_pages.wind_rose_data(db, s, now, None if tail == "all" else int(tail))
    if clean.startswith("/api/v1/rain/calendar/"):
        month = clean.rsplit("/", 1)[1]
        builders[clean] = lambda: api_pages.rain_calendar(db, s, now, month)
    if clean.startswith("/api/v1/days/"):
        which = clean.rsplit("/", 1)[1]
        builders[clean] = lambda: day_detail(db, s, now, which)
    builders.update({"/api/v1/compare": lambda: api_pages.compare(db, s, now),
                     "/api/v1/milestones": lambda: api_pages.milestones(db, s, now),
                     "/api/v1/anomalies": lambda: api_pages.anomalies(db, s, now),
                     "/api/v1/alerts/history": lambda: api_pages.alert_history(db, s, now),
                     "/api/v1/forecast/accuracy": lambda: api_pages.forecast_accuracy(db, s, now),
                     "/api/v1/export/daily": lambda: api_pages.export_daily(db, s, now),
                     "/api/v1/airport": lambda: api_pages.airport(db, s, now),
                     "/api/v1/tropics": lambda: api_pages.tropics_list(db, s, now),
                     "/api/v1/radar": lambda: api_pages.radar(db, s, now),
                     "/api/v1/air": lambda: api_pages.air(db, s, now),
                     "/api/v1/push": lambda: api_pages.push_info(db, s, now)})
    for prefix, make in (("/api/v1/onthisday/", api_pages.on_this_day), ("/api/v1/month/", api_pages.month_card),
                         ("/api/v1/rewind/", api_pages.rewind)):
        if clean.startswith(prefix):
            builders[clean] = lambda make=make, arg=clean.rsplit("/", 1)[1]: make(db, s, now, arg)
    if clean.startswith("/api/v1/measure/"):
        parts = clean[len("/api/v1/measure/"):].split("/")
        if len(parts) == 2 and parts[1].isdigit():
            builders[clean] = lambda: measure_history(db, s, now, parts[0], int(parts[1]))
    if clean.startswith("/api/v1/year/"):
        year = clean.rsplit("/", 1)[1]
        builders[clean] = lambda: (api_pages.year_card(db, s, now, int(year)) if year.isdigit()
                                   else {"error": "Use a year like 2026."})
    build = builders.get(clean)
    if build is None:
        return 404, {"error": "No such address in the API."}
    return 200, build()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - the name http.server expects
        from weatherlab.settings import load_settings
        path = self.path.split("?", 1)[0]
        try:
            s = load_settings()
            with stations.using(stations.MAIN):
                db = storage.connect()
                try:
                    code, body = route(path, self.headers.get("Authorization"), db, s, time.time())
                finally:
                    db.close()
        except Exception:  # keep the server alive; never send a traceback to a phone
            code, body = 500, {"error": "Weather Lab couldn't read its data just now."}
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # no request log in the console
        return


def ensure(enabled: bool, port: int = PORT) -> None:
    """Start the API when it is on, stop it when it is off, and restart it on a new port. Safe to call on every page load."""
    global _server, _running_port, _error
    with _lock:
        if not enabled:
            _stop_locked()
            return
        if _server is not None and _running_port == port:
            return
        _stop_locked()
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
        except OSError:
            _error = f"Port {port} is in use by another program. Choose another port in Settings."
            return
        _error = ""
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _server, _running_port = srv, port


def _stop_locked() -> None:
    global _server, _running_port
    if _server is not None:
        _server.shutdown()
        _server.server_close()
    _server, _running_port = None, None


def status_text() -> str:
    if _error:
        return _error
    if _server is not None:
        return f"Running on port {_running_port}."
    return "Not running. Turn it on above, and allow phones and devices."
