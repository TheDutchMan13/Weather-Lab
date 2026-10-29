"""The ? tips are off on Windows (0.37.37): term_tip gives nothing, so no tile label shows a ?."""
import unittest

try:
    from weatherlab import theme
except ImportError:
    theme = None


@unittest.skipIf(theme is None, "streamlit is not installed")
class TermTipTests(unittest.TestCase):
    def test_no_question_mark_for_a_known_term(self):
        self.assertEqual(theme.term_tip("aqi"), "")

    def test_unknown_term_gives_nothing(self):
        self.assertEqual(theme.term_tip("nope"), "")

    def test_css_shows_the_meaning_on_hover_and_focus(self):
        css = theme.css(False)
        self.assertIn(".wl-tip:hover .wl-tip-text", css)
        self.assertIn(".wl-tip:focus .wl-tip-text", css)

    def test_strip_tile_gets_the_tip(self):
        tile = theme.strip_tile_html("Heat index now", "90", help_key="heat_index")
        self.assertNotIn("wl-tip", tile)


if __name__ == "__main__":
    unittest.main()
