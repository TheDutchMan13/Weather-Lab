"""Tests for stations: each station's own database, settings, alert topic and backup copies."""

import os
import tempfile
import unittest
from pathlib import Path

from weatherlab import backup, push, settings, stations, storage


class StationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old = os.environ.get("APPDATA")
        os.environ["APPDATA"] = self._tmp.name

    def tearDown(self) -> None:
        if self._old is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old
        self._tmp.cleanup()

    def test_main_station_keeps_the_original_paths(self) -> None:
        root = Path(self._tmp.name) / "WeatherLab"
        self.assertEqual(storage.db_path(), root / "weatherlab.db")
        self.assertEqual(settings.settings_path(), root / "settings.json")

    def test_new_station_has_its_own_database_and_settings(self) -> None:
        row = stations.add_station("Back garden")
        with stations.using(row["id"]):
            folder = stations.base_dir() / "stations" / row["id"]
            self.assertEqual(storage.db_path(), folder / "weatherlab.db")
            self.assertEqual(settings.settings_path(), folder / "settings.json")
        self.assertEqual(storage.db_path(), stations.base_dir() / "weatherlab.db")

    def test_names_become_ids_and_the_main_station_comes_first(self) -> None:
        row = stations.add_station("Back Garden!")
        self.assertEqual(row["id"], "back-garden")
        self.assertEqual(stations.ids(), ["main", "back-garden"])

    def test_a_name_that_clashes_with_the_main_station_gets_a_number(self) -> None:
        row = stations.add_station("Main")
        self.assertNotEqual(row["id"], "main")
        self.assertIn(row["id"], stations.ids())

    def test_adding_a_removed_station_again_brings_its_folder_back(self) -> None:
        row = stations.add_station("Shed")
        marker = stations.folder(row["id"]) / "weatherlab.db"
        marker.write_text("old readings", encoding="utf-8")
        stations.remove_station(row["id"])
        self.assertNotIn(row["id"], stations.ids())
        again = stations.add_station("Shed")
        self.assertEqual(again["id"], row["id"])
        self.assertTrue(marker.exists())

    def test_the_main_station_cannot_be_removed(self) -> None:
        with self.assertRaises(ValueError):
            stations.remove_station(stations.MAIN)

    def test_rename_keeps_the_id(self) -> None:
        row = stations.add_station("Field")
        stations.rename_station(row["id"], "North field")
        self.assertEqual(stations.name_of(row["id"]), "North field")
        self.assertIn(row["id"], stations.ids())

    def test_using_puts_the_previous_station_back(self) -> None:
        row = stations.add_station("Roof")
        self.assertEqual(stations.current(), stations.MAIN)
        with stations.using(row["id"]):
            self.assertEqual(stations.current(), row["id"])
        self.assertEqual(stations.current(), stations.MAIN)

    def test_each_station_has_its_own_alert_topic(self) -> None:
        self.assertEqual(push.topic_key("main"), push.TOPIC_KEY)
        self.assertEqual(push.topic_key("back-garden"), push.TOPIC_KEY + ":back-garden")

    def test_damaged_registry_falls_back_to_the_main_station(self) -> None:
        path = stations._registry_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json", encoding="utf-8")
        self.assertEqual(stations.ids(), [stations.MAIN])

    def test_copies_for_a_station_go_into_its_own_subfolder(self) -> None:
        row = stations.add_station("Lake")
        source = Path(self._tmp.name) / "weatherlab-20261021-120000.db"
        from tests.test_backup import make_db
        make_db(source, 3)  # copies are checked from 0.37.54, so this has to be a real database
        target = Path(self._tmp.name) / "usb"
        with stations.using(row["id"]):
            backup.copy_to_folder(source, str(target), 5)
        self.assertTrue((target / row["id"] / source.name).exists())
        self.assertFalse((target / source.name).exists())

    def test_collector_knows_its_station_and_can_stop(self) -> None:
        from weatherlab.poller import Poller
        collector = Poller("back-garden")
        self.assertEqual(collector.station, "back-garden")
        collector.stop()
        self.assertTrue(collector._stop_event.is_set())


if __name__ == "__main__":
    unittest.main()
