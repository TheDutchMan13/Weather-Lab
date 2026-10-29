"""Compare stations (0.37.34): the numbers for each station and the gap between them."""
import unittest

from weatherlab import station_compare as sc

NOW = 1_000_000


def readings(*temps, gust=5, hum=30):
    return [(NOW - 600 * (len(temps) - i), {"tempf": t, "humidity": hum, "windgustmph": gust + i, "dailyrainin": 0.1})
            for i, t in enumerate(temps)]


class StationCompareTests(unittest.TestCase):
    def test_summarize(self):
        s = sc.summarize("Home", readings(70, 80, 75), NOW)
        self.assertEqual((s["high"], s["low"], s["count"]), (80, 70, 3))
        self.assertEqual(s["now"]["tempf"], 75)
        self.assertEqual(s["age_seconds"], 600)
        self.assertEqual(s["gust_max"], 7)

    def test_summarize_empty(self):
        s = sc.summarize("Shed", [], NOW)
        self.assertIsNone(s["age_seconds"])
        self.assertEqual(s["now"], {})

    def test_rows_us(self):
        a = sc.summarize("Home", readings(80), NOW)
        b = sc.summarize("Shed", readings(75), NOW)
        row = next(r for r in sc.rows(a, b, False) if r["label"] == "Temperature")
        self.assertEqual((row["a"], row["b"], row["diff"]), ("80.0 °F", "75.0 °F", "+5.0°F"))

    def test_rows_metric_difference_has_no_offset(self):
        a = sc.summarize("Home", readings(86), NOW)
        b = sc.summarize("Shed", readings(68), NOW)
        row = next(r for r in sc.rows(a, b, True) if r["label"] == "Temperature")
        self.assertEqual(row["diff"], "+10.0°C")  # 18 °F apart is 10 °C apart

    def test_same_and_missing(self):
        a = sc.summarize("Home", readings(70), NOW)
        b = sc.summarize("Shed", [], NOW)
        self.assertEqual(next(r for r in sc.rows(a, b, False) if r["label"] == "Humidity")["diff"], "--")
        self.assertEqual(next(r for r in sc.rows(a, a, False) if r["label"] == "Humidity")["diff"], "same")

    def test_headline(self):
        a = sc.summarize("Home", readings(80), NOW)
        b = sc.summarize("Shed", readings(75), NOW)
        self.assertEqual(sc.headline(a, b, False), "Home is 5.0°F warmer than Shed right now.")
        self.assertEqual(sc.headline(b, b, False), "Shed and Shed are at the same temperature.")
        self.assertIn("No recent temperature from Shed", sc.headline(a, sc.summarize("Shed", [], NOW), False))

    def test_age_text(self):
        self.assertEqual([sc.age_text(s) for s in (None, 30, 600, 7200, 200000)],
                         ["no readings yet", "just now", "10 min ago", "2 h ago", "2 d ago"])


if __name__ == "__main__":
    unittest.main()


class TwoStationDatabaseTests(unittest.TestCase):
    """Each station keeps its own database; reading both one after the other gives each its own numbers."""

    def test_read_two_stations(self):
        import os
        import tempfile
        import time
        from weatherlab import stations, storage
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("APPDATA")
            os.environ["APPDATA"] = tmp
            try:
                shed = stations.add_station("Shed")["id"]
                now = time.time()
                for station, temp in ((stations.MAIN, 80.0), (shed, 74.0)):
                    with stations.using(station):
                        db = storage.connect()
                        storage.store_reading(db, {"tempf": temp, "humidity": 20}, now - 120)
                        db.close()
                found = {}
                for station in (stations.MAIN, shed):
                    with stations.using(station):
                        db = storage.connect()
                        found[station] = sc.summarize(stations.name_of(station),
                                                      storage.readings_between(db, now - 86400, now + 1), now)
                        db.close()
                self.assertEqual(found[stations.MAIN]["now"]["tempf"], 80.0)
                self.assertEqual(found[shed]["now"]["tempf"], 74.0)
                self.assertEqual(sc.headline(found[stations.MAIN], found[shed], False),
                                 "Home is 6.0°F warmer than Shed right now.")
            finally:
                if old is None:
                    os.environ.pop("APPDATA", None)
                else:
                    os.environ["APPDATA"] = old
