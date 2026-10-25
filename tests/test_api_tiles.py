"""The data behind the Android Live tiles (Weather Lab 0.37.8)."""
import unittest
from unittest import mock

from tests.test_api_pages import ApiHelpers
from weatherlab import api_pages, nws, storage


class TilesApiTests(ApiHelpers, unittest.TestCase):
    def test_tiles_series_peaks_and_pressure(self):
        for m in range(0, 400, 5):
            ts = int(self.now - m * 60)
            storage.store_reading(self.db, {"humidity": 30.0 + m / 100, "windspeedmph": 5.0, "windgustmph": 9.0 + (m == 10) * 4,
                                            "baromrelin": 29.00 + (400 - m) / 4000, "uv": 3.0, "solarradiation": 500.0}, ts)
        code, body = self.get("/api/v1/tiles")
        self.assertEqual(code, 200)
        self.assertEqual(set(body["series"]), {"humidity", "windspeedmph", "windgustmph", "baromrelin", "solarradiation",
                                               "tempinf", "humidityin", "uv", "rainratein", "dailyrainin", "dewpointf"})
        self.assertGreater(len(body["series"]["uv"]), 2)
        self.assertEqual(body["series"]["dailyrainin"], [])
        self.assertGreater(len(body["series"]["humidity"]), 2)
        self.assertEqual(body["peaks"]["uv"], 3.0)
        self.assertEqual(body["peaks"]["windgustmph"], 13.0)
        self.assertIn(body["pressure"]["word"], ("rising", "rising fast", "steady"))

    def test_tiles_empty_database(self):
        code, body = self.get("/api/v1/tiles")
        self.assertEqual(code, 200)
        self.assertEqual(body["series"]["humidity"], [])
        self.assertIsNone(body["pressure"])
        self.assertIsNone(body["peaks"]["uv"])

    def test_observation_visibility_and_airport(self):
        obs = nws.parse_observation({"properties": {"visibility": {"value": 16093.44}, "presentWeather": [{"weather": "haze"}]}})
        self.assertAlmostEqual(obs["visibility_mi"], 10.0, places=1)
        self.assertEqual(obs["present"], ["haze"])
        station = {"id": "KGYR", "name": "Goodyear", "airport": True, "km": 5}
        with mock.patch.object(nws, "points", return_value={"stations": "u"}), \
                mock.patch.object(nws, "nearest_airport_station", return_value=station), \
                mock.patch.object(nws, "latest_observation", return_value=obs):
            body = api_pages.airport(self.db, self.s, self.now)
        self.assertEqual(body["visibility"]["unit"], "mi")
        self.assertEqual(body["present"], ["haze"])


if __name__ == "__main__":
    unittest.main()
