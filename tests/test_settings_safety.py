"""Settings files that are damaged or hold wrong values (0.37.55)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from weatherlab import settings
from weatherlab.settings import Settings


class FromDictTests(unittest.TestCase):
    def test_good_values_are_kept(self):
        s, bad = settings.from_dict({"station_ip": "192.168.1.5", "latitude": 33.4, "quiet_start": 22,
                                     "theme_mode": "dark", "alert_rules": [{"metric": "tempf"}]})
        self.assertEqual((s.station_ip, s.latitude, s.quiet_start, s.theme_mode), ("192.168.1.5", 33.4, 22, "dark"))
        self.assertEqual(bad, [])

    def test_wrong_values_fall_back_one_by_one(self):
        s, bad = settings.from_dict({"station_ip": "192.168.1.5", "frost_threshold_f": 50, "theme_mode": "purple",
                                     "quiet_start": "ten", "backup_enabled": "yes", "latitude": 95})
        self.assertEqual(s.station_ip, "192.168.1.5")
        self.assertEqual(s.frost_threshold_f, Settings().frost_threshold_f)
        self.assertEqual(s.theme_mode, "auto")
        self.assertEqual(sorted(bad), ["backup_enabled", "frost_threshold_f", "latitude", "quiet_start", "theme_mode"])

    def test_not_an_object(self):
        self.assertEqual(settings.from_dict([])[1], ["(the whole file)"])

    def test_whole_number_floats_are_fine_for_ints(self):
        s, bad = settings.from_dict({"quiet_start": 22.0})
        self.assertEqual((s.quiet_start, bad), (22, []))


class FileTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "settings.json"
        self._patch = mock.patch.object(settings, "settings_path", return_value=self.path)
        self._patch.start()

    def tearDown(self):
        self._patch.stop()
        self._tmp.cleanup()

    def test_save_is_atomic_and_round_trips(self):
        settings.save_settings(Settings(station_ip="10.0.0.2"))
        self.assertFalse(self.path.with_name("settings.json.tmp").exists())
        self.assertEqual(settings.load_settings().station_ip, "10.0.0.2")
        self.assertEqual(settings.load_problem, "")

    def test_damaged_file_is_kept_and_reported(self):
        self.path.write_text('{"station_ip": "10.0', encoding="utf-8")
        s = settings.load_settings()
        self.assertEqual(s, Settings())
        self.assertIn("damaged", settings.load_problem)
        self.assertTrue(self.path.with_name("settings.json.bad").exists())

    def test_hand_edited_list_does_not_crash(self):
        self.path.write_text("[]", encoding="utf-8")
        self.assertEqual(settings.load_settings(), Settings())

    def test_one_bad_value_is_reported(self):
        self.path.write_text(json.dumps({"station_ip": "10.0.0.2", "theme_mode": "purple"}), encoding="utf-8")
        s = settings.load_settings()
        self.assertEqual(s.station_ip, "10.0.0.2")
        self.assertIn("theme_mode", settings.load_problem)


if __name__ == "__main__":
    unittest.main()
