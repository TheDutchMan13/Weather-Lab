"""The Android app's extra pages: rankings, rain, wind, lightning, sun, heat, station, What's New, forecast."""
import json
import tempfile
import time
import unittest
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from tests.test_api import FakeKeys, PHX
from weatherlab import api, api_pages, nws, storage
from weatherlab.settings import Settings


class ApiHelpers:
    """Shared setup for the API page tests."""

    def setUp(self):
        keys = FakeKeys()
        p = mock.patch.object(api, "keystore", keys)
        p.start()
        self.addCleanup(p.stop)
        api._failures, api._locked_until = 0, 0.0
        self.db = storage.connect(Path(tempfile.mkdtemp()) / "t.db")
        self.addCleanup(self.db.close)
        self.s = replace(Settings(), timezone=PHX, units="US", latitude=33.4, longitude=-112.0)
        self.now = time.time()
        self.token = api.create_token()
        self.today = datetime.fromtimestamp(self.now, ZoneInfo(PHX)).date()
        api_pages._forecast_cache.clear()

    def get(self, path, s=None):
        return api.route(path, f"Bearer {self.token}", self.db, s or self.s, self.now)

    def seed_days(self):
        with self.db:
            for n, (hi, rain) in enumerate([(100, 0.5), (112, 0.0), (80, 0.0), (95, 1.2)], start=1):
                self.db.execute("INSERT INTO daily (date, data) VALUES (?, ?)", (
                    (self.today - timedelta(days=n)).isoformat(),
                    json.dumps({"tempf_max": hi, "tempf_min": hi - 30, "rain_in": rain, "gust_max": 20.0 + n,
                                "uvi": 9.0, "sun_hours": 10.0, "heat_index_max": hi})))

    def seed_readings(self, minutes=120):
        for m in range(minutes):
            ts = int(self.now - m * 60)
            storage.store_reading(self.db, {"tempf": 90.0, "humidity": 30.0, "windspeedmph": 8.0, "winddir": 270.0,
                                            "windgustmph": 12.0, "uv": 6.0, "solarradiation": 600.0,
                                            "dailyrainin": 0.0, "rainratein": 0.0}, ts)


class ApiPagesTests(ApiHelpers, unittest.TestCase):
    def test_rankings(self):
        self.seed_days()
        code, body = self.get("/api/v1/rankings")
        self.assertEqual(code, 200)
        by = {r["label"]: r for r in body["rankings"]}
        self.assertEqual(by["Warmest days"]["items"][0]["value"], 112)
        self.assertEqual(by["Coolest days"]["items"][0]["value"], 80)
        self.assertEqual(by["Wettest days"]["items"][0]["value"], 1.2)

    def test_rain_calendar_and_bad_month(self):
        self.seed_days()
        month = (self.today - timedelta(days=1)).strftime("%Y-%m")
        _, body = self.get(f"/api/v1/rain/calendar/{month}")
        self.assertGreaterEqual(body["total"], 0.5)
        self.assertGreaterEqual(body["rainy_days"], 1)
        self.assertTrue(body["years"])
        self.assertIn("error", self.get("/api/v1/rain/calendar/nonsense")[1])

    def test_rain_events_group_a_shower(self):
        base = int(self.now - 3600)
        for i, total in enumerate([0.0, 0.05, 0.1, 0.1, 0.1]):
            storage.store_reading(self.db, {"dailyrainin": total, "rainratein": 0.5 if total else 0.0}, base + i * 300)
        _, body = self.get("/api/v1/rain/events")
        self.assertEqual(len(body["events"]), 1)
        self.assertEqual(body["events"][0]["rain"], 0.1)

    def test_wind_rose(self):
        self.seed_readings()
        _, body = self.get("/api/v1/wind/1")
        top = max(body["directions"], key=lambda d: d["percent"])
        self.assertEqual(top["name"], "W")
        self.assertEqual(body["dominant"], "W")
        self.assertEqual(len(body["bins"]), 4)  # 1 mph, 2 mph, 3-4 mph, 5+ mph (calm is not drawn)
        self.assertEqual(self.get("/api/v1/wind/9")[0], 404)

    def test_lightning_days(self):
        storage.store_strike(self.db, int(self.now - 100), 4.0)
        storage.store_strike(self.db, int(self.now - 200), 2.5)
        _, body = self.get("/api/v1/lightning/days")
        self.assertEqual(body["days"][0]["strikes"], 2)
        self.assertEqual(body["days"][0]["closest"], 2.5)
        _, mt = self.get("/api/v1/lightning/days", replace(self.s, units="Metric"))
        self.assertEqual(mt["unit"], "km")

    def test_sun(self):
        self.seed_readings()
        _, body = self.get("/api/v1/sun")
        self.assertEqual(body["uv_now"], 6.0)
        self.assertEqual(body["uv_now_word"], "high")
        self.assertEqual(len(body["burn_now"]), 6)
        self.assertGreater(body["sunshine_week_hours"], 0)
        self.assertTrue(body["sunrise"] and body["sunset"])

    def test_heat(self):
        self.seed_readings()
        self.seed_days()
        _, body = self.get("/api/v1/heat")
        self.assertIsNotNone(body["heat_index"])
        self.assertIn("level", body)
        self.assertEqual(len(body["levels"]), 5)
        self.assertGreaterEqual(body["days_110"], 0)

    def test_station_without_a_gateway(self):
        self.seed_readings(60)
        _, body = self.get("/api/v1/station")
        self.assertEqual(body["status"], "ok")
        self.assertIsNone(body["radios"])
        self.assertTrue(any(x["label"] == "Outdoor temp" for x in body["sensors"]))

    def test_whats_new(self):
        _, body = self.get("/api/v1/whatsnew")
        self.assertEqual(body["entries"][0]["version"], api.APP_VERSION)

    def test_forecast_needs_a_location_and_converts_units(self):
        _, no = self.get("/api/v1/forecast", replace(self.s, latitude=None))
        self.assertFalse(no["available"])
        period = {"name": "Today", "isDaytime": True, "temperature": 104, "unit": "F", "wind": "5 mph", "short": "Sunny",
                  "detail": "Sunny.", "pop": 10, "start": "x"}
        with mock.patch.object(nws, "points", return_value={"forecast": "u", "forecastHourly": "h"}), \
                mock.patch.object(nws, "forecast_daily", return_value=[period]), \
                mock.patch.object(nws, "forecast_hourly", return_value=[]), \
                mock.patch.object(nws, "alerts", return_value=[]):
            _, us = self.get("/api/v1/forecast")
            api_pages._forecast_cache.clear()
            _, mt = self.get("/api/v1/forecast", replace(self.s, units="Metric"))
        self.assertEqual(us["periods"][0]["temp"], 104)
        self.assertEqual(mt["periods"][0]["temp"], 40)

    def test_forecast_failure_is_reported_not_raised(self):
        with mock.patch.object(nws, "points", side_effect=nws.NwsError("offline")):
            _, body = self.get("/api/v1/forecast")
        self.assertFalse(body["available"])

    def test_charts_have_temperature_points(self):
        self.seed_readings(180)
        _, body = self.get("/api/v1/charts/7")
        self.assertTrue(body["temp_points"])


if __name__ == "__main__":
    unittest.main()
