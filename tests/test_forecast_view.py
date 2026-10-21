"""The Forecast page's overview and 7-day views."""

import unittest
from datetime import datetime, timedelta, timezone

from weatherlab import forecast_view

UTC = timezone.utc
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
LAT, LON = 40.0, -100.0


def hourly_series(hours=30):
    out = []
    for i in range(hours):
        when = NOW + timedelta(hours=i)
        out.append({"start": when.isoformat(), "temperature": 60 + (i % 7), "unit": "F",
                    "short": "Chance Showers" if 4 <= i <= 9 else "Sunny", "pop": 50 if 4 <= i <= 9 else 5})
    return out


def daily_series(days=8):
    out = []
    for d in range(days):
        day = (NOW + timedelta(days=d)).replace(hour=6)
        night = day.replace(hour=18)
        out.append({"start": day.isoformat(), "isDaytime": True, "name": "Day", "temperature": 80 - d,
                    "unit": "F", "short": "Sunny", "pop": 10, "wind": "5 to 15 mph"})
        out.append({"start": night.isoformat(), "isDaytime": False, "name": "Night", "temperature": 60 - d,
                    "unit": "F", "short": "Mostly Clear", "pop": 40 if d == 2 else 0, "wind": "0 to 5 mph"})
    return out


class ConversionTests(unittest.TestCase):
    def test_temperature_converts_between_units(self):
        self.assertEqual(forecast_view.to_shown(32, "F", True), 0)
        self.assertEqual(forecast_view.to_shown(0, "C", False), 32)
        self.assertEqual(forecast_view.to_shown(75, "F", False), 75)
        self.assertIsNone(forecast_view.to_shown(None, "F", True))

    def test_wind_is_converted_to_km_per_hour_when_metric(self):
        self.assertEqual(forecast_view.wind_text("5 to 15 mph", True), "8 to 24 km/h")
        self.assertEqual(forecast_view.wind_text("5 to 15 mph", False), "5 to 15 mph")
        self.assertEqual(forecast_view.wind_text("", True), "")


class OverviewTests(unittest.TestCase):
    def test_takes_every_second_hour_from_now_for_twelve_columns(self):
        picks = forecast_view.overview_hours(hourly_series(), LAT, LON, UTC, NOW)
        self.assertEqual(len(picks), 12)
        self.assertEqual(picks[0]["when"], NOW)
        self.assertEqual(picks[1]["when"], NOW + timedelta(hours=2))

    def test_past_hours_are_left_out(self):
        later = NOW + timedelta(hours=5)
        picks = forecast_view.overview_hours(hourly_series(), LAT, LON, UTC, later)
        self.assertEqual(picks[0]["when"], later)

    def test_empty_forecast_renders_nothing(self):
        self.assertEqual(forecast_view.overview_html([], LAT, LON, UTC, False, 0, NOW), "")

    def test_overview_renders_labels_alerts_and_motion_rules(self):
        out = forecast_view.overview_html(hourly_series(), LAT, LON, UTC, False, 2, NOW)
        self.assertIn("Overview", out)
        self.assertIn("Now", out)
        self.assertIn("Severe weather alerts: 2", out)
        self.assertIn("wl-fc-drop", out)
        self.assertIn("Moon phase", out)

    def test_no_rain_streaks_when_no_hour_is_likely_wet(self):
        dry = [dict(h, pop=5) for h in hourly_series()]
        out = forecast_view.overview_html(dry, LAT, LON, UTC, False, 0, NOW)
        self.assertNotIn('class="wl-fc-drop"', out)

    def test_reduced_motion_stops_the_streaks(self):
        self.assertIn("prefers-reduced-motion", forecast_view.STYLE)


class DaysTests(unittest.TestCase):
    def test_groups_day_and_night_into_one_row_per_date(self):
        rows = forecast_view.days(daily_series(), UTC, NOW.date())
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[0]["name"], "Today")
        self.assertEqual(rows[0]["high"], 80)
        self.assertEqual(rows[0]["low"], 60)

    def test_rain_chance_is_the_higher_of_day_and_night(self):
        rows = forecast_view.days(daily_series(), UTC, NOW.date())
        self.assertEqual(rows[2]["pop"], 40)
        self.assertEqual(rows[0]["pop"], 10)

    def test_days_html_shows_the_week_with_wind_in_user_units(self):
        out = forecast_view.days_html(daily_series(), UTC, True, NOW.date())
        self.assertIn("Next 7 days", out)
        self.assertEqual(out.count('class="wl-fc-day"'), 7)
        self.assertIn("8 to 24 km/h", out)

    def test_empty_periods_render_nothing(self):
        self.assertEqual(forecast_view.days_html([], UTC, False, NOW.date()), "")


if __name__ == "__main__":
    unittest.main()
