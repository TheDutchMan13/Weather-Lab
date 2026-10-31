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


def size_text(size: int) -> str:
    """File size in plain words: 412 MB, 38 KB."""
    if size >= 1024 * 1024 * 1024:
        return f"{size / 1024 ** 3:.1f} GB"
    if size >= 1024 * 1024:
        return f"{size / 1024 ** 2:.0f} MB"
    return f"{max(1, round(size / 1024))} KB"


def describe(folder: Path) -> list[dict]:
    """The backups newest first as {"name", "when", "size", "bytes", "path"}, for the Backup page."""
    rows = []
    for path in reversed(backups(folder)):
        info = path.stat()
        rows.append({"name": path.name, "when": datetime.fromtimestamp(info.st_mtime), "bytes": info.st_size,
                     "size": size_text(info.st_size), "path": path})
    return rows


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


def run_if_due(database: Path, keep: int, now: datetime) -> Path | None:
    """Make a backup if one is due, then prune. Returns the new file, or None when not due. The off-site copy is made
    separately by catch_up (0.37.54), so a missing drive doesn't count as a failed backup."""
    folder = folder_for(database)
    if not due(folder, now.timestamp()):
        return None
    path = make_backup(database, folder, now)
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


def copy_folder(target: str) -> Path | None:
    """The off-site folder for the current station: the folder set on Backup, with a subfolder for each extra station.
    None when no folder is set."""
    if not target.strip():
        return None
    folder = Path(target.strip())
    if stations.current() != stations.MAIN:
        folder = folder / stations.current()
    return folder


def copy_to_folder(path: Path, target: str, keep: int) -> Path | None:
    """Copy a backup to a second folder, such as a USB drive, a synced cloud folder or a shared folder on another PC,
    and check the copy opens (0.37.54). Does nothing when no folder is set. Raises OSError when it can't."""
    folder = copy_folder(target)
    if folder is None:
        return None
    folder.mkdir(parents=True, exist_ok=True)
    copy = folder / path.name
    shutil.copy2(path, copy)
    ok, why = verify(copy)
    if not ok:
        copy.unlink(missing_ok=True)
        raise OSError(f"The copy in {folder} didn't check out: {why}")
    prune(folder, keep)
    return copy


def missing_copies(local: list[Path], copies: list[Path], keep: int) -> list[Path]:
    """The local backups newer than the newest off-site copy, oldest first, at most `keep` of them. Names sort by
    time, so this compares names."""
    newest = copies[-1].name if copies else ""
    return [p for p in local if p.name > newest][-max(1, keep):]


def catch_up(local_folder: Path, target: str, keep: int) -> list[Path]:
    """Copy every backup the off-site folder is missing (0.37.54). A drive that was unplugged or a network folder that
    was offline catches up the next time it is there. Returns the copies made; raises OSError when it can't."""
    folder = copy_folder(target)
    if folder is None:
        return []
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
    made = [copy_to_folder(p, target, keep) for p in missing_copies(backups(local_folder), backups(folder), keep)]
    return [c for c in made if c is not None]


def stamp(path: Path) -> datetime | None:
    """When a backup was made, from its name (weatherlab-20261030-031500.db)."""
    try:
        return datetime.strptime(path.name[len(PREFIX):-len(SUFFIX)], "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def copy_status(local_folder: Path, target: str, now: datetime) -> dict:
    """How the off-site copy is doing, for the Backup page and the health check (0.37.54).

    {"set": a folder is chosen, "reachable": it can be listed, "count": copies there, "newest": when the newest copy
    was made, "behind_days": whole days the newest copy is older than the newest backup on this PC}."""
    folder = copy_folder(target)
    if folder is None:
        return {"set": False, "reachable": False, "count": 0, "newest": None, "behind_days": 0}
    try:
        copies = backups(folder) if folder.exists() else []
        reachable = folder.exists()
    except OSError:
        copies, reachable = [], False
    local = backups(local_folder)
    newest_copy = stamp(copies[-1]) if copies else None
    newest_local = stamp(local[-1]) if local else None
    behind = 0
    if newest_local is not None:
        behind = (newest_local - newest_copy).days if newest_copy else max(1, (now - newest_local).days + 1)
    return {"set": True, "reachable": reachable, "count": len(copies), "newest": newest_copy,
            "behind_days": max(0, behind)}


def verify(path: Path) -> tuple[bool, str]:
    """Open a backup read-only and check it is a readable Weather Lab database with readings in it.
    Returns (ok, plain-language result). Nothing is changed."""
    if not path.is_file():
        return False, "The backup file is missing."
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return False, f"It could not be opened: {exc}"
    try:
        verdict = con.execute("PRAGMA quick_check").fetchone()
        if not verdict or verdict[0] != "ok":
            return False, f"The file is damaged: {verdict[0] if verdict else 'no answer'}."
        has = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='readings'").fetchone()[0]
        if not has:
            return False, "It opens, but it has no readings table, so it is not a Weather Lab database."
        rows = con.execute("SELECT count(*) FROM readings").fetchone()[0]
        if rows == 0:
            return True, "It opens and is intact, but it holds no readings yet."
        return True, f"It opens, is intact, and holds {rows:,} readings."
    except sqlite3.Error as exc:
        return False, f"It could not be read: {exc}"
    finally:
        con.close()
