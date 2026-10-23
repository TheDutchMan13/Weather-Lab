"""Daily summaries from Ecowitt readings exports (5-minute and 4-hour). Synthetic data only."""

import unittest
from datetime import datetime, timedelta

from weatherlab import readings_daily as rd

HEAD0 = ["Time", "Outdoor", None, "Rainfall Piezo", None, "Wind", "Pressure", "Solar and UVI"]
HEAD1 = [None, "Temperature(℉)", "Humidity(%)", "Daily(in)", "Rain Rate(in/hr)", "Wind Gust(mph)", "Relative(inHg)", "UVI"]


def export(start, end, step_min, temps=None):
    """Rows shaped like an Ecowitt export. The daily rain total starts again at midnight and rises 0.1 in per hour."""
    rows = [list(HEAD0), list(HEAD1)]
    t = start
    while t <= end:
        minutes = t.hour * 60 + t.minute
        temp = (temps or {}).get(t, 80.0)
        rows.append([t.strftime("%Y-%m-%d %H:%M"), temp, 50.0, round(0.1 * minutes / 60, 4), 0.0, 5.0, 29.9, 3.0])
        t += timedelta(minutes=step_min)
    return rows


class ReadingsDailyTests(unittest.TestCase):
    def test_five_minute_day_takes_highs_lows_and_rain(self):
        temps = {datetime(2026, 10, 2, 15, 0): 95.0, datetime(2026, 10, 2, 4, 0): 60.0}
        days = rd.days_from_readings([export(datetime(2026, 10, 1), datetime(2026, 10, 3), 5, temps)])
        day = days[datetime(2026, 10, 2).date()]
        self.assertEqual(day["tempf_max"], 95.0)
        self.assertEqual(day["tempf_min"], 60.0)
        self.assertNotIn("estimated", day)
        # 0.69 in from Oct 1 after 5 PM, then 1.70 in from Oct 2 before 5 PM (the total starts again at midnight)
        self.assertAlmostEqual(day["rain_in"], 2.39, places=2)

    def test_one_minute_day_is_not_estimated(self):
        days = rd.days_from_readings([export(datetime(2026, 10, 1), datetime(2026, 10, 3), 1)])
        self.assertNotIn("estimated", days[datetime(2026, 10, 2).date()])

    def test_four_hour_day_is_marked_estimated(self):
        days = rd.days_from_readings([export(datetime(2026, 10, 1, 1), datetime(2026, 10, 3, 1), 240)])
        self.assertTrue(days[datetime(2026, 10, 2).date()]["estimated"])

    def test_day_is_left_out_when_the_readings_stop_early(self):
        rows = export(datetime(2026, 10, 2, 0, 0), datetime(2026, 10, 2, 12, 0), 5)
        self.assertEqual(rd.days_from_readings([rows]), {})

    def test_day_is_left_out_when_the_readings_start_late(self):
        days = rd.days_from_readings([export(datetime(2026, 9, 1, 1), datetime(2026, 9, 3, 1), 240)])
        self.assertNotIn(datetime(2026, 9, 1).date(), days)

    def test_file_without_the_readings_is_refused(self):
        rows = [["Time", "Outdoor"], [None, "Humidity(%)"], ["2026-10-02 00:00", 70.0]]
        with self.assertRaises(ValueError):
            rd.days_from_readings([rows])


if __name__ == "__main__":
    unittest.main()
