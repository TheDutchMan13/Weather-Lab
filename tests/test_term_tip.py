"""The ? that goes in a tile label: it shows the one-line meaning on hover or focus, and is keyboard reachable."""
import unittest

try:
    from weatherlab import theme
except ImportError:
    theme = None


@unittest.skipIf(theme is None, "streamlit is not installed")
class TermTipTests(unittest.TestCase):
    def test_tip_has_a_label_and_the_meaning(self):
        tip = theme.term_tip("aqi")
        self.assertIn('class="wl-tip"', tip)
        self.assertIn('tabindex="0"', tip)
        self.assertIn("What is Air quality index?", tip)
        self.assertIn('role="tooltip"', tip)

    def test_unknown_term_gives_nothing(self):
        self.assertEqual(theme.term_tip("nope"), "")

    def test_css_shows_the_meaning_on_hover_and_focus(self):
        css = theme.css(False)
        self.assertIn(".wl-tip:hover .wl-tip-text", css)
        self.assertIn(".wl-tip:focus .wl-tip-text", css)

    def test_strip_tile_gets_the_tip(self):
        tile = theme.strip_tile_html("Heat index now", "90", help_key="heat_index")
        self.assertIn("wl-tip", tile)
        self.assertNotIn("&lt;span", tile)


if __name__ == "__main__":
    unittest.main()
