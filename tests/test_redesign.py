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


class AlertKinds(unittest.TestCase):
    def test_levels_from_words(self):
        from weatherlab import alert_kinds
        self.assertEqual(alert_kinds.classify("Lightning about 8 miles away.")["level"], "Critical")
        self.assertEqual(alert_kinds.classify("High wind gust: 28 mph")["level"], "Warning")
        self.assertEqual(alert_kinds.classify("Sensor battery low on the outdoor sensor.")["kind"], "Station")
        self.assertEqual(alert_kinds.classify("Weather Lab hasn't received a reading from the station for 15 minutes.")["kind"], "Station")
        self.assertEqual(alert_kinds.classify("Rain has started.")["level"], "Info")
        self.assertEqual(alert_kinds.classify("Yesterday (Nov 23): high 81 °F, rain 0.00 in.")["icon"], "calendar")
        self.assertEqual(alert_kinds.classify("Weather Lab 0.38.0 is available.")["kind"], "App")

    def test_title_and_detail(self):
        from weatherlab import alert_kinds
        self.assertEqual(alert_kinds.split("High wind gust: 28 mph, above your alert."), ("High wind gust", "28 mph, above your alert."))
        self.assertEqual(alert_kinds.split("Rain has started."), ("Rain has started", ""))

    def test_counts(self):
        from weatherlab import alert_kinds
        c = alert_kinds.counts([{"level": "Info"}, {"level": "Info"}, {"level": "Critical"}])
        self.assertEqual((c["Critical"], c["Warning"], c["Info"], c["total"]), (1, 0, 2, 3))


class AskFocus(unittest.TestCase):
    def setUp(self):
        from datetime import date
        self.today = date(2026, 11, 24)
        self.days = [(date(2026, 8, 10), {"rain_in": 2.0, "tempf_max": 101, "tempf_min": 80}),
                     (date(2026, 9, 3), {"rain_in": 0.5, "tempf_max": 96, "tempf_min": 70}),
                     (date(2026, 11, 2), {"rain_in": 5.0, "tempf_max": 75, "tempf_min": 45})]

    def test_month_answer_skips_this_month(self):
        from weatherlab import ask
        f = ask.focus("wettest month", self.days, self.today)
        self.assertEqual((f["measure"], f["year"], f["month"], f["day"]), ("rain", 2026, 8, None))
        bars = ask.bars(f, self.days)
        self.assertEqual(len(bars), 12)
        self.assertTrue(bars[7][2])  # August is the answer

    def test_day_answer(self):
        from weatherlab import ask
        f = ask.focus("coldest night", self.days, self.today)
        self.assertEqual((f["measure"], f["day"].month), ("low", 11))
        self.assertEqual(ask.bars(f, self.days), [("2", 45, True)])

    def test_nothing_to_draw(self):
        from weatherlab import ask
        self.assertIsNone(ask.focus("how many days over 100", self.days, self.today))
        self.assertIsNone(ask.focus("hello", self.days, self.today))


class RainHits(unittest.TestCase):
    def test_rate(self):
        from weatherlab import forecast_check
        self.assertEqual(forecast_check.rain_hit_rate({"wet_days": 2, "wet_rained": 1, "dry_days": 8, "dry_rained": 1}), 80)
        self.assertIsNone(forecast_check.rain_hit_rate({"wet_days": 0, "wet_rained": 0, "dry_days": 0, "dry_rained": 0}))


