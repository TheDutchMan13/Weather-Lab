"""The forecast report card (0.37.54)."""
import sqlite3
import unittest
from datetime import date, timezone

from weatherlab import forecast_card, storage


def period(day: bool, start: str, end: str, temp: float, pop=None) -> dict:
    return {"isDaytime": day, "temperature": temp, "unit": "F", "start": start, "end": end, "pop": pop}


PERIODS = [
    period(True, "2026-10-29T06:00:00+00:00", "2026-10-29T18:00:00+00:00", 90, 10),
    period(False, "2026-10-29T18:00:00+00:00", "2026-10-30T06:00:00+00:00", 65),
    period(True, "2026-10-30T06:00:00+00:00", "2026-10-30T18:00:00+00:00", 88, 40),
]


class SnapshotTests(unittest.TestCase):
    def test_night_low_belongs_to_the_morning_it_ends(self):
        self.assertEqual(forecast_card.lows_from_periods(PERIODS, timezone.utc), {"2026-10-30": 65.0})

    def test_overnight_period_after_midnight_is_that_day(self):
        p = [period(False, "2026-10-30T01:00:00+00:00", "2026-10-30T06:00:00+00:00", 60)]
        self.assertEqual(forecast_card.lows_from_periods(p, timezone.utc), {"2026-10-30": 60.0})

    def test_snapshot(self):
        snap = forecast_card.snapshot(PERIODS, timezone.utc)
        self.assertEqual(snap["2026-10-29"], {"high": 90.0, "low": None, "pop": 10.0})
        self.assertEqual(snap["2026-10-30"], {"high": 88.0, "low": 65.0, "pop": 40.0})


class GradeTests(unittest.TestCase):
    def test_pairs_by_days_ahead_and_skips_today(self):
        saved = [("2026-10-01", "2026-10-01", 90, 60, None), ("2026-09-28", "2026-10-01", 95, 55, None),
                 ("2026-10-02", "2026-10-02", 80, 50, None)]
        actuals = {date(2026, 10, 1): (91, 61), date(2026, 10, 2): (80, 50)}
        found = forecast_card.pairs(saved, actuals, today=date(2026, 10, 2))
        self.assertEqual(sorted(found), sorted([(0, "high", 90, 91), (0, "low", 60, 61),
                                                (3, "high", 95, 91), (3, "low", 55, 61)]))

    def test_grade_rows_and_letter(self):
        found = [(1, "high", 90, 91), (1, "high", 90, 95), (1, "low", 60, 60), (1, "low", 60, 61), (3, "high", 99, 90)]
        rows = forecast_card.grade_rows(found)
        one = rows[0]
        self.assertEqual(one["lead"], 1)
        self.assertEqual(one["high"], {"days": 2, "miss": 3.0, "bias": -3.0, "within": 50})
        self.assertEqual(one["low"]["within"], 100)
        self.assertEqual(rows[1]["lead"], 3)
        self.assertIsNone(rows[1]["low"])
        self.assertEqual(forecast_card.letter(rows), ("B", 75, 4))

    def test_letter_falls_back_to_same_day_and_none(self):
        self.assertIsNone(forecast_card.letter([]))
        rows = forecast_card.grade_rows([(0, "high", 90, 99)])
        self.assertEqual(forecast_card.letter(rows), ("F", 0, 1))


class StorageTests(unittest.TestCase):
    def test_first_forecast_of_the_day_is_kept(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE forecast_ahead (made TEXT NOT NULL, date TEXT NOT NULL, high REAL, low REAL, "
                   "pop REAL, PRIMARY KEY (made, date))")
        storage.store_forecast_ahead(db, "2026-10-01", {"2026-10-03": {"high": 90, "low": 60, "pop": 10}})
        storage.store_forecast_ahead(db, "2026-10-01", {"2026-10-03": {"high": 99, "low": 70, "pop": 90}})
        storage.store_forecast_ahead(db, "2026-10-02", {"2026-10-03": {"high": 91, "low": None, "pop": None}})
        self.assertEqual(storage.forecast_ahead(db, "2026-10-01"),
                         [("2026-10-01", "2026-10-03", 90.0, 60.0, 10.0), ("2026-10-02", "2026-10-03", 91.0, None, None)])


if __name__ == "__main__":
    unittest.main()
