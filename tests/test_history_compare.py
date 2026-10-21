"""Period comparison totals and the estimate flag on records. Synthetic data only."""

import unittest
from datetime import date, timedelta

from weatherlab import history, history_compare as hc


class PeriodStatsTests(unittest.TestCase):
    def test_totals_and_averages(self):
        start = date(2026, 9, 1)
        rows = [(start + timedelta(days=i), {"tempf_max": 90 + i, "tempf_min": 60 + i,
                                              "rain_in": 0.5 if i % 2 == 0 else 0.0, "sun_hours": 10})
                for i in range(4)]
        s = hc.period_stats(rows)
        self.assertEqual(s["days"], 4)
        self.assertEqual(s["avg_high"], 91.5)
        self.assertEqual(s["avg_low"], 61.5)
        self.assertEqual(s["max_high"], 93)
        self.assertEqual(s["min_low"], 60)
        self.assertEqual(s["rain_total"], 1.0)
        self.assertEqual(s["rain_days"], 2)
        self.assertEqual(s["sun_hours"], 40)

    def test_empty_period_has_no_averages(self):
        s = hc.period_stats([])
        self.assertEqual(s["days"], 0)
        self.assertIsNone(s["avg_high"])
        self.assertEqual(s["rain_total"], 0.0)

    def test_change(self):
        self.assertEqual(hc.change(95, 90), 5)
        self.assertIsNone(hc.change(None, 90))


class RecordsEstimateTests(unittest.TestCase):
    def test_record_from_an_estimated_day_is_flagged(self):
        class FakeDb:
            def execute(self, sql, params=()):
                rows = [("2026-07-01", '{"tempf_max": 99, "tempf_min": 70}'),
                        ("2026-07-02", '{"tempf_max": 104, "tempf_min": 72, "estimated": true}')]
                return _Cursor(rows)

        items = {r["label"]: r for r in history.records(FakeDb())}
        self.assertEqual(items["Highest temperature"]["value"], 104)
        self.assertTrue(items["Highest temperature"]["estimated"])
        self.assertFalse(items["Lowest temperature"]["estimated"])


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


if __name__ == "__main__":
    unittest.main()
