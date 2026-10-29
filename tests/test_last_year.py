"""Last year's figures for the History page (0.37.32)."""
import unittest
from datetime import date

from weatherlab import last_year


class LastYearTests(unittest.TestCase):
    def test_year_back(self):
        self.assertEqual(last_year.year_back(date(2026, 10, 28)), date(2025, 10, 28))
        self.assertEqual(last_year.year_back(date(2028, 2, 29)), date(2027, 2, 28))

    def test_figures(self):
        rows = [(date(2026, 7, 1), {"tempf_max": 104, "rain_in": 0.0}),
                (date(2026, 7, 2), {"tempf_max": 98, "rain_in": 0.25}),
                (date(2026, 7, 3), {})]
        f = last_year.figures(rows)
        self.assertEqual((f["hottest"], f["hot_days"], f["rain"], f["days"]), (104, 1, 0.25, 3))

    def test_no_data(self):
        f = last_year.figures([])
        self.assertIsNone(f["hottest"])
        self.assertIsNone(last_year.compare([(date(2026, 1, 1), {"tempf_max": 70})], [])["last"])


if __name__ == "__main__":
    unittest.main()
