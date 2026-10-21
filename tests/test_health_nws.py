"""Sensor health and NWS parsing. No network: NWS responses are sample data.

Run with:  python -m unittest discover -s tests -v
"""

import unittest
from unittest import mock

from weatherlab import health, nws


class HealthTests(unittest.TestCase):
    def test_completeness(self):
        rows = [(i * 30, {"tempf": 70.0}) for i in range(2880)]  # a full day at 30 s
        self.assertEqual(health.completeness(rows, 24), 100.0)
        self.assertEqual(health.completeness(rows[:1440], 24), 50.0)

    def test_gaps_found(self):
        rows = [(0, {}), (30, {}), (600, {}), (630, {})]  # 570 s pause between 30 and 600
        self.assertEqual(health.gaps(rows), [(30, 600)])

    def test_no_gaps_when_regular(self):
        rows = [(i * 30, {}) for i in range(10)]
        self.assertEqual(health.gaps(rows), [])

    def test_sensor_presence(self):
        rows = [(0, {"tempf": 70.0, "uv": 0}), (30, {"tempf": 71.0})]
        by_key = {s["key"]: s for s in health.sensors(rows)}
        self.assertEqual(by_key["tempf"]["present_pct"], 100.0)
        self.assertEqual(by_key["uv"]["present_pct"], 50.0)
        self.assertEqual(by_key["uv"]["last_seen"], 0)
        self.assertIsNone(by_key["baromrelin"]["last_seen"])

    def test_age_status(self):
        self.assertEqual(health.age_status(1000, 1100)[0], "ok")
        self.assertEqual(health.age_status(1000, 1000 + 10 * 60)[0], "slow")
        self.assertEqual(health.age_status(1000, 1000 + 60 * 60)[0], "silent")
        self.assertEqual(health.age_status(None, 1000)[0], "none")


POINTS = {"properties": {"forecast": "https://api.weather.gov/gridpoints/PSR/1,2/forecast",
                         "forecastHourly": "https://api.weather.gov/gridpoints/PSR/1,2/forecast/hourly",
                         "forecastZone": "https://api.weather.gov/zones/forecast/AZZ540"}}

ALERTS = {"features": [
    {"properties": {"event": "Heat Advisory", "headline": "Heat advisory in effect",
                    "severity": "Moderate", "expires": "2026-10-20T20:00:00-07:00"}},
    {"properties": {"event": "Extreme Wind Warning", "headline": "Wind warning",
                    "severity": "Extreme", "expires": ""}},
    {"properties": {"event": "Odd Thing", "severity": "Weird"}},
]}

DAILY = {"properties": {"periods": [
    {"name": "Tonight", "isDaytime": False, "temperature": 72, "temperatureUnit": "F",
     "windSpeed": "5 mph", "shortForecast": "Clear", "detailedForecast": "Clear skies.",
     "probabilityOfPrecipitation": {"value": None}},
    {"name": "Wednesday", "isDaytime": True, "temperature": 97, "temperatureUnit": "F",
     "windSpeed": "10 mph", "shortForecast": "Sunny", "detailedForecast": "Sunny.",
     "probabilityOfPrecipitation": {"value": 10}},
]}}


class NwsTests(unittest.TestCase):
    def test_points_gives_forecast_urls(self):
        with mock.patch.object(nws, "_get", return_value=POINTS):
            p = nws.points(33.4, -112.4, "me@example.com")
        self.assertTrue(p["forecast"].endswith("/forecast"))
        self.assertEqual(p["zone"], "AZZ540")

    def test_points_without_forecast_is_an_error(self):
        with mock.patch.object(nws, "_get", return_value={"properties": {}}):
            with self.assertRaises(nws.NwsError):
                nws.points(0.0, 0.0, "")

    def test_alerts_sorted_most_severe_first_and_unknown_severity_mapped(self):
        with mock.patch.object(nws, "_get", return_value=ALERTS):
            out = nws.alerts(33.4, -112.4, "")
        self.assertEqual([a["severity"] for a in out], ["Extreme", "Moderate", "Unknown"])
        self.assertEqual(out[1]["event"], "Heat Advisory")

    def test_daily_forecast_parsed(self):
        with mock.patch.object(nws, "_get", return_value=DAILY):
            out = nws.forecast_daily("https://example/forecast", "")
        self.assertEqual(out[0]["name"], "Tonight")
        self.assertIsNone(out[0]["pop"])
        self.assertEqual(out[1]["pop"], 10)

    def test_user_agent_includes_contact(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"{}"

        def fake_urlopen(req, timeout):
            captured["ua"] = req.get_header("User-agent")
            return FakeResponse()

        with mock.patch.object(nws, "urlopen", side_effect=fake_urlopen):
            nws._get("https://example", "me@example.com")
        self.assertIn("me@example.com", captured["ua"])


if __name__ == "__main__":
    unittest.main()
