"""Rain chance check and today compared with yesterday. Synthetic data only."""

import unittest
from datetime import date
from zoneinfo import ZoneInfo

from weatherlab import forecast_check as fc, history_compare as hc


class RainCheckTests(unittest.TestCase):
    def test_chance_of_rain_by_day_and_summary(self):
        tz = ZoneInfo("America/Phoenix")
        periods = [{"isDaytime": True, "pop": 60, "start": "2026-10-22T06:00:00-07:00"},
                   {"isDaytime": False, "pop": 80, "start": "2026-10-22T18:00:00-07:00"},
                   {"isDaytime": True, "pop": 10, "start": "2026-10-23T06:00:00-07:00"}]
        pops = fc.pops_from_periods(periods, tz)
        self.assertEqual(pops, {"2026-10-22": 60.0, "2026-10-23": 10.0})
        combined = fc.combine({"2026-10-22": 97.0}, pops)
        self.assertEqual(combined, {"2026-10-22": {"high": 97.0, "pop": 60.0}})
        summary = fc.rain_summary({date(2026, 10, 22): 60.0, date(2026, 10, 23): 10.0},
                                  {date(2026, 10, 22): True, date(2026, 10, 23): False})
        self.assertEqual(summary, {"wet_days": 1, "wet_rained": 1, "dry_days": 1, "dry_rained": 0})


class TodayVsYesterdayTests(unittest.TestCase):
    def test_highest_so_far_today_and_yesterday(self):
        today = [{"tempf": 92}, {"tempf": 90, "dailyrainin": 0.12}]
        yesterday = [{"tempf": 95, "windgustmph": 22}]
        out = hc.by_this_time(today, yesterday)
        self.assertEqual(out["tempf"], (92, 95))
        self.assertEqual(out["dailyrainin"], (0.12, None))
        self.assertEqual(out["windgustmph"], (None, 22))


if __name__ == "__main__":
    unittest.main()
