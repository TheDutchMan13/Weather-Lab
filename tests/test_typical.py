"""Typical weather for a date: the days within a week of it in other years. Synthetic data only."""

import unittest
from datetime import date

from weatherlab import history_compare as hc


class TypicalTests(unittest.TestCase):
    def test_averages_nearby_days_in_other_years_only(self):
        days = [(date(2023, 10, 21), {"tempf_max": 90, "tempf_min": 60}),
                (date(2024, 10, 21), {"tempf_max": 92, "tempf_min": 62}),
                (date(2025, 10, 21), {"tempf_max": 94, "tempf_min": 64}),
                (date(2025, 10, 15), {"tempf_max": 100, "tempf_min": 70}),
                (date(2025, 10, 1), {"tempf_max": 50, "tempf_min": 40}),
                (date(2026, 10, 21), {"tempf_max": 110, "tempf_min": 80})]
        self.assertEqual(hc.typical(days, date(2026, 10, 21)), {"high": 94.0, "low": 64.0, "years": 3})


if __name__ == "__main__":
    unittest.main()
