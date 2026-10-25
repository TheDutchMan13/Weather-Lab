"""Time in each heat level and dangerous days for the Heat safety page (0.37.15)."""
import unittest
from datetime import date

from weatherlab import heat_safety as hs


class Hours(unittest.TestCase):
    def test_each_reading_counts_until_the_next(self):
        series = [(0, 70.0), (1800, 95.0), (3600, 110.0), (5400, 110.0)]
        h = hs.hours_by_level(series)
        self.assertAlmostEqual(h["Comfortable"], 0.5)
        self.assertAlmostEqual(h["Extreme caution"], 0.5)
        self.assertAlmostEqual(h["Danger"], 0.5)
        self.assertAlmostEqual(hs.danger_hours(h), 0.5)

    def test_long_gap_is_capped(self):
        h = hs.hours_by_level([(0, 70.0), (36000, 70.0)])
        self.assertAlmostEqual(h["Comfortable"], 0.5)

    def test_missing_values_skipped_and_empty(self):
        self.assertEqual(sum(hs.hours_by_level([]).values()), 0)
        h = hs.hours_by_level([(0, None), (600, 85.0), (1200, 85.0)])
        self.assertAlmostEqual(h["Caution"], 600 / 3600)

    def test_names_order_and_colours(self):
        self.assertEqual(hs.LEVEL_NAMES[0], "Comfortable")
        self.assertEqual(hs.LEVEL_NAMES[-1], "Extreme danger")
        self.assertEqual(set(hs.LEVEL_NAMES), set(hs.LEVEL_COLOURS))


class Days(unittest.TestCase):
    def test_dangerous_days_worst_first(self):
        days = [(date(2026, 6, 1), {"heat_index_max": 104.0}), (date(2026, 6, 2), {"heat_index_max": 103.9}),
                (date(2026, 6, 3), {"heat_index_max": 126.0}), (date(2026, 6, 4), {})]
        out = hs.dangerous_days(days)
        self.assertEqual([(d.day, lvl) for d, _, lvl in out], [(3, "Extreme danger"), (1, "Danger")])


if __name__ == "__main__":
    unittest.main()
