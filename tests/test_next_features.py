"""Gauges, sparklines, alert map shapes, NWS outlines, and the history summaries. Offline."""

import unittest
from datetime import date, datetime, timedelta, timezone

from weatherlab import alert_map, dials, motion, nws, sparks, yearly


class DialTests(unittest.TestCase):
    def test_feels_zones(self):
        self.assertEqual(feels_name(50), "Cool")
        self.assertEqual(feels_name(70), "Comfortable")
        self.assertEqual(feels_name(100), "Hot")
        self.assertEqual(feels_name(140), "Extreme")

    def test_feels_dial_text_and_units(self):
        out, _ = dials.feels_dial_html(70.0, actual_f=72.0, humidity=45, dark=True)
        self.assertIn("70°F", out)
        self.assertIn("Comfortable", out)
        self.assertIn("humidity 45%", out)
        metric, _ = dials.feels_dial_html(32.0, metric=True)
        self.assertIn("0°C", metric)

    def test_pressure_bands_and_dial(self):
        self.assertEqual(dials.pressure_band(0.07)[0], "Rising fast")
        self.assertEqual(dials.pressure_band(-0.08)[0], "Falling fast")
        self.assertEqual(dials.pressure_band(0.0)[0], "Steady")
        out, _ = dials.pressure_dial_html(29.86, 0.03)
        self.assertIn("Rising", out)
        self.assertIn("29.86 inHg", out)
        self.assertIn("+0.03 inHg", out)


def feels_name(f):
    return dials.feels_zone(f)[0]


class SparkTests(unittest.TestCase):
    TZ = timezone.utc

    def test_usual_for_this_hour_needs_five_days(self):
        now = datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc)
        rows = []
        for day in range(7, 1, -1):  # six earlier days, oldest first; day 1 sits exactly on the cutoff
            ts = (now - timedelta(days=day)).timestamp()
            rows.append((ts, {"tempf": 90.0 + day}))
        rows.append((now.timestamp(), {"tempf": 99.0}))
        current, usual, days = sparks.hourly_usual(rows, "tempf", self.TZ, now.timestamp())
        self.assertEqual(current, 99.0)
        self.assertAlmostEqual(usual, 94.5)
        self.assertEqual(days, 6)
        self.assertIsNone(sparks.hourly_usual(rows[:3], "tempf", self.TZ, now.timestamp()))

    def test_compare_text(self):
        note, direction = sparks.compare_text(95.0, 90.0, "°F", 3)
        self.assertIn("▲ 5°F above usual", note)
        self.assertEqual(direction, "up")
        self.assertEqual(sparks.compare_text(90.5, 90.0, "°F", 3), ("● about usual for this hour", None))
        self.assertIn("▲ 5 mph above usual", sparks.compare_text(45.0, 40.0, "mph", 3)[0])

    def test_spark_and_tile(self):
        self.assertEqual(sparks.spark_svg([1.0], "#fff"), "")
        self.assertIn("<svg", sparks.spark_svg([1.0, 2.0, 3.0], "#fff"))
        html_out = sparks.tile_html({"label": "<Temp>", "value": "83", "unit": "°F", "series": [1, 2],
                                     "color": "#f00", "compare": "▲ 3°F above", "direction": "up"})
        self.assertIn("&lt;Temp&gt;", html_out)
        self.assertIn("▲ 3°F above", html_out)


class AlertMapTests(unittest.TestCase):
    ALERTS = [
        {"event": "Heat Advisory", "severity": "Moderate", "ugc": ["AZZ001"],
         "zones": [("AZZ001", [[[-112, 33], [-111, 33], [-111, 34]]])]},
        {"event": "Flood Warning", "severity": "Extreme", "ugc": ["AZZ002"],
         "zones": [("AZZ002", [[[-113, 33], [-112, 33], [-112, 34]]])]},
    ]

    def test_most_severe_drawn_last(self):
        out = alert_map.traces(self.ALERTS)
        self.assertEqual([t["name"] for t in out], ["Heat Advisory", "Flood Warning"])
        self.assertEqual(out[-1]["color"], nws.SEVERITY_COLORS["Extreme"])

    def test_highlight_fades_other_zones(self):
        out = alert_map.traces(self.ALERTS, highlight=0)
        by_name = {t["name"]: t["opacity"] for t in out}
        self.assertEqual(by_name["Heat Advisory"], 0.95)
        self.assertEqual(by_name["Flood Warning"], 0.2)

    def test_view_box_is_centred(self):
        x0, x1, y0, y1 = alert_map.view_box(33.4, -112.4)
        self.assertLess(x0, -112.4)
        self.assertGreater(x1, -112.4)
        self.assertAlmostEqual((y0 + y1) / 2, 33.4)


