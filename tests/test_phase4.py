"""Phase 4 tests: comfort, lightning, storage for strikes and air quality, keys, and the AirNow map. No network."""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from weatherlab import airquality, comfort, lightning, secrets, storage
from weatherlab.config import RISK_COLORS

UTC = ZoneInfo("UTC")


class ComfortTests(unittest.TestCase):
    def test_heat_index_is_hotter_than_air_when_humid(self):
        self.assertGreater(comfort.heat_index_f(90, 60), 90)

    def test_wind_chill_is_colder_than_air(self):
        self.assertLess(comfort.wind_chill_f(20, 15), 20)

    def test_humidex_rises_with_dew_point(self):
        self.assertGreater(comfort.humidex_c(90, 75), comfort.humidex_c(90, 50))


class LightningTests(unittest.TestCase):
    now = datetime(2026, 10, 20, 12, 0, tzinfo=UTC)

    def live(self, distance, count="3"):
        return {"lightning": [{"distance": distance, "date": "2026-10-20T10:30:00", "count": count}]}

    def test_no_strike_returns_none(self):
        self.assertIsNone(lightning.parse_lightning({"lightning": []}, UTC, self.now, False))

    def test_miles_kept_as_is(self):
        out = lightning.parse_lightning(self.live("5 mi"), UTC, self.now, False)
        self.assertAlmostEqual(out["distance_mi"], 5.0, places=2)
        self.assertEqual(out["today"], 3)

    def test_km_switch_converts_to_miles(self):
        out = lightning.parse_lightning(self.live("10 mi"), UTC, self.now, True)
        self.assertAlmostEqual(out["distance_mi"], 6.214, places=2)

    def test_strike_from_earlier_day_has_no_today_count(self):
        live = {"lightning": [{"distance": "5 mi", "date": "2026-10-18T10:30:00", "count": "9"}]}
        out = lightning.parse_lightning(live, UTC, self.now, False)
        self.assertEqual(out["today"], 0)

    def test_absurd_distance_rejected(self):
        self.assertIsNone(lightning.parse_lightning(self.live("5000 mi"), UTC, self.now, False))


class StorageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self._tmp.name) / "test.db")

    def tearDown(self):
        self.db.close()
        self._tmp.cleanup()

    def test_strikes_store_once_and_query_by_range(self):
        storage.store_strike(self.db, 1000, 4.2)
        storage.store_strike(self.db, 1000, 4.2)  # duplicate ignored
        storage.store_strike(self.db, 2000, 9.0)
        self.assertEqual(storage.strikes_between(self.db, 0, 1500), [(1000, 4.2)])
        self.assertEqual(storage.latest_strike(self.db), (2000, 9.0))

    def test_no_strikes_gives_none(self):
        self.assertIsNone(storage.latest_strike(self.db))

    def test_aqi_round_trip(self):
        storage.store_aqi(self.db, {"aqi": 42, "category": "Good", "risk": "good"}, ts=500)
        ts, data = storage.latest_aqi(self.db)
        self.assertEqual(ts, 500)
        self.assertEqual(data["aqi"], 42)


class SecretsTests(unittest.TestCase):
    def test_get_key_returns_empty_when_keyring_fails(self):
        fake = mock.Mock()
        fake.get_password.side_effect = RuntimeError("no backend")
        with mock.patch.dict(sys.modules, {"keyring": fake}):
            self.assertEqual(secrets.get_key("airnow"), "")

    def test_set_and_get_use_service_name(self):
        fake = mock.Mock()
        fake.get_password.return_value = "abc"
        with mock.patch.dict(sys.modules, {"keyring": fake}):
            secrets.set_key("airnow", "abc")
            fake.set_password.assert_called_once_with(secrets.SERVICE, "airnow", "abc")
            self.assertEqual(secrets.get_key("airnow"), "abc")

    def test_blank_value_deletes(self):
        fake = mock.Mock()
        with mock.patch.dict(sys.modules, {"keyring": fake}):
            secrets.set_key("airnow", "")
            fake.delete_password.assert_called_once_with(secrets.SERVICE, "airnow")


class AirQualityMapTests(unittest.TestCase):
    def test_every_category_maps_to_a_known_risk_colour(self):
        for category, risk in airquality.CATEGORY_TO_RISK.items():
            self.assertIn(risk, RISK_COLORS, category)

    def test_pollutants_defined(self):
        self.assertIn("PM2.5", airquality.POLLUTANTS)


if __name__ == "__main__":
    unittest.main()
