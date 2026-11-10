"""Endpoints added for the Android app's new pages (0.37.60)."""

import json
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from weatherlab import api, api_pages, stations, storage
from weatherlab.settings import Settings


class ParityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.db = storage.connect(self.tmp / "t.db")
        self.addCleanup(self.db.close)
        self.s = replace(Settings(), timezone="America/Phoenix", units="US", latitude=33.4, longitude=-112.0)
        self.now = time.time()
        p = mock.patch.object(api, "check_auth", lambda *a, **k: (True, ""))
        p.start()
        self.addCleanup(p.stop)

    def get(self, path):
        return api.route(path, "x", self.db, self.s, self.now, "t")

    def test_fire(self):
        self.assertFalse(self.get("/api/v1/fire")[1]["available"])
        rec = {"timestamp": "2026-11-10T10:51:00", "fwi": 20.2, "ffmc": 97.7, "dmc": 20.8, "dc": 39.9, "isi": 15.8,
               "bui": 20.7, "days_since_rain": 30,
               "forecast": [{"day": "Tue", "fwi": 20, "temperature": 90, "humidity": 10, "wind_speed": "5"},
                            {"day": "Wed", "fwi": 20.9, "temperature": 82, "humidity": 23, "wind_speed": "5"}]}
        storage.store_fire(self.db, rec, self.now)
        body = self.get("/api/v1/fire")[1]
        self.assertEqual(body["parts"][0], {"label": "Fire Weather Index", "value": 20.2, "note": ""})
        self.assertEqual(body["forecast"], [{"day": "Wed", "fwi": 20.9, "note": "82°F · 23% · 5 mph"}])

    def test_ask(self):
        body = self.get("/api/v1/ask/wettest%20month")[1]
        self.assertEqual(body["question"], "wettest month")
        self.assertIn("wettest month", body["examples"])
        self.assertIsInstance(body["answer"], str)

    def test_windmap_bad_hours(self):
        self.assertIn("error", self.get("/api/v1/windmap/7")[1])

    def test_windmap(self):
        frames = {"0": [(3.0, 180.0)] * 35, "3": [(12.0, 90.0)] * 35, "6": [], "12": []}
        with mock.patch("weatherlab.windmap.load", return_value={"frames": frames}):
            body = self.get("/api/v1/windmap/3")[1]
        self.assertEqual((body["rows"], body["cols"], len(body["points"])), (5, 7, 35))
        self.assertEqual(body["points"][0]["band"], 2)
        self.assertEqual(body["bands"][-1]["label"], "20+")

    def test_compare_two_stations(self):
        rows = [{"id": "main", "name": "Home"}, {"id": "yard", "name": "Back garden"}]
        dbs = {"main": self.tmp / "a.db", "yard": self.tmp / "b.db"}
        for sid, temp in (("main", 81.0), ("yard", 78.0)):
            d = storage.connect(dbs[sid])
            storage.store_reading(d, {"tempf": temp, "humidity": 20}, self.now - 60)
            d.close()
        current = {"id": "main"}

        class Using:
            def __init__(self, sid):
                self.sid = sid

            def __enter__(self):
                current["id"] = self.sid

            def __exit__(self, *a):
                current["id"] = "main"
        with mock.patch.object(stations, "all_stations", return_value=rows), \
                mock.patch.object(stations, "using", Using), \
                mock.patch.object(storage, "db_path", lambda: dbs[current["id"]]):
            body = self.get("/api/v1/compare/main/yard")[1]
            bad = self.get("/api/v1/compare/main/main")[1]
            listed = self.get("/api/v1/stations")[1]
        self.assertEqual((body["a"]["name"], body["b"]["name"]), ("Home", "Back garden"))
        self.assertIn("3", body["headline"])
        self.assertEqual(len(body["a"]["temps"]), 1)
        self.assertIn("error", bad)
        self.assertEqual(len(listed["stations"]), 2)


if __name__ == "__main__":
    unittest.main()
