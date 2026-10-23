"""Ecowitt exports of any span are stored as readings. Synthetic data only."""

import tempfile
from pathlib import Path
import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from tests.test_readings_daily import export
from weatherlab import ecowitt_import as ei, storage

TZ = ZoneInfo("America/Phoenix")


def db():
    return storage.connect(Path(tempfile.mkdtemp()) / "t.db")


class AnyRangeTests(unittest.TestCase):
    def found(self, rows):
        ei.read_xlsx = lambda source, rows=rows: rows
        return ei.readings_from_files([object()], TZ)

    def test_partial_day_file_gives_readings(self):
        found, widest = self.found(export(datetime(2026, 10, 22, 0, 0), datetime(2026, 10, 22, 23, 55), 5))
        self.assertEqual(len(found), 288)
        self.assertEqual(widest, 5)
        reading, _ = next(iter(found.values()))
        self.assertEqual(reading["tempf"], 80.0)
        self.assertEqual(reading["baromrelin"], 29.9)

    def test_store_adds_readings_and_builds_the_day(self):
        found, widest = self.found(export(datetime(2026, 10, 20, 0, 0), datetime(2026, 10, 21, 23, 55), 5))
        d = db()
        added, skipped, days = ei.store_readings(d, found, widest, TZ)
        self.assertEqual((added, skipped, days), (576, 0, 2))
        self.assertEqual(d.execute("SELECT COUNT(*) FROM daily").fetchone()[0], 2)

    def test_readings_already_stored_are_skipped(self):
        found, widest = self.found(export(datetime(2026, 10, 20, 0, 0), datetime(2026, 10, 20, 1, 0), 30))
        d = db()
        ts = int(datetime(2026, 10, 20, 0, 10, tzinfo=TZ).timestamp())
        d.execute("INSERT INTO readings (ts, data, source) VALUES (?, '{}', 'x')", (ts,))
        added, skipped, _ = ei.store_readings(d, found, widest, TZ)
        self.assertEqual((added, skipped), (2, 1))

    def test_importing_twice_adds_nothing(self):
        found, widest = self.found(export(datetime(2026, 10, 20, 0, 0), datetime(2026, 10, 20, 6, 0), 30))
        d = db()
        ei.store_readings(d, found, widest, TZ)
        added, _, _ = ei.store_readings(d, found, widest, TZ)
        self.assertEqual(added, 0)

    def test_no_complete_day_is_not_an_error(self):
        ei.read_xlsx = lambda source: export(datetime(2026, 10, 22, 0, 0), datetime(2026, 10, 22, 12, 0), 5)
        self.assertEqual(ei.days_from_files([object()]), {})


if __name__ == "__main__":
    unittest.main()
