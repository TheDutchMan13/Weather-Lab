"""Hourly packing of old readings (0.37.58): nothing lost, reads unchanged, file smaller."""

import json
import os
import socket
import sqlite3
import tempfile
import unittest
import urllib.error
from pathlib import Path

from weatherlab import backup, plain_errors, storage


def _fill(db, start, hours, step=30):
    rows = []
    for i in range(hours * 3600 // step):
        ts = start + i * step
        rows.append((ts, json.dumps({"tempf": 60 + (i % 50) / 10, "windspeedmph": i % 7, "winddir": (i * 13) % 360}), "gw2000"))
    db.executemany("INSERT INTO readings (ts, data, source) VALUES (?, ?, ?)", rows)
    db.commit()
    return len(rows)


class PackingTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "w.db"
        self.db = storage.connect(self.path)
        self.start = 1_700_000_000 - (1_700_000_000 % 3600)
        self.n = _fill(self.db, self.start, 48)

    def tearDown(self):
        self.db.close()
        self.dir.cleanup()

    def test_nothing_lost_and_reads_unchanged(self):
        end = self.start + 48 * 3600
        before = storage.readings_between(self.db, self.start, end)
        sampled = storage.readings_sampled(self.db, self.start, end, 600)
        hourly = storage.readings_sampled(self.db, self.start, end, 3600)
        temps = storage.series(self.db, "tempf", self.start, end, 1800)
        moved = storage.pack_before(self.db, self.start + 30 * 3600 + 90)  # only whole hours before the cutoff
        self.assertEqual(moved, 30 * 120)
        self.assertEqual(storage.reading_count(self.db), self.n)
        self.assertEqual(storage.readings_between(self.db, self.start, end), before)
        self.assertEqual(storage.readings_sampled(self.db, self.start, end, 600), sampled)
        self.assertEqual(storage.readings_sampled(self.db, self.start, end, 3600), hourly)
        self.assertEqual(storage.series(self.db, "tempf", self.start, end, 1800), temps)
        self.assertEqual(len(storage.reading_times(self.db, self.start, end)), self.n)

    def test_packing_twice_merges_and_late_readings_join_their_hour(self):
        storage.pack_before(self.db, self.start + 10 * 3600)
        late = self.start + 3600 + 15  # a reading imported later into an hour that is already packed
        self.db.execute("INSERT INTO readings (ts, data) VALUES (?, ?)", (late, json.dumps({"tempf": 99})))
        self.db.commit()
        storage.pack_before(self.db, self.start + 10 * 3600)
        self.assertEqual(storage.reading_count(self.db), self.n + 1)
        got = dict(storage.readings_between(self.db, late, late + 1))
        self.assertEqual(got[late]["tempf"], 99)

    def test_archive_table_is_packed_too(self):
        storage.archive_before(self.db, self.start + 5 * 3600)
        storage.pack_before(self.db, self.start + 5 * 3600)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM readings_archive").fetchone()[0], 0)
        self.assertEqual(storage.reading_count(self.db), self.n)

    def test_file_shrinks_after_vacuum(self):
        size = os.path.getsize(self.path)
        storage.pack_before(self.db, self.start + 48 * 3600)
        self.db.execute("VACUUM")
        self.assertLess(os.path.getsize(self.path), size / 4)

    def test_backup_check_counts_packed_readings(self):
        storage.pack_before(self.db, self.start + 24 * 3600)
        self.db.commit()
        ok, text = backup.verify(self.path)
        self.assertTrue(ok)
        self.assertIn(f"{self.n:,}", text)


class PlainErrorTests(unittest.TestCase):
    def test_no_class_names(self):
        cases = [urllib.error.URLError(socket.timeout()), TimeoutError(), urllib.error.URLError(socket.gaierror()),
                 ConnectionRefusedError(), urllib.error.HTTPError("u", 401, "x", {}, None), ValueError("x")]
        for exc in cases:
            text = plain_errors.station("192.168.1.9", exc)
            self.assertNotRegex(text, r"Error\b|URLError|timeout\(")
            self.assertIn("192.168.1.9", text)
        self.assertIn("didn't answer in time", plain_errors.why(urllib.error.URLError(socket.timeout())))
        self.assertIn("refused the key", plain_errors.service("AirNow", urllib.error.HTTPError("u", 403, "x", {}, None)))


if __name__ == "__main__":
    unittest.main()
