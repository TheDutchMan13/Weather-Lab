"""Theme tests. Skipped where Streamlit isn't installed."""

import unittest

try:
    from weatherlab import theme
except ImportError:
    theme = None


@unittest.skipIf(theme is None, "streamlit is not installed")
class ThemeTests(unittest.TestCase):
    def test_explicit_modes(self):
        self.assertTrue(theme.is_dark("dark"))
        self.assertFalse(theme.is_dark("light"))


@unittest.skipIf(theme is None, "streamlit is not installed")
class SectionTests(unittest.TestCase):
    def test_section_escapes_and_shows_age(self):
        import time
        out = theme.section_html("<b>Rain</b>", "note", updated=time.time() - 120)
        self.assertIn("&lt;b&gt;Rain&lt;/b&gt;", out)
        self.assertIn("updated 2 min ago", out)

    def test_freshness_colours(self):
        import time
        self.assertIn("#15803d", theme.freshness_html(time.time()))
        self.assertIn("#b45309", theme.freshness_html(time.time() - 30 * 60))
        self.assertIn("#b91c1c", theme.freshness_html(time.time() - 3 * 3600))
        self.assertEqual(theme.freshness_html(None), "")


if __name__ == "__main__":
    unittest.main()
