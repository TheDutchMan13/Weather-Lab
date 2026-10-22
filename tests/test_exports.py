"""The Export page's date helpers."""

import unittest
from datetime import date
from zoneinfo import ZoneInfo

from weatherlab import exports

UTC = ZoneInfo("UTC")


class MonthBoundsTests(unittest.TestCase):
    def test_october_has_31_days(self):
        self.assertEqual(exports.month_bounds(2026, 10), (date(2026, 10, 1), date(2026, 10, 31)))

    def test_february_in_a_leap_year(self):
        self.assertEqual(exports.month_bounds(2028, 2)[1], date(2028, 2, 29))

    def test_february_in_a_common_year(self):
        self.assertEqual(exports.month_bounds(2026, 2)[1], date(2026, 2, 28))

    def test_december_rolls_into_the_next_year(self):
        self.assertEqual(exports.month_bounds(2026, 12), (date(2026, 12, 1), date(2026, 12, 31)))


class DayRangeTests(unittest.TestCase):
    def test_range_ends_at_the_start_of_the_day_after_the_last_day(self):
        start, end = exports.day_range_ts(date(2026, 10, 1), date(2026, 10, 1), UTC)
        self.assertEqual(end - start, 86400)

    def test_a_month_spans_its_days(self):
        first, last = exports.month_bounds(2026, 10)
        start, end = exports.day_range_ts(first, last, UTC)
        self.assertEqual(end - start, 31 * 86400)

    def test_timezone_moves_the_start(self):
        utc_start = exports.day_start(date(2026, 10, 1), UTC)
        phoenix_start = exports.day_start(date(2026, 10, 1), ZoneInfo("America/Phoenix"))
        self.assertEqual(phoenix_start - utc_start, 7 * 3600)


if __name__ == "__main__":
    unittest.main()
