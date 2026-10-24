"""The Android app's history and public-source pages (Weather Lab 0.37.0)."""
import json
import unittest
from datetime import timedelta
from unittest import mock

from tests.test_api_pages import ApiHelpers
from weatherlab import api_pages, nws, storage, tropics


class HistoryApiTests(ApiHelpers, unittest.TestCase):
    def put_day(self, d, **data):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO daily (date, data) VALUES (?, ?)", (d.isoformat(), json.dumps(data)))

    def test_on_this_day(self):
        for y in (2024, 2025):
            self.put_day(self.today.replace(year=y), tempf_max=100 + y - 2024, tempf_min=70, rain_in=0.1)
        code, body = self.get("/api/v1/onthisday/today")
        self.assertEqual(code, 200)
        self.assertEqual([r["year"] for r in body["years"]], [2025, 2024])
        self.assertEqual(body["record_high"], 101)
        self.assertIn("error", self.get("/api/v1/onthisday/nope")[1])

    def test_compare_and_milestones(self):
        self.put_day(self.today - timedelta(days=3), tempf_max=102, tempf_min=30, rain_in=0.4)
        self.put_day(self.today - timedelta(days=2), tempf_max=91, tempf_min=50, rain_in=0.0)
        _, body = self.get("/api/v1/compare")
        self.assertEqual(body["heat_days"][0]["days_100"], 1)
        self.assertEqual(len(body["months"]), 12)
        _, ms = self.get("/api/v1/milestones")
        by = {m["key"]: m for m in ms["milestones"]}
        self.assertEqual(by["freeze"]["years"][0]["count"], 1)
        self.assertEqual(by["90"]["years"][0]["count"], 2)
        self.assertEqual(by["100"]["years"][0]["count"], 1)

    def test_month_and_year(self):
        self.seed_days()
        month = (self.today - timedelta(days=1)).strftime("%Y-%m")
        _, card = self.get(f"/api/v1/month/{month}")
        self.assertTrue(card["found"])
        self.assertGreaterEqual(card["days_with_data"], 1)
        self.assertEqual(self.get("/api/v1/month/2001-01")[1]["found"], False)
        self.assertIn("error", self.get("/api/v1/month/bad")[1])
        _, year = self.get(f"/api/v1/year/{self.today.year}")
        self.assertTrue(year["found"] or year["days_with_data"] == 0)
        self.assertIn("error", self.get("/api/v1/year/abc")[1])

    def test_year_runs(self):
        for n, rain in enumerate([0.0, 0.0, 0.0, 0.2, 0.3], start=1):
            self.put_day(self.today.replace(month=1, day=n) if self.today.month == 1 else self.today.replace(month=1, day=n),
                         tempf_max=70, tempf_min=40, rain_in=rain)
        _, y = self.get(f"/api/v1/year/{self.today.year}")
        self.assertEqual(y["longest_dry"]["days"], 3)
        self.assertEqual(y["longest_wet"]["days"], 2)

    def test_metric_units_convert(self):
        from dataclasses import replace
        self.put_day(self.today - timedelta(days=1), tempf_max=104, tempf_min=68, rain_in=1.0)
        _, body = self.get(f"/api/v1/month/{(self.today - timedelta(days=1)).strftime('%Y-%m')}", replace(self.s, units="Metric"))
        self.assertEqual(body["hottest"]["value"], 40.0)
        self.assertEqual(body["rain_unit"], "mm")

    def test_alert_history_and_export(self):
        storage.log_alert(self.db, self.now - 3600, "Heat warning")
        storage.log_alert(self.db, self.now - 20 * 86400, "Old one")
        _, body = self.get("/api/v1/alerts/history")
        self.assertEqual([a["text"] for a in body["alerts"]], ["Heat warning"])
        self.seed_days()
        _, csv = self.get("/api/v1/export/daily")
        self.assertTrue(csv["csv"].startswith("date,high_f"))
        self.assertEqual(len(csv["csv"].strip().splitlines()), 5)

    def test_forecast_accuracy(self):
        self.seed_days()
        yesterday = self.today - timedelta(days=1)
        storage.store_forecasts(self.db, {yesterday.isoformat(): {"high": 98.0}})
        _, body = self.get("/api/v1/forecast/accuracy")
        self.assertEqual(body["days"], 1)
        self.assertEqual(body["rows"][0]["miss"], -2.0)

    def test_anomalies_and_rewind(self):
        self.seed_readings(minutes=1)
        for h in range(48, 600):
            storage.store_reading(self.db, {"tempf": 70.0 + (h % 5), "humidity": 40.0 + (h % 3), "windgustmph": 8.0 + (h % 4),
                                            "baromrelin": 29.9 + (h % 2) * 0.01}, int(self.now - h * 3600 / 2 * 1.0))
        storage.store_reading(self.db, {"tempf": 130.0, "humidity": 41.0, "windgustmph": 9.0, "baromrelin": 29.9}, int(self.now - 600))
        _, body = self.get("/api/v1/anomalies")
        self.assertIn("Temperature", [a["label"] for a in body["anomalies"]])
        day = self.today.isoformat()
        _, rw = self.get(f"/api/v1/rewind/{day}")
        self.assertIn("series", rw)
        self.assertIn("error", self.get("/api/v1/rewind/yesterday")[1])

    def test_airport_needs_location(self):
        from dataclasses import replace
        _, body = self.get("/api/v1/airport", replace(self.s, latitude=None, longitude=None))
        self.assertFalse(body["available"])

    def test_airport_compares(self):
        self.seed_readings(minutes=2)
        station = {"id": "KPHX", "name": "Phoenix Sky Harbor Intl Airport", "km": 16.09, "airport": True}
        obs = {"time": "t", "text": "Clear", "temp_f": 88.0, "humidity": 25.0, "wind_mph": 5.0, "gust_mph": None, "direction": 90.0}
        with mock.patch.object(nws, "points", return_value={"stations": "u"}), \
                mock.patch.object(nws, "nearest_airport_station", return_value=station), \
                mock.patch.object(nws, "latest_observation", return_value=obs):
            api_pages._cache.clear()
            _, body = self.get("/api/v1/airport")
        self.assertTrue(body["available"])
        self.assertEqual(body["distance"], 10.0)
        self.assertEqual(body["rows"][0]["station"], 90.0)
        self.assertEqual(body["rows"][0]["airport"], 88.0)

    def test_tropics(self):
        cache = {"ok": True, "checked": "now", "storms": [{"name": "Test", "class": "TS", "wind_mph": 50, "miles": 800,
                                                              "direction": "SW", "move": "N at 5 mph"}]}
        with mock.patch.object(tropics, "refresh", return_value=cache):
            _, body = self.get("/api/v1/tropics")
        self.assertEqual(body["storms"][0]["distance"], 800)

    def test_radar(self):
        with mock.patch.object(nws, "points", return_value={"radar": "KIWA"}):
            api_pages._cache.clear()
            _, body = self.get("/api/v1/radar")
        self.assertTrue(body["local_loop"].endswith("KIWA_loop.gif"))

    def test_air_needs_key(self):
        _, body = self.get("/api/v1/air")
        self.assertFalse(body["available"])

    def test_push_info(self):
        _, body = self.get("/api/v1/push")
        self.assertEqual(body["server"], "https://ntfy.sh")


if __name__ == "__main__":
    unittest.main()
