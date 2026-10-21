"""Stations: each station has its own readings database and settings file.

The first station ("main") keeps the original files in %APPDATA%\\WeatherLab, so existing data stays put.
Other stations live in %APPDATA%\\WeatherLab\\stations\\<id>\\. The station the pages show is set for each
run with set_current(). The collector thread for a station sets it too, so its database and settings match.
"""

import contextvars
from contextlib import contextmanager
import json
import os
import re
from pathlib import Path

MAIN = "main"
DEFAULT_NAME = "Home"
_current: contextvars.ContextVar = contextvars.ContextVar("weatherlab_station", default=MAIN)


def base_dir() -> Path:
    return Path(os.environ.get("APPDATA") or str(Path.home())) / "WeatherLab"


def current() -> str:
    return _current.get()


def set_current(station_id: str) -> None:
    _current.set(station_id or MAIN)


def folder(station_id: str | None = None) -> Path:
    sid = station_id or current()
    return base_dir() if sid == MAIN else base_dir() / "stations" / sid


def _registry_path() -> Path:
    return base_dir() / "stations.json"


def all_stations() -> list[dict]:
    """Every station as {"id", "name"}. The first station is always the main one."""
    rows = []
    try:
        data = json.loads(_registry_path().read_text(encoding="utf-8"))
        for r in data.get("stations", []):
            if isinstance(r, dict) and re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", str(r.get("id", ""))):
                rows.append({"id": str(r["id"]), "name": str(r.get("name") or r["id"])})
    except (OSError, ValueError, AttributeError):
        pass
    main = next((r for r in rows if r["id"] == MAIN), {"id": MAIN, "name": DEFAULT_NAME})
    return [main] + [r for r in rows if r["id"] != MAIN]


def _save(rows: list[dict]) -> None:
    path = _registry_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"stations": rows}, indent=2), encoding="utf-8")


def ids() -> list[str]:
    return [r["id"] for r in all_stations()]


def name_of(station_id: str) -> str:
    return next((r["name"] for r in all_stations() if r["id"] == station_id), station_id)


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40].strip("-")
    return s or "station"


def add_station(name: str) -> dict:
    """Register a station. Its id comes from the name. A name whose folder is still on disk reuses that folder,
    so an earlier station's readings come back."""
    rows = all_stations()
    base = slug(name)
    sid, number = base, 2
    while sid == MAIN or any(r["id"] == sid for r in rows):
        sid = f"{base}-{number}"
        number += 1
    row = {"id": sid, "name": name.strip() or sid}
    _save(rows + [row])
    folder(sid).mkdir(parents=True, exist_ok=True)
    return row


def rename_station(station_id: str, name: str) -> None:
    rows = all_stations()
    if not any(r["id"] == station_id for r in rows):
        raise ValueError("No station has that id.")
    _save([dict(r, name=name.strip() or r["name"]) if r["id"] == station_id else r for r in rows])


def remove_station(station_id: str) -> None:
    """Unregister a station and stop collecting for it. Its data folder is kept on disk."""
    if station_id == MAIN:
        raise ValueError("The first station can't be removed.")
    _save([r for r in all_stations() if r["id"] != station_id])


@contextmanager
def using(station_id: str):
    """Run a block against one station, then go back to the station before."""
    token = _current.set(station_id or MAIN)
    try:
        yield
    finally:
        _current.reset(token)
