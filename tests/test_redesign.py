"""The redesign, part 1 (0.37.62): header bar, page titles above tabs, the Home cards and the line icons."""

import unittest
from unittest import mock

from weatherlab import hero, line_icons, nws, theme


class HeaderBar(unittest.TestCase):
    def tearDown(self):
        theme._CONTEXT.set(None)
        theme._SLOT.set(None)

    def test_bar_shows_station_place_and_live(self):
        out = theme.context_bar_html({"station": "Backyard", "place": "Springfield, AZ", "live": ("ok", "2 min ago")})
        self.assertIn("Backyard", out)
        self.assertIn("Springfield, AZ", out)
        self.assertIn("LIVE", out)
        self.assertIn("updated 2 min ago", out)

    def test_bar_words_say_the_state_without_colour(self):
        self.assertIn("OFFLINE", theme.context_bar_html({"live": ("silent", "40 min ago")}))
        self.assertIn("LATE", theme.context_bar_html({"live": ("slow", "9 min ago")}))
        self.assertNotIn("updated", theme.context_bar_html({"live": ("none", "No readings yet")}))

    def test_text_is_escaped(self):
        self.assertNotIn("<b>x", theme.context_bar_html({"station": "<b>x</b>"}))

    def test_bar_only_on_weather_pages(self):
        theme.set_context("Home", "Backyard", "", ("ok", "just now"))
        self.assertIn("wl-ctx", theme.page_head("Home", "Live readings"))
        theme.set_context("Settings", "Backyard", "", ("ok", "just now"))
        self.assertNotIn("wl-ctx", theme.page_head("Settings"))

    def test_tabbed_page_puts_its_name_in_the_slot(self):
        slot = mock.Mock()
        theme.set_context("Air and heat")
        theme.head_slot(slot)
        self.assertEqual(theme.page_head("Air quality", "From AirNow"), "")
        html = slot.markdown.call_args[0][0]
        self.assertIn("Air and heat", html)
        self.assertIn("From AirNow", html)
        self.assertIsNone(theme.take_slot())  # used once

    def test_dark_is_navy(self):
        self.assertEqual(theme.PAGE_DARK["background"], "#0b1828")
        self.assertIn("#38c6ec", theme.css(True))


class Place(unittest.TestCase):
    def test_city_and_state_from_points(self):
        reply = {"properties": {"relativeLocation": {"properties": {"city": "Springfield", "state": "AZ"}}}}
        with mock.patch.object(nws, "_get", return_value=reply):
            self.assertEqual(nws.place_name(33.4, -112.0, "me"), "Springfield, AZ")

    def test_missing_gives_empty(self):
        with mock.patch.object(nws, "_get", return_value={}):
            self.assertEqual(nws.place_name(33.4, -112.0, "me"), "")


class HomeCards(unittest.TestCase):
    def test_right_now_card(self):
        out = hero.card_html({"temp": "84", "unit": "°F", "label": "Partly cloudy", "feels": "86 °F", "hi_text": "89°",
                              "lo_text": "68°", "trend": "2° in the last hour", "trend_up": True,
                              "sun_note": "Sunset in 3 h 18 min"})
        for text in ("84", "°F", "Partly cloudy", "Feels like 86 °F", "89°", "68°", "▲", "Sunset in 3 h 18 min"):
            self.assertIn(text, out)

    def test_steady_and_alert(self):
        out = hero.card_html({"temp": "70", "trend": "steady over the last hour", "trend_up": None,
                              "alert": "Heat warning", "alert_tone": "bad"})
        self.assertIn("–", out)
        self.assertIn("Heat warning", out)

    def test_reading_card(self):
        out = hero.metric_html("", "Wind", "6", "mph SW", "Gusts 18 mph today", "<svg></svg>")
        self.assertIn("mph SW", out)
        self.assertIn("Gusts 18 mph today", out)

    def test_no_network_in_the_sky(self):
        out = hero.card_html({"temp": "70", "kind": "night"})
        self.assertNotIn("http://", out.replace("http://www.w3.org/2000/svg", ""))
        self.assertNotIn("https://", out)


class Icons(unittest.TestCase):
    def test_known_and_unknown(self):
        self.assertIn("<svg", line_icons.icon("wind"))
        self.assertEqual(line_icons.icon("nope"), "")


if __name__ == "__main__":
    unittest.main()
