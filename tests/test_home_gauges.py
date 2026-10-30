"""Gauges on Home (0.37.44): a group of its own, open on a computer and closed on a phone, set on Home layout."""
import pathlib
import unittest

from weatherlab import card_order
from weatherlab.settings import Settings

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOW = (ROOT / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")
PHONE = "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36"
DESKTOP = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"


class Gauges(unittest.TestCase):
    def test_auto_opens_on_a_computer_and_closes_on_a_phone(self):
        self.assertTrue(card_order.gauges_open("auto", DESKTOP))
        self.assertFalse(card_order.gauges_open("auto", PHONE))
        self.assertFalse(card_order.gauges_open("auto", "iPhone"))
        self.assertTrue(card_order.gauges_open("auto", ""))

    def test_the_choice_beats_the_device(self):
        self.assertTrue(card_order.gauges_open("open", PHONE))
        self.assertFalse(card_order.gauges_open("closed", DESKTOP))

    def test_default_is_auto(self):
        self.assertEqual(Settings().gauges, "auto")

    def test_home_wiring(self):
        self.assertIn('st.expander("Gauges"', NOW)
        self.assertNotIn("Compact sections", NOW)
        self.assertNotIn("live_compact", NOW)
        start = NOW.index("def home_page() -> None:")
        body = NOW[start:NOW.index("def alerts_log_page", start)]
        self.assertLess(body.index("live_readings()"), body.index("airport_card(s)"))


if __name__ == "__main__":
    unittest.main()
