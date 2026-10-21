"""Database backups: copies, pruning and the daily check. Uses a temporary database."""

import os
import sqlite3
import tempfile
import time
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


class BackupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.database = self.root / "weatherlab.db"
        make_db(self.database, 25)
        self.folder = backup.folder_for(self.database)

    def tearDown(self):
        self._tmp.cleanup()

    def test_copy_has_the_same_rows(self):
        path = backup.make_backup(self.database, self.folder, datetime(2026, 10, 1, 3, 0, 0))
        self.assertEqual(path.name, "weatherlab-20261001-030000.db")
        copy = sqlite3.connect(path)
        self.assertEqual(copy.execute("SELECT COUNT(*) FROM readings").fetchone()[0], 25)
        copy.close()
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_prune_keeps_the_newest(self):
        for day in range(1, 6):
            backup.make_backup(self.database, self.folder, datetime(2026, 10, day, 3, 0, 0))
        removed = backup.prune(self.folder, 2)
        self.assertEqual(len(removed), 3)
        self.assertEqual([p.name for p in backup.backups(self.folder)],
                         ["weatherlab-20261004-030000.db", "weatherlab-20261005-030000.db"])

    def test_prune_never_removes_other_files(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        notes = self.folder / "notes.txt"
        notes.write_text("keep me")
        backup.make_backup(self.database, self.folder, datetime(2026, 10, 1, 3, 0, 0))
        backup.prune(self.folder, 1)
        self.assertTrue(notes.exists())

    def test_due_when_empty_and_not_after_a_fresh_copy(self):
        self.assertTrue(backup.due(self.folder, time.time()))
        path = backup.make_backup(self.database, self.folder, datetime.now())
        self.assertFalse(backup.due(self.folder, time.time()))
        old = time.time() - 25 * 3600
        os.utime(path, (old, old))
        self.assertTrue(backup.due(self.folder, time.time()))

    def test_run_if_due_makes_one_copy_a_day(self):
        now = datetime(2026, 10, 1, 3, 0, 0)
        self.assertIsNotNone(backup.run_if_due(self.database, 14, now))
        self.assertIsNone(backup.run_if_due(self.database, 14, now))


if __name__ == "__main__":
    unittest.main()
