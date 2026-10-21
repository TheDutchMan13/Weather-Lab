"""Restoring a backup: the backup comes back and the data from before the restore is kept."""

import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from weatherlab import backup


def make_db(path: Path, rows: int) -> None:
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE readings (ts INTEGER)")
    db.executemany("INSERT INTO readings VALUES (?)", [(i,) for i in range(rows)])
    db.commit()
    db.close()


def count(path: Path) -> int:
    db = sqlite3.connect(path)
    try:
        return db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    finally:
        db.close()


class RestoreTests(unittest.TestCase):
    def test_restore_brings_back_the_backup_and_keeps_the_current_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "weatherlab.db"
            make_db(database, 25)
            folder = backup.folder_for(database)
            saved = backup.make_backup(database, folder, datetime(2026, 10, 1, 3, 0, 0))
            db = sqlite3.connect(database)
            db.executemany("INSERT INTO readings VALUES (?)", [(i,) for i in range(100, 110)])
            db.commit()
            db.close()
            safety = backup.restore(saved, database, folder, datetime(2026, 10, 2, 3, 0, 0))
            self.assertEqual(count(database), 25)
            self.assertEqual(count(safety), 35)


if __name__ == "__main__":
    unittest.main()
