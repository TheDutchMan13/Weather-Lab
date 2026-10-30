"""The ? help marks are gone (0.37.37), and nothing restyles the buttons of popovers (0.37.38).

The ? marks used a popover button styled as a small round ring. With the marks gone, that rule squashed the
Customize button on Home into a tiny circle."""
import pathlib
import unittest

try:
    from weatherlab import theme
except ImportError:
    theme = None

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipIf(theme is None, "streamlit is not installed")
class NoHelpMarks(unittest.TestCase):
    def test_no_popover_button_restyle(self):
        css = theme.css(False)
        self.assertNotIn("stPopover", css)
        self.assertNotIn("wl-tip", css)

    def test_no_tip_helpers_left(self):
        self.assertFalse(hasattr(theme, "term_tip"))

    def test_strip_tile_still_builds(self):
        tile = theme.strip_tile_html("Heat index now", "90", "Caution", "warn")
        self.assertIn("Heat index now", tile)
        self.assertNotIn("wl-tip", tile)


class NoHelpSource(unittest.TestCase):
    def test_pages_do_not_ask_for_help_marks(self):
        for name in ("screens/now.py", "screens/hazards.py", "screens/outlook.py", "screens/common.py"):
            src = (ROOT / "weatherlab" / name).read_text(encoding="utf-8")
            self.assertNotIn("help_key", src, name)
            self.assertNotIn("term_help", src, name)
            self.assertNotIn("term_tip", src, name)


if __name__ == "__main__":
    unittest.main()
