"""Local SQLite storage. Same readings and daily tables the dashboard uses, in the user's own AppData folder."""

import json
import os
import sqlite3
import time
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
    db.execute("CREATE TABLE IF NOT EXISTS daily (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS noaa_daily (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS aqi (ts INTEGER PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS lightning_events (ts INTEGER PRIMARY KEY, distance REAL)")
    db.execute("CREATE TABLE IF NOT EXISTS fire (ts INTEGER PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS forecast_log (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
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


def readings_between(db: sqlite3.Connection, start_ts: float, end_ts: float) -> list[tuple[int, dict]]:
    """Readings in a time range, including ones moved to the archive table."""
    return [(ts, json.loads(data)) for ts, data in db.execute(
        "SELECT ts, data FROM readings WHERE ts >= ? AND ts < ? "
        "UNION ALL SELECT ts, data FROM readings_archive WHERE ts >= ? AND ts < ? ORDER BY ts",
        (int(start_ts), int(end_ts), int(start_ts), int(end_ts)))]


def readings_sampled(db: sqlite3.Connection, start_ts: float, end_ts: float, every_s: int = 600) -> list[tuple[int, dict]]:
    """The first reading in each every_s-second slot of a time range, in time order, including the archive. Enough
    for a wind pattern, and far quicker than reading every row."""
    s, e = int(start_ts), int(end_ts)
    rows = db.execute(
        "SELECT MIN(ts), data FROM readings WHERE ts >= ? AND ts < ? GROUP BY ts / ? "
        "UNION ALL SELECT MIN(ts), data FROM readings_archive WHERE ts >= ? AND ts < ? GROUP BY ts / ? ORDER BY 1",
        (s, e, every_s, s, e, every_s)).fetchall()
    return [(ts, json.loads(data)) for ts, data in rows]


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
