"""The backup test: a good backup passes, and a damaged or wrong file is reported, not crashed on."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from weatherlab import backup


class VerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def make_db(self, name, rows):
        path = self.tmp / name
        con = sqlite3.connect(path)
        con.execute("CREATE TABLE readings (id INTEGER PRIMARY KEY, ts INTEGER, data TEXT)")
        con.executemany("INSERT INTO readings (ts, data) VALUES (?, 'x')", [(i,) for i in range(rows)])
        con.commit()
        con.close()
        return path

    def test_good_backup_passes_and_counts(self):
        ok, text = backup.verify(self.make_db("good.db", 12))
        self.assertTrue(ok)
        self.assertIn("12 readings", text)

    def test_empty_backup_passes_with_a_note(self):
        ok, text = backup.verify(self.make_db("empty.db", 0))
        self.assertTrue(ok)
        self.assertIn("no readings", text)

    def test_missing_file(self):
        ok, text = backup.verify(self.tmp / "nope.db")
        self.assertFalse(ok)
        self.assertIn("missing", text)

    def test_wrong_database_is_refused(self):
        path = self.tmp / "other.db"
        sqlite3.connect(path).execute("CREATE TABLE things (a)").connection.close()
        ok, text = backup.verify(path)
        self.assertFalse(ok)
        self.assertIn("not a Weather Lab database", text)

    def test_damaged_file_is_reported(self):
        path = self.make_db("bad.db", 50)
        data = bytearray(path.read_bytes())
        data[4096:4096 * 3] = b"\x00" * (4096 * 2)
        path.write_bytes(bytes(data))
        ok, _ = backup.verify(path)
        self.assertFalse(ok)

    def test_verify_changes_nothing(self):
        path = self.make_db("keep.db", 3)
        before = path.read_bytes()
        backup.verify(path)
        self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
