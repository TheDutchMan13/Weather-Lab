"""Theme and gauge tests. Skipped where Streamlit isn't installed."""

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

    def test_gauge_arc_is_clamped(self):
        full = theme.gauge_html(150, 0, 100, "Humidity", "{:.0f}", False)
        empty = theme.gauge_html(-5, 0, 100, "Humidity", "{:.0f}", False)
        self.assertIn('stroke-dasharray="276.5,276.5"', full)
        self.assertIn('stroke-dasharray="0.0,276.5"', empty)

    def test_missing_value_shows_dashes(self):
        self.assertIn(">--</text>", theme.gauge_html(None, 0, 100, "Humidity", "{:.0f}", True))

    def test_status_dot_colors(self):
        self.assertIn("#3ddc84", theme.status_dot("ok"))
        self.assertIn("#9aa3b0", theme.status_dot("none"))


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


@unittest.skipIf(theme is None, "streamlit is not installed")
class SweepTests(unittest.TestCase):
    def test_animated_gauge_gets_the_sweep_class(self):
        self.assertIn('class="wl-sweep"', theme.gauge_html(50, 0, 100, "H", "{:.0f}", False, animate=True))
        self.assertNotIn("wl-sweep", theme.gauge_html(50, 0, 100, "H", "{:.0f}", False))


if __name__ == "__main__":
    unittest.main()
