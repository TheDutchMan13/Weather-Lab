"""The off-site backup copy (0.37.54): verified copies, catching up after the folder was away, and its status."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from tests.test_backup import make_db
from weatherlab import backup, health_check


class OffsiteTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.database = self.root / "weatherlab.db"
        make_db(self.database, 10)
        self.local = backup.folder_for(self.database)
        self.target = str(self.root / "offsite")

    def tearDown(self):
        self._tmp.cleanup()

    def _backup(self, day: int):
        return backup.make_backup(self.database, self.local, datetime(2026, 10, day, 3, 0, 0))

    def test_catch_up_copies_only_what_is_missing(self):
        for d in (1, 2, 3):
            self._backup(d)
        made = backup.catch_up(self.local, self.target, 14)
        self.assertEqual([p.name for p in made], [f"weatherlab-202610{d:02d}-030000.db" for d in (1, 2, 3)])
        self.assertEqual(backup.catch_up(self.local, self.target, 14), [])
        self._backup(4)
        self.assertEqual([p.name for p in backup.catch_up(self.local, self.target, 14)], ["weatherlab-20261004-030000.db"])

    def test_catch_up_copies_at_most_keep(self):
        for d in range(1, 8):
            self._backup(d)
        self.assertEqual(len(backup.catch_up(self.local, self.target, 3)), 3)

    def test_a_damaged_copy_is_refused(self):
        bad = self.local / "weatherlab-20261005-030000.db"
        self.local.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"not a database")
        with self.assertRaises(OSError):
            backup.copy_to_folder(bad, self.target, 5)
        self.assertFalse((Path(self.target) / bad.name).exists())

    def test_status(self):
        self.assertFalse(backup.copy_status(self.local, "", datetime(2026, 10, 9))["set"])
        for d in (1, 2):
            self._backup(d)
        backup.catch_up(self.local, self.target, 14)
        for d in (3, 4, 5, 6):
            self._backup(d)
        status = backup.copy_status(self.local, self.target, datetime(2026, 10, 6, 4))
        self.assertTrue(status["reachable"])
        self.assertEqual(status["count"], 2)
        self.assertEqual(status["newest"], datetime(2026, 10, 2, 3))
        self.assertEqual(status["behind_days"], 4)

    def test_unreachable_folder(self):
        self._backup(1)
        status = backup.copy_status(self.local, str(self.root / "missing"), datetime(2026, 10, 1, 4))
        self.assertFalse(status["reachable"])
        self.assertGreaterEqual(status["behind_days"], 1)


class OffsiteHealthTests(unittest.TestCase):
    def _check(self, **facts):
        base = {"poller_alive": True, "disk_free_bytes": 50 * 1024 ** 3, "backup_enabled": True,
                "backup_newest_ts": 1000.0, "copy_folder": "E:\\Backups", "copy_folder_ok": True}
        rows = {c["name"]: c for c in health_check.evaluate(dict(base, **facts), 2000.0)}
        return rows["Second backup folder"]

    def test_three_days_behind_is_an_alert(self):
        row = self._check(copy_behind_days=3)
        self.assertEqual(row["state"], "fail")
        messages, _ = health_check.alert_messages([row], set())
        self.assertEqual(len(messages), 1)

    def test_one_day_behind_is_fine(self):
        self.assertEqual(self._check(copy_behind_days=1)["state"], "ok")

    def test_copy_error_warns(self):
        self.assertEqual(self._check(copy_error="Couldn't copy")["state"], "warn")


if __name__ == "__main__":
    unittest.main()
