"""The welcome screen (0.37.61): time of day, readable text, one self-contained picture, and what starts the wizard."""

import re
import unittest
from unittest import mock

from weatherlab.screens import welcome


def _lum(hex_colour: str) -> float:
    r, g, b = (int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _blend(stops, at: float) -> str:
    """The sky colour at one height, between its two nearest stops."""
    for (o1, c1), (o2, c2) in zip(stops, stops[1:]):
        if o1 <= at <= o2:
            t = (at - o1) / (o2 - o1)
            return "#" + "".join(f"{round(int(c1[i:i + 2], 16) * (1 - t) + int(c2[i:i + 2], 16) * t):02X}" for i in (1, 3, 5))
    return stops[-1][1]


class PeriodTests(unittest.TestCase):
    def test_every_hour_has_a_period_and_the_edges_are_right(self):
        self.assertEqual({welcome.period(h) for h in range(24)}, set(welcome.PERIODS))
        self.assertEqual([welcome.period(h) for h in (4, 5, 11, 12, 16, 17, 20, 21, 23, 0)],
                         ["night", "morning", "morning", "afternoon", "afternoon", "evening", "evening", "night", "night", "night"])

    def test_each_period_has_a_greeting_and_a_palette(self):
        for name in welcome.PERIODS:
            self.assertIn(name, welcome.GREETING)
            self.assertIn(name, welcome.PALETTE)
            self.assertTrue(welcome.GREETING[name].endswith("."))


class LookTests(unittest.TestCase):
    def test_text_is_readable_over_the_sky_where_it_sits(self):
        # The text sits in the top 40% of the window (the sky stops there, by design).
        for name, p in welcome.PALETTE.items():
            for at in (0.0, 0.2, 0.4):
                sky = _blend(p["stops"], at)
                for colour, label, need in ((welcome.INK, "greeting", 4.5), (welcome.SUB, "subtitle", 4.5), (welcome.EYEBROW, "eyebrow", 4.5)):
                    self.assertGreaterEqual(_contrast(colour, sky), need, f"{name} {label} at {at}: {sky}")

    def test_small_print_is_readable_over_the_darkest_hill(self):
        for name, p in welcome.PALETTE.items():
            self.assertGreaterEqual(_contrast(welcome.NOTE, p["hills"][2]), 4.5, name)

    def test_the_picture_needs_nothing_from_the_network(self):
        for name in welcome.PERIODS:
            svg = welcome.scene_svg(name)
            self.assertNotIn("http://", svg.replace("http://www.w3.org/2000/svg", ""))
            self.assertNotIn("https://", svg)
            self.assertNotIn("<image", svg)
            self.assertNotIn("<script", svg)
            self.assertTrue(svg.startswith("<svg") and svg.endswith("</svg>"))
            self.assertLess(len(svg), 12000)

    def test_stars_only_when_dark_and_the_moon_only_at_night(self):
        self.assertEqual(welcome.PALETTE["afternoon"]["stars"], 0)
        self.assertGreater(welcome.PALETTE["night"]["stars"], welcome.PALETTE["evening"]["stars"] > 0)
        self.assertEqual([n for n, p in welcome.PALETTE.items() if p["moon"]], ["night"])

    def test_css_hides_the_sidebar_and_uses_the_bundled_font(self):
        css = welcome.css("evening")
        self.assertIn("stSidebar", css)
        self.assertIn("app/static/outfit.ttf", css)
        self.assertIn("data:image/svg+xml", css)
        self.assertNotIn("url(http", css)
        self.assertEqual(len(re.findall(r"<style>", css)), 1)


class FlowTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        patcher = mock.patch.object(welcome.st, "session_state", self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _settings(self, ip):
        return mock.patch.object(welcome, "load_settings", return_value=mock.Mock(station_ip=ip))

    def test_a_new_install_sees_it(self):
        with self._settings(""):
            self.assertTrue(welcome.pending())

    def test_a_saved_station_skips_it(self):
        with self._settings("192.168.1.50"):
            self.assertFalse(welcome.pending())

    def test_run_setup_again_skips_it(self):
        self.state["wiz_active"] = True
        with self._settings(""):
            self.assertFalse(welcome.pending())

    def test_find_my_station_opens_the_wizard_and_starts_the_search(self):
        welcome._begin(True)
        self.assertTrue(self.state["wl_welcomed"] and self.state["wiz_active"] and self.state["wiz_autofind"])
        self.assertEqual(self.state["wiz_step"], 0)
        with self._settings(""):
            self.assertFalse(welcome.pending())

    def test_i_know_its_address_opens_the_wizard_without_searching(self):
        welcome._begin(False)
        self.assertTrue(self.state["wiz_active"])
        self.assertNotIn("wiz_autofind", self.state)


if __name__ == "__main__":
    unittest.main()
