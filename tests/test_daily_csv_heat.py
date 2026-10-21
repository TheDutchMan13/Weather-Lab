"""Daily summaries as CSV, and hot days by year. Synthetic data only."""

import unittest
from datetime import date

from weatherlab import history, history_compare as hc


class DailyCsvTests(unittest.TestCase):
    def test_header_and_values(self):
        rows = [(date(2026, 10, 20), {"tempf_max": 95.0, "tempf_min": 71.0, "tempf_avg": 84.2, "rain_in": 0.0,
                                      "gust_max": 22.0, "wind_run_mi": 120.5, "sun_hours": 10.3,
                                      "humidity_min": 12, "humidity_max": 60})]
        lines = history.daily_csv(rows).strip().splitlines()
        self.assertEqual(lines[0], "date,high_f,low_f,average_f,rain_in,gust_max_mph,wind_run_mi,sun_hours,"
                                   "humidity_min_pct,humidity_max_pct")
        self.assertEqual(lines[1], "2026-10-20,95.0,71.0,84.2,0.0,22.0,120.5,10.3,12,60")

    def test_missing_values_are_empty(self):
        lines = history.daily_csv([(date(2026, 10, 21), {})]).strip().splitlines()
        self.assertEqual(lines[1], "2026-10-21" + "," * 9)


class HeatDaysTests(unittest.TestCase):
    def test_counts_days_at_each_level(self):
        days = [(date(2025, 7, 1), {"tempf_max": 99}), (date(2025, 7, 2), {"tempf_max": 100}),
                (date(2025, 7, 3), {"tempf_max": 111}), (date(2024, 7, 1), {})]
        self.assertEqual(hc.heat_days_by_year(days), {2025: {100: 2, 110: 1}})


if __name__ == "__main__":
    unittest.main()
