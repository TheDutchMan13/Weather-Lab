"""Automatic copies of the Weather Lab database, one a day, keeping the newest few.

Copies are made with SQLite's backup API, so they are safe to take while the poller is writing.
They live in a 'backups' folder beside the database and are named by time, so the newest sorts last.
Only files named weatherlab-*.db are ever removed.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from weatherlab import stations

PREFIX = "weatherlab-"
SUFFIX = ".db"
INTERVAL_SECONDS = 24 * 3600


def folder_for(database: Path) -> Path:
    return database.parent / "backups"


def make_backup(database: Path, folder: Path, now: datetime) -> Path:
    """Copy the database into the folder. The copy is written under a temporary name, then renamed."""
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{PREFIX}{now:%Y%m%d-%H%M%S}{SUFFIX}"
    target = folder / name
    temp = folder / (name + ".tmp")
    source = sqlite3.connect(database)
    try:
        copy = sqlite3.connect(temp)
        try:
            source.backup(copy)
        finally:
            copy.close()
    finally:
        source.close()
    temp.replace(target)
    return target


def backups(folder: Path) -> list[Path]:
    """Backup files, oldest first."""
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.glob(f"{PREFIX}*{SUFFIX}") if p.is_file())


def prune(folder: Path, keep: int) -> list[Path]:
    """Delete all but the newest `keep` backups. Returns the files removed."""
    items = backups(folder)
    doomed = items[:max(0, len(items) - max(1, keep))]
    for path in doomed:
        path.unlink()
    return doomed


def due(folder: Path, now_ts: float, interval: int = INTERVAL_SECONDS) -> bool:
    """True when there is no backup, or the newest one is at least `interval` seconds old."""
    items = backups(folder)
    if not items:
        return True
    return now_ts - items[-1].stat().st_mtime >= interval


def run_if_due(database: Path, keep: int, now: datetime, copy_to: str = "") -> Path | None:
    """Make a backup if one is due, then prune. Returns the new file, or None when not due."""
    folder = folder_for(database)
    if not due(folder, now.timestamp()):
        return None
    path = make_backup(database, folder, now)
    copy_to_folder(path, copy_to, keep)
    prune(folder, keep)
    return path


def restore(source: Path, database: Path, folder: Path, now: datetime) -> Path:
    """Replace the database with a backup. The current data is copied to the folder first, and that copy is returned."""
    safety = make_backup(database, folder, now)
    src = sqlite3.connect(source)
    try:
        dst = sqlite3.connect(database)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    return safety


def copy_to_folder(path: Path, target: str, keep: int) -> Path | None:
    """Copy a backup to a second folder, such as a USB drive or a synced folder. Does nothing when no folder is set."""
    if not target.strip():
        return None
    folder = Path(target.strip())
    if stations.current() != stations.MAIN:
        folder = folder / stations.current()
    folder.mkdir(parents=True, exist_ok=True)
    copy = folder / path.name
    shutil.copy2(path, copy)
    prune(folder, keep)
    return copy
