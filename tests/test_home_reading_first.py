"""Home shows the reading right now first, then the briefing (0.37.39), and doesn't repeat the hero's numbers."""
import pathlib
import unittest

SRC = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class HomeReadingFirst(unittest.TestCase):
    def setUp(self):
        start = SRC.index("def home_page() -> None:")
        self.body = SRC[start:SRC.index("def alerts_log_page", start)]

    def test_right_now_comes_before_the_briefing(self):
        self.assertLess(self.body.index("live_now()"), self.body.index("_briefing_card(s)"))
        self.assertLess(self.body.index("_briefing_card(s)"), self.body.index("live_readings()"))

    def test_no_duplicate_status_or_caption(self):
        self.assertNotIn("freshness_line", SRC)
        self.assertNotIn("_today_vs_yesterday", SRC)

    def test_briefing_has_no_tile_grid(self):
        start = SRC.index("def _briefing_card(")
        body = SRC[start:SRC.index("def home_page", start)]
        self.assertNotIn("grid_html", body)

    def test_hero_sizes_to_its_content(self):
        start = SRC.index("def _hero(")
        body = SRC[start:SRC.index("\ndef ", start + 10)]
        self.assertNotIn("components.html", body)  # a fixed-height frame left a gap under the panel on desktop


if __name__ == "__main__":
    unittest.main()
