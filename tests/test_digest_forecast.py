"""Morning summary text and forecast accuracy. Synthetic data only."""

import unittest
from datetime import date
from zoneinfo import ZoneInfo

from weatherlab import digest, forecast_check as fc


class DigestTests(unittest.TestCase):
    def test_summary_line_in_us_units(self):
        line = digest.text("Oct 20", {"tempf_max": 95.3, "tempf_min": 71.2, "rain_in": 0.0, "sun_hours": 10.4}, False)
        self.assertTrue(line.startswith("Yesterday (Oct 20):"))
        self.assertIn("high 95", line)
        self.assertIn("low 71", line)
        self.assertIn("sun 10.4 hours", line)

    def test_metric_units(self):
        line = digest.text("Oct 20", {"tempf_max": 95.0, "tempf_min": 71.0}, True)
        self.assertIn("high 35", line)

    def test_empty_summary_gives_no_line(self):
        self.assertEqual(digest.text("Oct 20", {}, False), "")


class ForecastTests(unittest.TestCase):
    def test_daytime_highs_by_local_date_and_in_fahrenheit(self):
        tz = ZoneInfo("America/Phoenix")
        periods = [
            {"isDaytime": True, "temperature": 97, "unit": "F", "start": "2026-10-22T06:00:00-07:00"},
            {"isDaytime": False, "temperature": 70, "unit": "F", "start": "2026-10-22T18:00:00-07:00"},
            {"isDaytime": True, "temperature": 30, "unit": "C", "start": "2026-10-23T06:00:00-07:00"},
        ]
        self.assertEqual(fc.highs_from_periods(periods, tz), {"2026-10-22": 97, "2026-10-23": 86.0})

    def test_compare_and_accuracy(self):
        forecasts = {date(2026, 10, 20): 95.0, date(2026, 10, 21): 90.0, date(2026, 10, 22): 99.0}
        actuals = {date(2026, 10, 20): 93.0, date(2026, 10, 21): 94.0}
        rows = fc.compare(forecasts, actuals)
        self.assertEqual([r[0] for r in rows], [date(2026, 10, 21), date(2026, 10, 20)])
        self.assertEqual(rows[0][3], -4.0)
        self.assertEqual(fc.accuracy(rows), {"days": 2, "mae": 3.0, "bias": -1.0})
        self.assertEqual(fc.accuracy([]), {"days": 0, "mae": None, "bias": None})


if __name__ == "__main__":
    unittest.main()