class Batch3(unittest.TestCase):
    def test_aqi_between(self):
        import os, tempfile
        old = os.environ.get("APPDATA")
        os.environ["APPDATA"] = tempfile.mkdtemp()
        try:
            from weatherlab import storage
            db = storage.connect()
            for t in (100, 200, 300):
                storage.store_aqi(db, {"aqi": t // 10}, t)
            self.assertEqual([a["aqi"] for _, a in storage.aqi_between(db, 150, 300)], [20, 30])
        finally:
            if old is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = old

    def test_day_icon(self):
        from weatherlab.screens.history import _day_kind
        self.assertEqual(_day_kind({"rain_in": 0.2, "sun_hours": 9}), "rain")
        self.assertEqual(_day_kind({"sun_hours": 9}), "clear_day")
        self.assertEqual(_day_kind({"sun_hours": 5}), "cloudy_day")
        self.assertEqual(_day_kind({"sun_hours": 1}), "cloud")

    def test_daylight_arch(self):
        from weatherlab.screens.outlook import _daylight_svg
        up = _daylight_svg(0.5, "7:00 AM", "5:30 PM", "10 h 30 m", "12:15 PM")
        self.assertIn("10 h 30 m", up)
        self.assertIn("12:15 PM", up)
        self.assertNotIn("12:15 PM", _daylight_svg(None, "7:00 AM", "5:30 PM", "10 h 30 m", "12:15 PM"))

    def test_uv_colours(self):
        from weatherlab.screens.outlook import _uv_colour
        self.assertEqual(_uv_colour(1), "#3ddc84")
        self.assertEqual(_uv_colour(12), "#b06cff")


class FireDanger(unittest.TestCase):
    def test_levels(self):
        from weatherlab import fire
        self.assertEqual(fire.danger(2)["level"], "Low")
        self.assertEqual(fire.danger(8)["level"], "Moderate")
        self.assertEqual(fire.danger(15)["level"], "High")
        self.assertEqual(fire.danger(30)["level"], "Very high")
        self.assertEqual(fire.danger(60)["level"], "Extreme")
        self.assertEqual(fire.danger(60)["share"], 1.0)
        self.assertEqual(fire.danger(None)["level"], "Unknown")

    def test_gauge_draws(self):
        from weatherlab.screens.hazards import _fire_gauge
        self.assertIn("Moderate", _fire_gauge(.2, "#f6c445", "Moderate"))


class InlineColours(unittest.TestCase):
    def test_coloured_spans_keep_their_colour(self):
        self.assertIn(".stApp span:not([style*='color'])", theme.css(True))


class Batch5(unittest.TestCase):
    def test_banner_holds_icon_title_and_line(self):
        from weatherlab import hero
        out = hero.banner_html("<svg></svg>", "Station connected", "Backyard", '<div class="wl-bline">x</div>')
        for text in ("wl-banner", "Station connected", "Backyard", "wl-bline", "<svg>"):
            self.assertIn(text, out)

    def test_banner_without_a_line_has_no_empty_sub(self):
        from weatherlab import hero
        self.assertNotIn("wl-bsub", hero.banner_html("", "Title"))

    def test_new_styles_exist(self):
        css = theme.css(True)
        for name in (".wl-banner", ".wl-cols", ".wl-srows", ".wl-stcard", ".wl-term", ".wl-bcard", ".wl-kvlist"):
            self.assertIn(name, css)

    def test_status_row_names_its_word(self):
        from weatherlab.screens.system import _srow
        row = _srow("ok", "Collector", "Receiving data", "Running")
        self.assertIn("Running", row)
        self.assertIn("Collector", row)

    def test_station_card_marks_the_picked_one(self):
        from weatherlab.screens.system import _station_card
        f = {"id": "main", "name": "Backyard", "ts": None, "state": "none"}
        self.assertIn("wl-on", _station_card(f, True))
        self.assertNotIn("wl-on", _station_card(f, False))

    def test_help_rows_are_in_letter_order_with_icons(self):
        from weatherlab import glossary
        from weatherlab.screens.help import TERM_ICONS, _rows
        out = _rows(glossary.TERMS)
        self.assertLess(out.index('wl-letter">A'), out.index('wl-letter">D'))
        for t in glossary.TERMS:
            self.assertIn(t["key"], TERM_ICONS)

    def test_version_entry(self):
        from weatherlab import whats_new
        self.assertIn("0.37.66", [e["version"] for e in whats_new.ENTRIES])
