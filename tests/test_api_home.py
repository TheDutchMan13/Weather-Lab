"""The Home layout for the Android Live tab (0.37.46)."""
import unittest
from dataclasses import replace

from tests.test_api_pages import ApiHelpers


class HomeLayoutApi(ApiHelpers, unittest.TestCase):
    def test_layout_follows_the_settings(self):
        s = replace(self.s, home_briefing=False, live_cards=["tempinf", "dailyrainin", "windgustmph"],
                    wide_cards=["dailyrainin"], gauges="closed")
        code, body = self.get("/api/v1/home", s)
        self.assertEqual(code, 200)
        self.assertEqual(body, {"briefing": False, "cards": ["tempinf", "dailyrainin", "windgustmph"],
                                "wide": ["dailyrainin"], "gauges": "closed", "hero": "gradient"})

    def test_24_hour_readings_and_stale_wide_cards_are_left_out(self):
        s = replace(self.s, live_cards=["tempf", "humidity", "windgustmph"], wide_cards=["tempf", "uv", "windgustmph"])
        _, body = self.get("/api/v1/home", s)
        self.assertEqual(body["cards"], ["windgustmph"])
        self.assertEqual(body["wide"], ["windgustmph"])

    def test_defaults(self):
        _, body = self.get("/api/v1/home")
        self.assertTrue(body["briefing"])
        self.assertEqual(body["cards"], ["windgustmph", "dailyrainin", "tempinf"])
        self.assertEqual(body["wide"], [])
        self.assertEqual(body["gauges"], "auto")

    def test_needs_the_token(self):
        from weatherlab import api
        code, _ = api.route("/api/v1/home", "Bearer wrong", self.db, self.s, self.now)
        self.assertEqual(code, 401)


if __name__ == "__main__":
    unittest.main()
