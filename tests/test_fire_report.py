"""Fire weather and PDF report tests. Offline; the PDF test is skipped if reportlab isn't installed."""

import unittest
from datetime import date, datetime
from zoneinfo import ZoneInfo

from weatherlab import fire

PHOENIX = ZoneInfo("America/Phoenix")


class FireTests(unittest.TestCase):
    def test_indices_are_in_range(self):
        c = fire.roll_day(fire.DEFAULT_CODES, fire.f_to_c(90), 25, 12 * fire.MPH_TO_KMH, 0.0, 7)
        self.assertTrue(0 <= c["ffmc"] <= 101)
        self.assertGreaterEqual(c["dmc"], 0)
        self.assertGreaterEqual(c["dc"], 0)
        self.assertGreater(c["fwi"], 0)

    def test_rain_makes_fuels_wetter(self):
        dry = fire.roll_day(fire.DEFAULT_CODES, 25, 40, 10, 0.0, 7)
        wet = fire.roll_day(fire.DEFAULT_CODES, 25, 40, 10, 20.0, 7)
        self.assertLess(wet["ffmc"], dry["ffmc"])
        self.assertLess(wet["dmc"], dry["dmc"])

    def test_starting_codes(self):
        self.assertEqual(fire.starting_codes("2026-10-20", {}), fire.DEFAULT_CODES)
        carry = {"date": "2026-10-19", "today": {"ffmc": 90, "dmc": 20, "dc": 100}}
        self.assertEqual(fire.starting_codes("2026-10-20", carry), {"ffmc": 90, "dmc": 20, "dc": 100})
        same_day = {"date": "2026-10-20", "base": {"ffmc": 80, "dmc": 10, "dc": 50},
                    "today": {"ffmc": 99, "dmc": 99, "dc": 99}}
        self.assertEqual(fire.starting_codes("2026-10-20", same_day), {"ffmc": 80, "dmc": 10, "dc": 50})

    def test_days_since_rain(self):
        today = date(2026, 10, 20)
        rows = [("2026-10-18", 0.0), ("2026-10-15", 0.5)]
        self.assertEqual(fire.days_since_rain(rows, today, 0.0), 5)  # last wet day was the 15th
        self.assertEqual(fire.days_since_rain(rows, today, 0.2), 0)
        self.assertEqual(fire.days_since_rain([], today, 0.0), 30)

    def test_forecast_uses_hour_nearest_1pm_and_highest_wind(self):
        hourly = [
            {"start": "2026-10-21T09:00:00-07:00", "temperature": 80, "unit": "F", "humidity": 30, "wind": "5 to 10 mph"},
            {"start": "2026-10-21T13:00:00-07:00", "temperature": 95, "unit": "F", "humidity": 20, "wind": "8 to 12 mph"},
            {"start": "2026-10-21T15:00:00-07:00", "temperature": 99, "unit": "F", "humidity": 15, "wind": "20 mph"},
        ]
        out = fire.forecast_noon(hourly, PHOENIX)[date(2026, 10, 21)]
        self.assertEqual(out["temp_f"], 95.0)
        self.assertEqual(out["wind_mph"], 12.0)

    def test_forecast_skips_incomplete_hours(self):
        hourly = [{"start": "2026-10-21T13:00:00-07:00", "temperature": 95, "unit": "F", "humidity": None, "wind": "5 mph"}]
        self.assertEqual(fire.forecast_noon(hourly, PHOENIX), {})

    def test_build_carries_codes_to_next_day(self):
        obs = {"temp_f": 95, "humidity": 20, "wind_mph": 8, "rain_in": 0.0, "days_since_rain": 3}
        first = fire.build(obs, {}, datetime(2026, 10, 20, 13, 0, tzinfo=PHOENIX), {})
        self.assertEqual(first["date"], "2026-10-20")
        self.assertEqual(len(first["forecast"]), 1)
        self.assertGreaterEqual(first["fwi"], 0)
        second = fire.build(obs, first, datetime(2026, 10, 21, 13, 0, tzinfo=PHOENIX), {})
        self.assertEqual(second["base"], first["today"])


class ReportTests(unittest.TestCase):
    def test_daily_pdf_is_a_pdf(self):
        try:
            from weatherlab import report
        except ImportError:
            self.skipTest("reportlab is not installed")
        summary = {"tempf_max": 95.0, "tempf_min": 70.0, "tempf_avg": 84.0, "rain_in": 0.0,
                   "wind_run_mi": 120.5, "gust_max": 28.0, "sun_hours": 11.2,
                   "humidity_min": 12.0, "humidity_max": 60.0}
        current = {"tempf": 88.4, "humidity": 22, "windspeedmph": 5.0, "windgustmph": 9.0, "dailyrainin": 0.0}
        pdf = report.daily_pdf("2026-10-20", summary, current)
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_daily_pdf_without_current_or_values(self):
        try:
            from weatherlab import report
        except ImportError:
            self.skipTest("reportlab is not installed")
        self.assertTrue(report.daily_pdf("2026-10-20", {}, None).startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
