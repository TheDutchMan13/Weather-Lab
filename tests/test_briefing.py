"""The daily briefing (0.37.26)."""
import unittest
from datetime import date, timedelta
from unittest import mock

from tests.test_api_pages import ApiHelpers
from weatherlab import api_pages, briefing


class BriefingHelperTests(unittest.TestCase):
    def test_streak(self):
        today = date(2026, 7, 10)
        highs = {today - timedelta(days=n): 104 for n in (1, 2, 3)}
        highs[today - timedelta(days=4)] = 98
        self.assertEqual(briefing.hot_streak(highs, today), 3)
        self.assertEqual(briefing.hot_streak(highs, today, today_high=101), 4)
        self.assertEqual(briefing.hot_streak({}, today), 0)

    def test_difference(self):
        self.assertEqual(briefing.difference(100, 96, "°F", "yesterday"), "4°F warmer than yesterday")
        self.assertEqual(briefing.difference(90, 95, "°F", "last year"), "5°F cooler than last year")
        self.assertEqual(briefing.difference(90, 90, "°F", "yesterday"), "the same as yesterday")
        self.assertIsNone(briefing.difference(None, 90, "°F", "yesterday"))

    def test_headline(self):
        text = briefing.headline(104, "°F", "Sunny", 10, 1, "Danger")
        self.assertEqual(text, "A high near 104°F, sunny. 10% chance of rain; heat safety: danger; 1 weather alert in effect.")
        self.assertEqual(briefing.headline(None, "°F", None, None, 0, None), "No forecast yet today.")

    def test_worth_knowing(self):
        lines = briefing.worth_knowing(["Heat Advisory"], "05:30", "19:40", "dry and comfortable", 41, 3, "steady", 0)
        self.assertEqual(lines[0], "Heat Advisory")
        self.assertIn("3 days in a row at 100°F or more.", lines)
        self.assertIn("Sunrise 05:30, sunset 19:40.", lines)
        self.assertIn("Pressure is steady.", lines)


class BriefingApiTests(ApiHelpers, unittest.TestCase):
    def test_endpoint_without_forecast(self):
        self.seed_days()
        self.seed_readings()
        with mock.patch.object(api_pages, "forecast", return_value={"available": False}):
            code, body = self.get("/api/v1/briefing")
        self.assertEqual(code, 200)
        labels = [t["label"] for t in body["tiles"]]
        self.assertEqual(labels[:3], ["Expected high", "Same day last year", "Low last night"])
        self.assertEqual(body["tiles"][0]["value"], 90)   # no forecast: today's observed high
        self.assertFalse(body["forecast"])
        self.assertTrue(body["headline"])

    def test_endpoint_with_forecast_and_alert(self):
        self.seed_days()
        self.seed_readings()
        fc = {"available": True, "periods": [{"name": "Today", "is_day": True, "temp": 108, "short": "Sunny",
                                              "detail": "", "rain_chance": 5, "wind": "S 10 mph"}],
              "alerts": [{"event": "Excessive Heat Warning", "severity": "Severe", "headline": "until 8 PM"}]}
        with mock.patch.object(api_pages, "forecast", return_value=fc):
            _, body = self.get("/api/v1/briefing")
        self.assertEqual(body["tiles"][0]["value"], 108)
        self.assertIn("Excessive Heat Warning: until 8 PM", body["notes"])
        self.assertIn("1 weather alert in effect", body["headline"])

    def test_empty_database(self):
        with mock.patch.object(api_pages, "forecast", return_value={"available": False}):
            code, body = self.get("/api/v1/briefing")
        self.assertEqual(code, 200)
        self.assertIsNone(body["tiles"][0]["value"])


if __name__ == "__main__":
    unittest.main()


class MorningNotificationTests(unittest.TestCase):
    def test_notification_text(self):
        data = {"headline": "A high near 104°F, sunny.",
                "tiles": [{"label": "Expected high", "note": "4°F warmer than yesterday"}],
                "notes": ["Excessive Heat Warning: until 8 PM", "Sunrise 05:30, sunset 19:40."]}
        self.assertEqual(briefing.notification(data),
                         "A high near 104°F, sunny. 4°F warmer than yesterday. Excessive Heat Warning: until 8 PM.")

    def test_notification_without_extras(self):
        self.assertEqual(briefing.notification({"headline": "No forecast yet today.", "tiles": [], "notes": ["Sunrise 05:30, sunset 19:40."]}),
                         "No forecast yet today.")

    def test_due_once_a_day_after_the_hour(self):
        today = date(2026, 10, 26)
        self.assertFalse(briefing.due(6, 7, None, today, False))
        self.assertTrue(briefing.due(7, 7, None, today, False))
        self.assertFalse(briefing.due(9, 7, today, today, False))
        self.assertTrue(briefing.due(9, 7, today - timedelta(days=1), today, False))
        self.assertFalse(briefing.due(9, 7, None, today, True))

    def test_setting_defaults_off_and_wired(self):
        from pathlib import Path
        from weatherlab.settings import Settings
        s = Settings()
        self.assertFalse(s.briefing_notice)
        self.assertEqual(s.briefing_hour, 7)
        root = Path(__file__).resolve().parent.parent
        self.assertIn("self._briefing(db, s)", (root / "weatherlab" / "poller.py").read_text(encoding="utf-8"))
        self.assertIn("briefing_notice=brief_on", (root / "weatherlab" / "screens" / "system.py").read_text(encoding="utf-8"))


class BriefingSunTimeTests(unittest.TestCase):
    def test_sun_times_follow_the_24_hour_setting(self):
        from weatherlab import timefmt
        self.assertEqual(api_pages._clock_text("17:42", timefmt), "5:42 PM" if not timefmt.use_24h() else "17:42")
        self.assertEqual(api_pages._clock_text("06:44", timefmt), "6:44 AM" if not timefmt.use_24h() else "06:44")
        self.assertIsNone(api_pages._clock_text(None, timefmt))

    def test_24_hour_setting_is_respected(self):
        from weatherlab import timefmt
        with mock.patch.object(timefmt, "use_24h", return_value=True):
            self.assertEqual(api_pages._clock_text("17:42", timefmt), "17:42")
        with mock.patch.object(timefmt, "use_24h", return_value=False):
            self.assertEqual(api_pages._clock_text("17:42", timefmt), "5:42 PM")
