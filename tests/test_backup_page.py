"""The Backup page (0.37.25): the list of backups with sizes, and the page's wiring."""
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from weatherlab import backup, nav_groups

ROOT = Path(__file__).resolve().parent.parent


class BackupPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.db = self.dir / "weatherlab.db"
        con = sqlite3.connect(self.db)
        con.execute("CREATE TABLE readings (id INTEGER PRIMARY KEY, ts INTEGER, data TEXT)")
        con.execute("INSERT INTO readings (ts, data) VALUES (1, '{}')")
        con.commit()
        con.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_size_text(self):
        self.assertEqual(backup.size_text(500), "1 KB")
        self.assertEqual(backup.size_text(38 * 1024), "38 KB")
        self.assertEqual(backup.size_text(412 * 1024 * 1024), "412 MB")
        self.assertEqual(backup.size_text(int(1.5 * 1024 ** 3)), "1.5 GB")

    def test_describe_lists_newest_first_with_sizes(self):
        folder = backup.folder_for(self.db)
        first = backup.make_backup(self.db, folder, datetime(2026, 10, 1, 9, 0, 0))
        second = backup.make_backup(self.db, folder, datetime(2026, 10, 2, 9, 0, 0))
        rows = backup.describe(folder)
        self.assertEqual([r["name"] for r in rows], [second.name, first.name])
        self.assertEqual(set(rows[0]), {"name", "when", "size", "bytes", "path"})
        self.assertGreater(rows[0]["bytes"], 0)

    def test_describe_empty_folder(self):
        self.assertEqual(backup.describe(self.dir / "nothing"), [])

    def test_page_is_in_station_and_wired_into_the_app(self):
        self.assertIn("Backup", nav_groups.GROUPS["Station"])  # Tools became part of Station (0.37.40)
        app = (ROOT / "app.py").read_text(encoding="utf-8")
        self.assertIn('"Backup": backup_page', app)
        self.assertIn('"Backup": "💾"', app)

    def test_page_checks_a_backup_before_restoring_it(self):
        source = (ROOT / "weatherlab" / "screens" / "data.py").read_text(encoding="utf-8")
        page = source[source.index("def backup_page"):source.index("# ---------------------------------------------------------------- Export")]
        self.assertLess(page.index("backup.verify(chosen"), page.index("backup.restore("))
        self.assertIn("Yes, restore", page)


if __name__ == "__main__":
    unittest.main()
