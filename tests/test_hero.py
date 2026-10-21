"""The Live hero panel: sky choice, sunrise and sunset looks, and the HTML it builds. Offline."""

import unittest
from datetime import datetime

from weatherlab import hero


class HeroTests(unittest.TestCase):
    def test_storm_and_rain_win_over_night(self):
        self.assertEqual(hero.pick_kind(True, True, False, False), "storm")
        self.assertEqual(hero.pick_kind(True, False, True, False), "rain")
        self.assertEqual(hero.pick_kind(True, False, False, False), "night")
        self.assertEqual(hero.pick_kind(False, False, False, True), "cloudy_day")
        self.assertEqual(hero.pick_kind(False, False, False, False), "clear_day")

    def test_dawn_and_dusk(self):
        rise = datetime(2026, 10, 20, 6, 30)
        sset = datetime(2026, 10, 20, 17, 30)
        self.assertEqual(hero.sky_phase("clear_day", datetime(2026, 10, 20, 6, 40), rise, sset), "dawn")
        self.assertEqual(hero.sky_phase("clear_day", datetime(2026, 10, 20, 17, 40), rise, sset), "dusk")
        self.assertEqual(hero.sky_phase("clear_day", datetime(2026, 10, 20, 12, 0), rise, sset), "clear_day")
        self.assertEqual(hero.sky_phase("rain", datetime(2026, 10, 20, 6, 40), rise, sset), "rain")

    def test_html_escapes_text_and_shows_values(self):
        out, height = hero.hero_html({"temp_text": "83°", "label": "<b>Clear</b>", "place": "Goodyear",
                                      "live_text": "Live · updated just now", "live_state": "ok",
                                      "tiles": [("Wind", "8 mph", "gusts 12")]})
        self.assertIn("83°", out)
        self.assertNotIn("<b>Clear</b>", out)
        self.assertIn("&lt;b&gt;Clear&lt;/b&gt;", out)
        self.assertIn("No weather alerts", out)
        self.assertIn("gusts 12", out)
        self.assertGreater(height, 300)

    def test_alert_pill_and_range_bar(self):
        out, _ = hero.hero_html({"temp_text": "80°", "alert": "Flood Watch until 22 Oct 17:00", "alert_tone": "bad",
                                 "lo": 70.0, "hi": 95.0, "now": 80.0, "lo_text": "70°F", "hi_text": "95°F"})
        self.assertIn("Flood Watch until 22 Oct 17:00", out)
        self.assertNotIn("No weather alerts", out)
        self.assertIn("left:calc(40% - 8px)", out)

    def test_no_range_bar_without_a_spread(self):
        out, _ = hero.hero_html({"temp_text": "80°", "lo": 80.0, "hi": 80.0, "now": 80.0})
        self.assertNotIn("low →", out)


if __name__ == "__main__":
    unittest.main()
