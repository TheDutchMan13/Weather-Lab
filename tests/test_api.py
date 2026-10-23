"""The read-only API for the Android app: tokens, routes, lockout, unit conversion, and the server itself."""
import socket
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path
from unittest import mock

from weatherlab import api, storage
from weatherlab.settings import Settings

PHX = "America/Phoenix"


class FakeKeys:
    """Stands in for Windows Credential Manager."""
    def __init__(self):
        self.values = {}

    def get_key(self, name):
        return self.values.get(name, "")

    def set_key(self, name, value):
        self.values[name] = value


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.keys = FakeKeys()
        patcher = mock.patch.object(api, "keystore", self.keys)
        patcher.start()
        self.addCleanup(patcher.stop)
        api._failures, api._locked_until = 0, 0.0
        self.tmp = Path(tempfile.mkdtemp())
        self.db = storage.connect(self.tmp / "t.db")
        self.addCleanup(self.db.close)
        self.s = replace(Settings(), timezone=PHX, units="US")
        self.now = time.time()

    def token(self):
        return api.create_token()

    # --- tokens
    def test_token_is_stored_as_a_hash_and_checks_out(self):
        t = self.token()
        self.assertNotIn(t, self.keys.values.values())
        self.assertTrue(api.token_ok(f"Bearer {t}"))
        self.assertFalse(api.token_ok("Bearer wrong"))
        self.assertFalse(api.token_ok(None))
        self.assertFalse(api.token_ok(t))  # the Bearer word is required

    def test_no_token_means_nothing_gets_in(self):
        self.assertFalse(api.token_set())
        self.assertFalse(api.token_ok("Bearer anything"))

    def test_clearing_the_token_stops_access(self):
        t = self.token()
        api.clear_token()
        self.assertFalse(api.token_ok(f"Bearer {t}"))

    # --- routes
    def test_wrong_or_missing_token_is_401(self):
        self.token()
        code, body = api.route("/api/v1/status", None, self.db, self.s, self.now)
        self.assertEqual(code, 401)
        self.assertNotIn("Traceback", str(body))

    def test_unknown_path_is_404_for_a_good_token(self):
        t = self.token()
        code, _ = api.route("/api/v1/nope", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(code, 404)

    def test_status_with_no_readings(self):
        t = self.token()
        code, body = api.route("/api/v1/status", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(code, 200)
        self.assertIsNone(body["latest_reading_age_seconds"])
        self.assertEqual(body["api_version"], api.VERSION)

    def test_lockout_after_too_many_wrong_tokens(self):
        self.token()
        for _ in range(api.MAX_FAILURES):
            api.route("/api/v1/status", "Bearer nope", self.db, self.s, self.now)
        code, body = api.route("/api/v1/status", "Bearer nope", self.db, self.s, self.now)
        self.assertEqual(code, 429)
        self.assertIn("Try again in", body["error"])

    def test_a_good_token_clears_the_count(self):
        t = self.token()
        for _ in range(api.MAX_FAILURES - 1):
            api.route("/api/v1/status", "Bearer nope", self.db, self.s, self.now)
        api.route("/api/v1/status", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(api._failures, 0)

    # --- data
    def test_current_converts_to_metric_only_when_chosen(self):
        storage.store_reading(self.db, {"tempf": 212.0, "humidity": 40, "dailyrainin": 1.0}, ts=self.now - 60)
        t = self.token()
        _, us = api.route("/api/v1/current", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(us["reading"]["values"]["tempf"], {"value": 212.0, "unit": "°F"})
        self.assertEqual(us["reading"]["values"]["humidity"]["value"], 40)
        metric = replace(self.s, units="Metric")
        _, mt = api.route("/api/v1/current", f"Bearer {t}", self.db, metric, self.now)
        self.assertEqual(mt["reading"]["values"]["tempf"], {"value": 100.0, "unit": "°C"})
        self.assertTrue(mt["metric"])

    def test_today_reports_high_low_and_rain(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        local = datetime.fromtimestamp(self.now, ZoneInfo(PHX))
        midday = local.replace(hour=0, minute=5, second=0, microsecond=0).timestamp()
        if midday > self.now:
            midday = self.now - 60
        storage.store_reading(self.db, {"tempf": 90.0, "dailyrainin": 0.2}, ts=midday)
        storage.store_reading(self.db, {"tempf": 101.0, "dailyrainin": 0.5}, ts=midday + 1)
        t = self.token()
        _, body = api.route("/api/v1/today", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(body["high"]["value"], 101.0)
        self.assertEqual(body["low"]["value"], 90.0)
        self.assertEqual(body["rain"]["value"], 0.5)

    def test_alerts_are_listed_newest_first(self):
        storage.log_alert(self.db, self.now - 100, "Older")
        storage.log_alert(self.db, self.now - 10, "Newer")
        t = self.token()
        _, body = api.route("/api/v1/alerts", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(body["alerts"][0]["text"], "Newer")
        self.assertEqual(len(body["alerts"]), 2)

    def test_history_is_a_day_of_temperatures_in_the_chosen_units(self):
        storage.store_reading(self.db, {"tempf": 50.0}, ts=self.now - 7200)
        storage.store_reading(self.db, {"tempf": 212.0}, ts=self.now - 60)
        storage.store_reading(self.db, {"tempf": 10.0}, ts=self.now - 90000)  # older than a day: left out
        t = self.token()
        _, us = api.route("/api/v1/history", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual([p[1] for p in us["points"]], [50.0, 212.0])
        self.assertEqual(us["unit"], "°F")
        _, mt = api.route("/api/v1/history", f"Bearer {t}", self.db, replace(self.s, units="Metric"), self.now)
        self.assertEqual(mt["points"][-1][1], 100.0)
        self.assertEqual(mt["unit"], "°C")

    def test_week_has_seven_days_with_gaps_as_none(self):
        import json
        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        today = datetime.fromtimestamp(self.now, ZoneInfo(PHX)).date()
        yesterday = (today - timedelta(days=1)).isoformat()
        with self.db:
            self.db.execute("INSERT INTO daily (date, data) VALUES (?, ?)",
                            (yesterday, json.dumps({"tempf_max": 95.0, "tempf_min": 70.0, "rain_in": 0.25})))
        t = self.token()
        _, body = api.route("/api/v1/week", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(len(body["days"]), 7)
        self.assertEqual(body["days"][-1]["date"], today.isoformat())
        by_date = {d["date"]: d for d in body["days"]}
        self.assertEqual(by_date[yesterday]["high"], 95.0)
        self.assertEqual(by_date[yesterday]["rain"], 0.25)
        self.assertIsNone(body["days"][0]["high"])

    def test_storm_with_no_strikes(self):
        t = self.token()
        code, body = api.route("/api/v1/storm", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(code, 200)
        self.assertIsNone(body["last_strike"])
        self.assertEqual(body["trend"], "none")
        self.assertEqual(body["strikes_30m"], 0)

    def test_storm_reports_approaching_and_converts_distance(self):
        for minutes_ago, miles in [(18, 12.0), (15, 11.0), (8, 6.0), (4, 5.0)]:
            storage.store_strike(self.db, int(self.now - minutes_ago * 60), miles)
        t = self.token()
        _, body = api.route("/api/v1/storm", f"Bearer {t}", self.db, self.s, self.now)
        self.assertEqual(body["trend"], "approaching")
        self.assertEqual(body["strikes_30m"], 4)
        self.assertEqual(body["strikes_10m"], 2)
        self.assertEqual(body["last_strike"]["distance"], {"value": 5.0, "unit": "mi"})
        _, mt = api.route("/api/v1/storm", f"Bearer {t}", self.db, replace(self.s, units="Metric"), self.now)
        self.assertEqual(mt["last_strike"]["distance"]["unit"], "km")

    def test_storm_overhead_and_receding(self):
        storage.store_strike(self.db, int(self.now - 30), 0.5)
        self.assertEqual(api._trend(storage.strikes_between(self.db, self.now - 1800, self.now + 1), self.now), "overhead")
        self.assertEqual(api._trend([(self.now - 1000, 3.0), (self.now - 100, 9.0)], self.now), "receding")
        self.assertEqual(api._trend([(self.now - 3000, 3.0)], self.now), "none")

    # --- the server
    def test_server_starts_answers_and_stops(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        t = self.token()
        try:
            with mock.patch.object(api.stations, "current", return_value=api.stations.MAIN):
                api.ensure(True, port)
                self.assertEqual(api._running_port, port)
                req = urllib.request.Request(f"http://127.0.0.1:{port}/api/v1/status",
                                             headers={"Authorization": f"Bearer {t}"})
                with urllib.request.urlopen(req, timeout=5) as r:
                    self.assertEqual(r.status, 200)
                    self.assertIn(b"api_version", r.read())
                with self.assertRaises(urllib.error.HTTPError) as err:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/status", timeout=5)
                self.assertEqual(err.exception.code, 401)
        finally:
            api.ensure(False)
        self.assertIsNone(api._server)
        self.assertEqual(api.status_text(), "Not running. Turn it on above, and allow phones and devices.")

    def test_port_in_use_is_reported(self):
        busy = socket.socket()
        busy.bind(("0.0.0.0", 0))
        busy.listen(1)
        port = busy.getsockname()[1]
        try:
            api.ensure(True, port)
            self.assertIsNone(api._server)
            self.assertIn("in use", api.status_text())
        finally:
            api.ensure(False)
            busy.close()


if __name__ == "__main__":
    unittest.main()
