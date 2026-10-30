"""The Daily page's ranges: one day, or several days together (0.37.12)."""
import unittest

from weatherlab import daily_ranges


class DailyRangeTests(unittest.TestCase):
    def test_choices_in_order(self):
        self.assertEqual(list(daily_ranges.DAILY_RANGES), ["1 day", "Several days"])

    def test_one_day_is_the_day_view_others_are_periods(self):
        self.assertTrue(daily_ranges.is_day_view("1 day"))
        self.assertFalse(daily_ranges.is_day_view("Several days"))