class OutlineTests(unittest.TestCase):
    def test_polygon_and_multipolygon(self):
        square = [[0, 0], [1, 0], [1, 1], [0, 0]]
        hole = [[0.2, 0.2], [0.3, 0.2], [0.3, 0.3], [0.2, 0.2]]
        self.assertEqual(nws._rings({"type": "Polygon", "coordinates": [square, hole]}), [square])
        multi = {"type": "MultiPolygon", "coordinates": [[square], [square, hole]]}
        self.assertEqual(nws._rings(multi), [square, square])
        self.assertEqual(nws._rings(None), [])


class YearlyTests(unittest.TestCase):
    DAYS = [
        (date(2025, 10, 20), {"tempf_max": 99.0, "tempf_min": 60.0, "rain_in": 0.0, "gust_max": 20.0,
                              "tempf_avg": 80.0}),
        (date(2026, 10, 20), {"tempf_max": 104.0, "tempf_min": 58.0, "rain_in": 0.5, "gust_max": 35.0,
                              "tempf_avg": 84.0}),
        (date(2026, 1, 5), {"tempf_max": 60.0, "tempf_min": 30.0, "rain_in": 0.25, "gust_max": 15.0,
                            "tempf_avg": 45.0}),
        (date(2026, 1, 6), {"tempf_max": 58.0, "tempf_min": 40.0, "rain_in": None}),
    ]

    def test_ranking_order(self):
        top = yearly.ranking(self.DAYS, "tempf_max", "max", 2)
        self.assertEqual([v for _, v in top], [104.0, 99.0])
        low = yearly.ranking(self.DAYS, "tempf_min", "min", 1)
        self.assertEqual(low[0][1], 30.0)

    def test_on_this_day(self):
        rows = yearly.on_this_day(self.DAYS, 10, 20)
        self.assertEqual([d.year for d, _ in rows], [2025, 2026])

    def test_monthly_rounds_and_sums(self):
        table = yearly.monthly(self.DAYS)
        self.assertEqual(table[2026][1], {"temp": 45.0, "rain": 0.25, "days": 2})
        self.assertEqual(table[2026][10]["temp"], 84.0)
        self.assertEqual(table[2025][10]["rain"], 0.0)

    def test_year_summary(self):
        s = yearly.year_summary(self.DAYS, 2026)
        self.assertEqual(s["days"], 3)
        self.assertEqual(s["rain"], 0.75)
        self.assertEqual(s["rainy_days"], 2)
        self.assertEqual(s["hottest"], (date(2026, 10, 20), 104.0))
        self.assertEqual(s["coldest"], (date(2026, 1, 5), 30.0))
        self.assertEqual(s["windiest"], (date(2026, 10, 20), 35.0))
        self.assertEqual(s["hot_days"], 1)
        self.assertEqual(s["freezing"], 1)  # 2026-01-05 low of 30°F
        self.assertEqual(yearly.year_summary(self.DAYS, 2026, hot_f=110.0)["hot_days"], 0)
        self.assertIsNone(yearly.year_summary(self.DAYS, 1999))


class MotionTests(unittest.TestCase):
    def test_script_added_only_when_on(self):
        self.assertEqual(motion.add("<p>", False), "<p>")
        out = motion.add("<p>", True)
        self.assertTrue(out.startswith("<p>") and out.endswith("</script>\n"))

    def test_needle_angles(self):
        self.assertIn("rotate(-64.3 110 112)", dials.feels_dial_html(70.0)[0])
        self.assertIn("rotate(27.0 130 118)", dials.pressure_dial_html(29.86, 0.03)[0])


if __name__ == "__main__":
    unittest.main()
