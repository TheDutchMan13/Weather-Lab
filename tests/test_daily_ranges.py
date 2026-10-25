"""The Daily page's ranges: one day, or several days together (0.37.12)."""
import unittest

from weatherlab import daily_ranges


class DailyRangeTests(unittest.TestCase):
    def test_choices_in_order(self):
        self.assertEqual(list(daily_ranges.DAILY_RANGES), ["1 day", "7 days", "30 days", "All"])

    def test_one_day_is_the_day_view_others_are_periods(self):
        self.assertTrue(daily_ranges.is_day_view("1 day"))
        self.assertFalse(daily_ranges.is_day_view("7 days"))
        self.assertEqual(daily_ranges.DAILY_RANGES["7 days"], 7)
        self.assertEqual(daily_ranges.DAILY_RANGES["30 days"], 30)
        self.assertIsNone(daily_ranges.DAILY_RANGES["All"])
