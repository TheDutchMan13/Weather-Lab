"""Freeze warnings: forecast nights at or below the threshold, starting soon. Synthetic data only."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from weatherlab import forecast_check as fc


class FrostTests(unittest.TestCase):
    def test_only_cold_nights_starting_soon(self):
        tz = ZoneInfo("America/Phoenix")
        now = datetime(2026, 10, 21, 19, 0, tzinfo=tz)
        periods = [
            {"isDaytime": False, "temperature": 38, "unit": "F", "start": "2026-10-21T18:00:00-07:00"},
            {"isDaytime": False, "temperature": 34, "unit": "F", "start": "2026-10-22T18:00:00-07:00"},
            {"isDaytime": True, "temperature": 20, "unit": "F", "start": "2026-10-22T06:00:00-07:00"},
            {"isDaytime": False, "temperature": 30, "unit": "F", "start": "2026-10-28T18:00:00-07:00"},
        ]
        self.assertEqual(fc.frost_nights(periods, tz, now, 36.0), [("2026-10-22", 34.0)])

    def test_celsius_low_is_converted(self):
        tz = ZoneInfo("America/Phoenix")
        now = datetime(2026, 10, 21, 19, 0, tzinfo=tz)
        periods = [{"isDaytime": False, "temperature": 1, "unit": "C", "start": "2026-10-22T18:00:00-07:00"}]
        self.assertEqual(fc.frost_nights(periods, tz, now, 36.0), [("2026-10-22", 33.8)])


if __name__ == "__main__":
    unittest.main()
