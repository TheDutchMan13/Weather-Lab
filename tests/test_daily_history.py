"""Daily summaries, rollup, records, and rain totals. Uses a temporary SQLite file, no network.

Run with:  python -m unittest discover -s tests -v
"""

import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from weatherlab import daily, history, storage

TZ = ZoneInfo("America/Phoenix")
DAY = date(2026, 10, 10)
LAT, LON, ELEV = 33.4, -112.46, 330.0


def _day_readings(day: date, temps: list[float]) -> list[tuple[int, dict]]:
    """One reading every 60 seconds across the local day, cycling through the given temperatures."""
    start = int(datetime(day.year, day.month, day.day, tzinfo=TZ).timestamp())
    return [(start + i * 60, {"tempf": temps[i % len(temps)], "humidity": 40.0, "windspeedmph": 2.0,
                              "windgustmph": 4.0, "dailyrainin": 0.1 if i > 500 else 0.0})
            for i in range(0, 1440)]


class DailyTests(unittest.TestCase):
    def test_summary_has_expected_extremes(self):
        rows = _day_readings(DAY, [70.0, 95.0, 88.0])
        summary, hours = daily.summarize_day(rows, LAT, LON, ELEV, TZ)
        self.assertEqual(summary["tempf_max"], 95.0)
        self.assertEqual(summary["tempf_min"], 70.0)
        self.assertEqual(summary["rain_in"], 0.1)
        self.assertEqual(summary["humidity_min"], 40.0)
        self.assertGreater(hours, 23.0)

    def test_too_few_readings_gives_no_summary(self):
        summary, _ = daily.summarize_day(_day_readings(DAY, [70.0])[:5], LAT, LON, ELEV, TZ)
        self.assertIsNone(summary)

    def test_no_sun_at_night(self):
        midnight = int(datetime(2026, 10, 10, 0, 0, tzinfo=TZ).timestamp())
        self.assertEqual(daily._solar_max(midnight, LAT, LON, ELEV, TZ), 0.0)

    def test_sun_at_noon(self):
        noon = int(datetime(2026, 10, 10, 12, 0, tzinfo=TZ).timestamp())
        self.assertGreater(daily._solar_max(noon, LAT, LON, ELEV, TZ), 500)


class RollupAndHistoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self._tmp.name) / "test.db")
        for ts, reading in _day_readings(DAY, [70.0, 95.0, 88.0]):
            storage.store_reading(self.db, reading, ts)

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_rollup_writes_finished_day_only(self):
        written = daily.rollup_days(self.db, [DAY, DAY + timedelta(days=1)], LAT, LON, ELEV, TZ,
                                    today=DAY + timedelta(days=1))
        self.assertEqual(written, [DAY.isoformat()])
        rows = history.all_daily(self.db)
        self.assertEqual(rows[0][0], DAY)
        self.assertEqual(rows[0][1]["tempf_max"], 95.0)

    def test_records_and_rain_totals(self):
        daily.rollup_days(self.db, [DAY], LAT, LON, ELEV, TZ, today=DAY + timedelta(days=1))
        recs = {r["label"]: r for r in history.records(self.db)}
        self.assertEqual(recs["Highest temperature"]["value"], 95.0)
        self.assertEqual(recs["Highest temperature"]["date"], DAY)
        totals = history.rain_totals(self.db, DAY + timedelta(days=1), live_today_in=0.3)
        self.assertEqual(totals["today"], 0.3)
        self.assertEqual(totals["last_7_days"], 0.4)  # 0.1 from the finished day + 0.3 today

    def test_empty_history(self):
        self.assertEqual(history.records(self.db), [])
        totals = history.rain_totals(self.db, DAY, live_today_in=None)
        self.assertEqual(totals["this_year"], 0.0)


if __name__ == "__main__":
    unittest.main()
