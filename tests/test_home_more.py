"""More readings, the All alerts link and the hero style (0.37.51)."""
import pathlib
import unittest

from weatherlab import hero
from weatherlab.settings import Settings

NOW = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class MoreReadings(unittest.TestCase):
    def test_dew_and_airport_are_together_at_the_bottom(self):
        home = NOW[NOW.index("def home_page() -> None:"):NOW.index("def alerts_log_page")]
        block = home[home.index("st.expander(\"More readings"):]
        self.assertLess(block.index("_dew_card()"), block.index("airport_card(s)"))

    def test_each_part_opens_only_its_own_history_window(self):
        self.assertIn('live_history.show_pending([k for k in live_history.MEASURES if k != "dewpointf"])', NOW)
        self.assertIn('live_history.show_pending(["dewpointf"])', NOW)


class NoticesLink(unittest.TestCase):
    def test_strip_links_to_alert_history(self):
        start = NOW.index("def _notices(")
        self.assertIn('.get("Alert history")', NOW[start:NOW.index("\ndef ", start + 10)])


class HeroStyle(unittest.TestCase):
    def test_default_is_the_gradient(self):
        self.assertEqual(Settings().hero_style, "gradient")
        out, _ = hero.hero_html({"temp_text": "70°"})
        self.assertIn("linear-gradient(120deg", out)

    def test_plain_has_no_gradient(self):
        out, _ = hero.hero_html({"temp_text": "70°", "kind": "night", "plain": True})
        style = out[out.index('class="wl-hero"'):]
        style = style[:style.index(">")]
        self.assertNotIn("gradient", style)
        self.assertNotIn("svg", style)  # no stars


if __name__ == "__main__":
    unittest.main()
