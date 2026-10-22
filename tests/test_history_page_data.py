"""The Daily history page data helpers: sampled readings and the wind by month."""

import tempfile
import unittest
from datetime import timezone
from pathlib import Path

from weatherlab import storage, wind_rose


class WindPatternTests(unittest.TestCase):
    def _reading(self, direction, speed):
        return {"winddir": direction, "windspeedmph": speed}

    def test_prevailing_direction_for_each_month(self):
        jan = 1767225600  # 1 Jan 2026 00:00 UTC
        items = [
            (jan, self._reading(300, 8.0)),          # WNW, windy
            (jan + 600, self._reading(300, 9.0)),    # WNW, windy
            (jan + 1200, self._reading(90, 6.0)),    # E, windy
            (jan + 1800, self._reading(90, 2.0)),    # E, calm: counted for the average only
        ]
        feb = jan + 31 * 86400
        items.append((feb, self._reading(180, 7.0)))  # S, windy
        out = wind_rose.patterns(items, timezone.utc)
        self.assertEqual(out["total"], 5)
        months = {m["month"]: m for m in out["months"]}
        self.assertEqual(months["Jan 2026"]["from"], "WNW")
        self.assertEqual(months["Jan 2026"]["share"], 66.7)  # 2 of the 3 windy readings
        self.assertEqual(months["Feb 2026"]["from"], "S")
        self.assertEqual(months["Feb 2026"]["share"], 100.0)
        self.assertEqual(months["Jan 2026"]["avg_mph"], 6.2)  # (8 + 9 + 6 + 2) / 4

    def test_month_without_windy_readings_has_no_direction(self):
        items = [(1767225600, self._reading(10, 1.0))]
        out = wind_rose.patterns(items, timezone.utc)
        self.assertIsNone(out["months"][0]["from"])
        self.assertIsNone(out["months"][0]["share"])

    def test_readings_without_direction_are_skipped(self):
        out = wind_rose.patterns([(1767225600, {"windspeedmph": 5.0})], timezone.utc)
        self.assertEqual(out["total"], 0)
        self.assertEqual(out["months"], [])


class SampledReadingsTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self._dir.name) / "test.db")

    def tearDown(self):
        self.db.close()
        self._dir.cleanup()

    def test_one_reading_per_slot(self):
        for ts in range(0, 3000, 30):  # one reading every 30 s for 50 minutes
            self.db.execute("INSERT INTO readings (ts, data) VALUES (?, ?)", (ts, '{"tempf": 70}'))
        self.db.commit()
        rows = storage.readings_sampled(self.db, 0, 3000, every_s=600)
        self.assertEqual([ts for ts, _ in rows], [0, 600, 1200, 1800, 2400])

    def test_archive_is_included(self):
        self.db.execute("INSERT INTO readings_archive (ts, data) VALUES (?, ?)", (3600, '{"winddir": 90}'))
        self.db.commit()
        rows = storage.readings_sampled(self.db, 3000, 4000, every_s=600)
        self.assertEqual(rows, [(3600, {"winddir": 90})])

    def test_range_end_is_exclusive(self):
        self.db.execute("INSERT INTO readings (ts, data) VALUES (?, ?)", (600, "{}"))
        self.db.commit()
        self.assertEqual(storage.readings_sampled(self.db, 0, 600), [])


if __name__ == "__main__":
    unittest.main()
