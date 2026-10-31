"""My year (0.37.54): compared with the year before, the months that stood out, and the January notice."""
import unittest
from datetime import date, timedelta

from weatherlab import yearly


def year_of(year: int, high: float, rain_every: int, rain: float) -> list:
    out, d = [], date(year, 1, 1)
    while d.year == year:
        hot = high + (10 if d.month == 7 else 0)
        out.append((d, {"tempf_max": hot, "tempf_min": hot - 30, "tempf_avg": hot - 15,
                        "rain_in": rain if d.timetuple().tm_yday % rain_every == 0 else 0.0, "gust_max": 20}))
        d += timedelta(days=1)
    return out


class YearReviewTests(unittest.TestCase):
    def setUp(self):
        self.days = year_of(2025, 90, 10, 0.2) + year_of(2026, 92, 5, 0.1)

    def test_compare_years(self):
        cmp = yearly.compare_years(self.days, 2026)
        self.assertEqual(cmp["rainy_days"][0] - cmp["rainy_days"][1], cmp["rainy_days"][2])
        self.assertGreater(cmp["rainy_days"][2], 0)
        self.assertEqual(cmp["hottest"][2], 2.0)
        self.assertEqual(cmp["days"], (365, 365))
        self.assertIsNone(cmp["through"])
        self.assertIsNone(yearly.compare_years(self.days, 2025))

    def test_a_year_in_progress_is_compared_with_the_same_dates(self):
        days = year_of(2025, 90, 10, 0.2) + [(d, s) for d, s in year_of(2026, 92, 5, 0.1) if d < date(2026, 3, 1)]
        cmp = yearly.compare_years(days, 2026)
        self.assertEqual(cmp["through"], date(2026, 2, 28))
        self.assertEqual(cmp["days"], (59, 59))

    def test_month_extremes(self):
        ext = yearly.month_extremes(self.days, 2026)
        self.assertEqual(ext["warmest"][0], 7)
        self.assertIn(ext["wettest"][0], range(1, 13))
        self.assertLessEqual(ext["driest"][1], ext["wettest"][1])

    def test_short_months_are_left_out(self):
        few = [(date(2026, 3, d), {"tempf_avg": 99, "rain_in": 0.0}) for d in range(1, 6)]
        self.assertEqual(yearly.month_extremes(few, 2026), {})

    def test_announcement(self):
        summary = yearly.year_summary(self.days, 2026)
        text = yearly.year_announcement(summary, 2026, "7.30 in", "102 °F")
        self.assertTrue(text.startswith("Your 2026 weather year is ready: 7.30 in of rain on "))
        self.assertIn("hottest 102 °F on Jul 1", text)
        self.assertIsNone(yearly.year_announcement(None, 2026, "", None))


if __name__ == "__main__":
    unittest.main()
