"""Local SQLite storage. Same readings and daily tables the dashboard uses, in the user's own AppData folder."""

import json
import sqlite3
import time
import zlib
from pathlib import Path

from weatherlab import stations

SOURCE = "gw2000"


def db_path() -> Path:
    """The readings database for the current station."""
    return stations.folder() / "weatherlab.db"


def connect(path: Path | None = None) -> sqlite3.Connection:
    path = path or db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=30, check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS readings (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, "
               "data TEXT NOT NULL, source TEXT DEFAULT 'gw2000', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    db.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_readings_ts ON readings(ts)")
    db.execute("CREATE TABLE IF NOT EXISTS readings_archive (ts INTEGER PRIMARY KEY, data TEXT NOT NULL, "
               "source TEXT DEFAULT 'gw2000')")
    # Old readings packed an hour at a time (0.37.58): one compressed row per hour holds every reading in it, about 14
    # times smaller than one row per reading. Nothing is thrown away; reads unpack them transparently.
    # first_ts and first hold the hour's first reading unpacked, so hourly sampling (the all-time wind rose) needn't
    # unpack anything.
    db.execute("CREATE TABLE IF NOT EXISTS readings_packed (hour INTEGER PRIMARY KEY, n INTEGER NOT NULL, "
               "first_ts INTEGER NOT NULL, first TEXT NOT NULL, data BLOB NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS daily (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS noaa_daily (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS aqi (ts INTEGER PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS lightning_events (ts INTEGER PRIMARY KEY, distance REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS fire (ts INTEGER PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS forecast_log (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
    # The forecast report card (0.37.54): the first forecast saved each day, for every day it covers, so a forecast
    # made 3 days ahead can be graded separately from one made the same morning.
    db.execute("CREATE TABLE IF NOT EXISTS forecast_ahead (made TEXT NOT NULL, date TEXT NOT NULL, high REAL, low REAL, "
               "pop REAL, PRIMARY KEY (made, date))")
    db.execute("CREATE TABLE IF NOT EXISTS alert_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts INTEGER NOT NULL, text TEXT NOT NULL)")
    return db


def store_reading(db: sqlite3.Connection, reading: dict, ts: float | None = None) -> None:
    with db:
        db.execute("INSERT OR IGNORE INTO readings (ts, data, source) VALUES (?, ?, ?)",
                   (int(ts or time.time()), json.dumps(reading), SOURCE))


def latest(db: sqlite3.Connection) -> tuple[int, dict] | None:
    row = db.execute("SELECT ts, data FROM readings ORDER BY ts DESC LIMIT 1").fetchone()
    return None if row is None else (row[0], json.loads(row[1]))


def store_aqi(db: sqlite3.Connection, data: dict, ts: float | None = None) -> None:
    with db:
        db.execute("INSERT OR REPLACE INTO aqi (ts, data) VALUES (?, ?)", (int(ts or time.time()), json.dumps(data)))


def latest_aqi(db: sqlite3.Connection) -> tuple[int, dict] | None:
    row = db.execute("SELECT ts, data FROM aqi ORDER BY ts DESC LIMIT 1").fetchone()
    return None if row is None else (row[0], json.loads(row[1]))


def store_strike(db: sqlite3.Connection, ts: int, distance_mi: float) -> None:
    with db:
        db.execute("INSERT OR IGNORE INTO lightning_events (ts, distance) VALUES (?, ?)", (ts, distance_mi))


def latest_strike(db: sqlite3.Connection) -> tuple[int, float] | None:
    row = db.execute("SELECT ts, distance FROM lightning_events ORDER BY ts DESC LIMIT 1").fetchone()
    return None if row is None else (row[0], row[1])


def store_fire(db: sqlite3.Connection, record: dict, ts: float | None = None) -> None:
    with db:
        db.execute("INSERT OR REPLACE INTO fire (ts, data) VALUES (?, ?)", (int(ts or time.time()), json.dumps(record)))


def latest_fire(db: sqlite3.Connection) -> dict | None:
    row = db.execute("SELECT data FROM fire ORDER BY ts DESC LIMIT 1").fetchone()
    return None if row is None else json.loads(row[0])


def recent_daily_rain(db: sqlite3.Connection, limit: int = 60) -> list[tuple[str, float | None]]:
    """(date, rain_in) for the newest daily summaries, newest first."""
    out = []
    for day, data in db.execute("SELECT date, data FROM daily ORDER BY date DESC LIMIT ?", (limit,)):
        out.append((day, json.loads(data).get("rain_in")))
    return out


PACK_AFTER_DAYS = 35  # readings older than this are packed by hour; the last month stays one row per reading


def _unpack(blob: bytes) -> list[tuple[int, str]]:
    return [(int(ts), data) for ts, data in json.loads(zlib.decompress(blob))]


def _pack(rows: list[tuple[int, str]]) -> bytes:
    return zlib.compress(json.dumps(rows, separators=(",", ":")).encode("utf-8"), 6)


def packed_rows(db: sqlite3.Connection, start_ts: float, end_ts: float) -> list[tuple[int, str]]:
    """Packed readings in [start_ts, end_ts), as (ts, raw JSON text), in time order."""
    s, e = int(start_ts), int(end_ts)
    out = []
    for (blob,) in db.execute("SELECT data FROM readings_packed WHERE hour >= ? AND hour < ? ORDER BY hour",
                              (s // 3600, (e + 3599) // 3600)):
        out.extend((ts, data) for ts, data in _unpack(blob) if s <= ts < e)
    return out


def _raw_between(db: sqlite3.Connection, start_ts: float, end_ts: float) -> list[tuple[int, str]]:
    s, e = int(start_ts), int(end_ts)
    rows = db.execute(
        "SELECT ts, data FROM readings WHERE ts >= ? AND ts < ? "
        "UNION ALL SELECT ts, data FROM readings_archive WHERE ts >= ? AND ts < ?", (s, e, s, e)).fetchall()
    packed = packed_rows(db, s, e)
    if packed:
        rows = rows + packed
    rows.sort(key=lambda r: r[0])
    return rows


def readings_between(db: sqlite3.Connection, start_ts: float, end_ts: float) -> list[tuple[int, dict]]:
    """Readings in a time range, including archived and packed ones, in time order. Unreadable rows are skipped."""
    out = []
    for ts, data in _raw_between(db, start_ts, end_ts):
        try:
            out.append((ts, json.loads(data)))
        except (TypeError, ValueError):
            continue
    return out


def reading_times(db: sqlite3.Connection, start_ts: float, end_ts: float) -> list[int]:
    """Just the timestamps of the readings in a range, sorted."""
    return [ts for ts, _ in _raw_between(db, start_ts, end_ts)]


def readings_sampled(db: sqlite3.Connection, start_ts: float, end_ts: float, every_s: int = 600) -> list[tuple[int, dict]]:
    """The first reading in each every_s-second slot of a time range, in time order, including archived and packed
    readings. Enough for a wind pattern, and far quicker than reading every row."""
    s, e = int(start_ts), int(end_ts)
    rows = db.execute(
        "SELECT MIN(ts), data FROM readings WHERE ts >= ? AND ts < ? GROUP BY ts / ? "
        "UNION ALL SELECT MIN(ts), data FROM readings_archive WHERE ts >= ? AND ts < ? GROUP BY ts / ?",
        (s, e, every_s, s, e, every_s)).fetchall()
    if every_s % 3600 == 0:  # whole hours: each packed hour's first reading is enough, and is kept unpacked
        rows.extend(db.execute("SELECT MIN(first_ts), first FROM readings_packed WHERE first_ts >= ? AND first_ts < ? "
                               "GROUP BY first_ts / ?", (s, e, every_s)).fetchall())
    else:
        last = None
        for ts, data in packed_rows(db, s, e):
            slot = ts // every_s
            if slot != last:
                rows.append((ts, data))
                last = slot
    rows.sort(key=lambda r: r[0])
    out, seen = [], set()
    for ts, data in rows:
        slot = ts // every_s
        if slot in seen:
            continue
        seen.add(slot)
        try:
            out.append((ts, json.loads(data)))
        except (TypeError, ValueError):
            continue
    return out


def series(db: sqlite3.Connection, key: str, start_ts: float, end_ts: float, every_s: int) -> list[tuple[int, float]]:
    """One reading's value, the latest in each every_s slot, as (ts, value). Done in SQL for the recent rows so a month
    of readings isn't parsed in Python (0.37.58)."""
    s, e = int(start_ts), int(end_ts)
    path = "$." + "".join(c for c in key if c.isalnum() or c == "_")
    rows = db.execute(
        "SELECT MAX(ts), json_extract(data, ?) FROM readings WHERE ts >= ? AND ts < ? AND json_valid(data) GROUP BY ts / ? "
        "UNION ALL SELECT MAX(ts), json_extract(data, ?) FROM readings_archive WHERE ts >= ? AND ts < ? "
        "AND json_valid(data) GROUP BY ts / ?",
        (path, s, e, every_s, path, s, e, every_s)).fetchall()
    for ts, data in packed_rows(db, s, e):
        try:
            rows.append((ts, json.loads(data).get(key)))
        except (TypeError, ValueError, AttributeError):
            continue
    best: dict[int, tuple[int, float]] = {}
    for ts, value in rows:
        if value is None or isinstance(value, str):
            continue
        slot = ts // every_s
        if slot not in best or ts > best[slot][0]:
            best[slot] = (ts, float(value))
    return [best[k] for k in sorted(best)]


def pack_before(db: sqlite3.Connection, cutoff_ts: float, batch_hours: int = 500) -> int:
    """Pack readings from whole hours before the cutoff into readings_packed and remove the single rows. Works in
    batches so the app stays responsive. Returns the number of readings packed. Nothing is lost: each hour is written
    and checked before its rows are deleted, in one transaction."""
    cutoff_hour = int(cutoff_ts) // 3600
    moved = 0
    while True:
        hours = [h for (h,) in db.execute(
            "SELECT DISTINCT ts / 3600 FROM (SELECT ts FROM readings WHERE ts < ?1 "
            "UNION ALL SELECT ts FROM readings_archive WHERE ts < ?1) ORDER BY 1 LIMIT ?2",
            (cutoff_hour * 3600, batch_hours))]
        if not hours:
            return moved
        with db:
            for hour in hours:
                lo, hi = hour * 3600, hour * 3600 + 3600
                fresh = db.execute("SELECT ts, data FROM readings WHERE ts >= ? AND ts < ? "
                                   "UNION SELECT ts, data FROM readings_archive WHERE ts >= ? AND ts < ?",
                                   (lo, hi, lo, hi)).fetchall()
                held = db.execute("SELECT data FROM readings_packed WHERE hour = ?", (hour,)).fetchone()
                merged = dict(_unpack(held[0])) if held else {}
                for ts, data in fresh:
                    merged.setdefault(int(ts), data)
                rows = sorted(merged.items())
                blob = _pack(rows)
                if len(_unpack(blob)) != len(rows):  # never delete anything that didn't pack cleanly
                    raise sqlite3.DatabaseError("Packing check failed")
                db.execute("INSERT OR REPLACE INTO readings_packed (hour, n, first_ts, first, data) VALUES (?, ?, ?, ?, ?)",
                           (hour, len(rows), rows[0][0], rows[0][1], blob))
                db.execute("DELETE FROM readings WHERE ts >= ? AND ts < ?", (lo, hi))
                db.execute("DELETE FROM readings_archive WHERE ts >= ? AND ts < ?", (lo, hi))
                moved += len(fresh)


def reading_count(db: sqlite3.Connection) -> int:
    """Every reading kept, single and packed."""
    single = db.execute("SELECT (SELECT COUNT(*) FROM readings) + (SELECT COUNT(*) FROM readings_archive)").fetchone()[0]
    packed = db.execute("SELECT COALESCE(SUM(n), 0) FROM readings_packed").fetchone()[0]
    return single + packed


def archive_before(db: sqlite3.Connection, cutoff_ts: float) -> int:
    """Move raw readings older than the cutoff into the archive table. Nothing is deleted from the data. Returns the
    number of readings moved."""
    with db:
        cur = db.execute("INSERT OR IGNORE INTO readings_archive (ts, data, source) "
                         "SELECT ts, data, source FROM readings WHERE ts < ?", (int(cutoff_ts),))
        moved = cur.rowcount
        db.execute("DELETE FROM readings WHERE ts < ? AND ts IN (SELECT ts FROM readings_archive)", (int(cutoff_ts),))
    return moved


def store_noaa_days(db: sqlite3.Connection, days: dict) -> None:
    """NOAA daily values, keyed by date ISO string. Days already in the app's own daily table are left alone when read."""
    with db:
        db.executemany("INSERT OR REPLACE INTO noaa_daily (date, data) VALUES (?, ?)",
                       [(day, json.dumps(values)) for day, values in days.items()])


def noaa_summary(db: sqlite3.Connection) -> tuple[int, str | None, str | None]:
    """(number of NOAA days stored, first date, last date)."""
    count, first, last = db.execute("SELECT COUNT(*), MIN(date), MAX(date) FROM noaa_daily").fetchone()
    return count, first, last


def noaa_days_between(db: sqlite3.Connection, start: str, end: str) -> list[tuple[str, dict]]:
    return [(d, json.loads(data)) for d, data in db.execute(
        "SELECT date, data FROM noaa_daily WHERE date >= ? AND date <= ? ORDER BY date", (start, end))]


def strikes_between(db: sqlite3.Connection, start_ts: float, end_ts: float) -> list[tuple[int, float]]:
    return db.execute("SELECT ts, distance FROM lightning_events WHERE ts >= ? AND ts < ? ORDER BY ts",
                      (int(start_ts), int(end_ts))).fetchall()


def store_forecasts(db: sqlite3.Connection, values: dict) -> None:
    """Keep the latest forecast high for each date. Each new forecast replaces the one before it."""
    with db:
        for day, value in values.items():
            db.execute("INSERT OR REPLACE INTO forecast_log (date, data) VALUES (?, ?)", (day, json.dumps(value)))


def store_forecast_ahead(db: sqlite3.Connection, made: str, values: dict) -> None:
    """Keep the first forecast saved on `made` (a local date) for each day it covers. Later forecasts that day are
    ignored, so each day is graded on the forecast as it stood early that day."""
    with db:
        for day, v in values.items():
            db.execute("INSERT OR IGNORE INTO forecast_ahead (made, date, high, low, pop) VALUES (?, ?, ?, ?, ?)",
                       (made, day, v.get("high"), v.get("low"), v.get("pop")))


def forecast_ahead(db: sqlite3.Connection, since: str) -> list[tuple[str, str, float | None, float | None, float | None]]:
    """(made, date, high, low, pop) for forecast days on or after `since`, oldest first."""
    return db.execute("SELECT made, date, high, low, pop FROM forecast_ahead WHERE date >= ? ORDER BY date, made",
                      (since,)).fetchall()


def forecast_highs(db: sqlite3.Connection) -> dict:
    """Forecast high for each date, as {date: high}."""
    from datetime import date as _date
    rows = db.execute("SELECT date, data FROM forecast_log").fetchall()
    return {_date.fromisoformat(d): json.loads(data)["high"] for d, data in rows}


def log_alert(db: sqlite3.Connection, ts: float, text: str) -> None:
    with db:
        db.execute("INSERT INTO alert_log (ts, text) VALUES (?, ?)", (int(ts), text))


def recent_alerts(db: sqlite3.Connection, limit: int = 300) -> list[tuple[int, str]]:
    """The newest alerts first, as (timestamp, text)."""
    return db.execute("SELECT ts, text FROM alert_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()


def forecast_pops(db: sqlite3.Connection) -> dict:
    """Forecast chance of rain (percent) for each date that has one."""
    from datetime import date as _date
    out = {}
    for day, data in db.execute("SELECT date, data FROM forecast_log").fetchall():
        pop = json.loads(data).get("pop")
        if pop is not None:
            out[_date.fromisoformat(day)] = pop
    return out
