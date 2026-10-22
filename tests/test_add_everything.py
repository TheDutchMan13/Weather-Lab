"""Tests for the features added in 0.22.0: NWS warning pushes, automatic reports, the reading archive, NOAA history,
the regional wind map, and the nearby airport reading. Nothing here calls the network."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from weatherlab import auto_reports, health_check, noaa, nws, nws_push, storage, windmap


class NwsPushTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(nws_push.stations, "folder", return_value=Path(self.tmp.name))
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_each_alert_is_sent_once(self):
        alert = {"event": "Heat Advisory", "headline": "Heat until 9 PM", "expires": "2026-10-22T21:00", "severity": "Moderate"}
        fresh, seen = nws_push.new_alerts([alert], [])
        self.assertEqual(len(fresh), 1)
        again, _ = nws_push.new_alerts([alert], seen)
        self.assertEqual(again, [])

    def test_seen_list_is_kept_short(self):
        alerts = [{"event": f"E{i}", "headline": "", "expires": str(i)} for i in range(nws_push.KEEP + 20)]
        _, seen = nws_push.new_alerts(alerts, [])
        self.assertEqual(len(seen), nws_push.KEEP)

    def test_message_and_urgency(self):
        self.assertEqual(nws_push.message({"event": "Flood Watch", "headline": "Rain tonight"}), "Flood Watch: Rain tonight")
        self.assertEqual(nws_push.message({"event": "Flood Watch", "headline": ""}), "Flood Watch")
        self.assertTrue(nws_push.is_urgent({"severity": "Extreme"}))
        self.assertTrue(nws_push.is_urgent({"severity": "Severe"}))
        self.assertFalse(nws_push.is_urgent({"severity": "Minor"}))

    def test_no_saved_list_means_first_run(self):
        self.assertIsNone(nws_push.load_seen())
        nws_push.save_seen(["a|b|c"])
        self.assertEqual(nws_push.load_seen(), ["a|b|c"])


class AutoReportTests(unittest.TestCase):
    def test_monthly_report_waits_until_the_second_day(self):
        self.assertEqual(auto_reports.due(date(2026, 11, 1), set()), [])
        names = [name for name, *_ in auto_reports.due(date(2026, 11, 2), set())]
        self.assertEqual(names, ["weather_report_2026_10.pdf"])

    def test_january_also_makes_last_years_report(self):
        got = auto_reports.due(date(2026, 1, 2), set())
        self.assertEqual([(kind, year, month) for _, kind, year, month in got], [("monthly", 2025, 12), ("yearly", 2025, 0)])

    def test_existing_reports_are_not_made_again(self):
        existing = {"weather_report_2026_10.pdf"}
        self.assertEqual(auto_reports.due(date(2026, 11, 2), existing), [])

    def test_month_ranges(self):
        self.assertEqual(auto_reports.month_range(2026, 2), (date(2026, 2, 1), date(2026, 2, 28)))
        self.assertEqual(auto_reports.month_range(2028, 2)[1], date(2028, 2, 29))
        self.assertEqual(auto_reports.month_range(2026, 12)[1], date(2026, 12, 31))


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = storage.connect(Path(self.tmp.name) / "test.db")
        with self.db:
            for ts in (1000, 2000, 3000, 9000):
                self.db.execute("INSERT INTO readings (ts, data) VALUES (?, ?)", (ts, '{"tempf": 70}'))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_old_readings_move_and_nothing_is_lost(self):
        moved = storage.archive_before(self.db, 5000)
        self.assertEqual(moved, 3)
        left = self.db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        archived = self.db.execute("SELECT COUNT(*) FROM readings_archive").fetchone()[0]
        self.assertEqual((left, archived), (1, 3))

    def test_reads_still_see_archived_readings(self):
        storage.archive_before(self.db, 5000)
        found = [ts for ts, _ in storage.readings_between(self.db, 0, 10_000)]
        self.assertEqual(found, [1000, 2000, 3000, 9000])

    def test_archiving_twice_is_harmless(self):
        storage.archive_before(self.db, 5000)
        self.assertEqual(storage.archive_before(self.db, 5000), 0)


class NoaaTests(unittest.TestCase):
    def test_nearest_station_is_picked(self):
        results = [{"id": "GHCND:FAR", "name": "Far", "latitude": 34.0, "longitude": -112.0},
                   {"id": "GHCND:NEAR", "name": "Near", "latitude": 33.45, "longitude": -112.07},
                   {"id": "GHCND:BAD", "name": "No position"}]
        station_id, name, km = noaa.nearest_station(results, 33.43, -112.01)
        self.assertEqual((station_id, name), ("GHCND:NEAR", "Near"))
        self.assertLess(km, 10)

    def test_no_stations_gives_none(self):
        self.assertIsNone(noaa.nearest_station([], 33.4, -112.0))

    def test_distance_is_zero_for_the_same_point(self):
        self.assertAlmostEqual(noaa.distance_km(33.4, -112.0, 33.4, -112.0), 0.0)

    def test_daily_rows_are_grouped_by_day(self):
        items = [{"datatype": "PRCP", "date": "2026-01-05T00:00:00", "value": 2.54},
                 {"datatype": "TMAX", "date": "2026-01-05T00:00:00", "value": 75.0},
                 {"datatype": "SNOW", "date": "2026-01-05T00:00:00", "value": 1.0},
                 {"datatype": "TMIN", "date": "2026-01-05T00:00:00", "value": None}]
        days = noaa.parse_daily(items)
        self.assertEqual(days, {"2026-01-05": {"source": "noaa", "rain_in": 2.54, "tempf_max": 75.0}})


class WindMapTests(unittest.TestCase):
    def test_grid_has_one_point_per_cell_and_the_station_in_the_middle(self):
        points = windmap.grid_points(33.4, -112.0)
        self.assertEqual(len(points), windmap.ROWS * windmap.COLS)
        self.assertEqual(points[(windmap.ROWS // 2) * windmap.COLS + windmap.COLS // 2], (33.4, -112.0))

    def test_bands(self):
        self.assertEqual(windmap.band(0), 0)
        self.assertEqual(windmap.band(None), 0)
        self.assertEqual(windmap.band(7), 1)
        self.assertEqual(windmap.band(25), len(windmap.BANDS) - 1)

    def test_arrows_point_where_the_wind_goes(self):
        self.assertEqual(windmap.toward(0), 180)  # wind from the north blows to the south
        self.assertEqual(windmap.toward(270), 90)
        self.assertIn("rotate(180deg)", windmap.arrow_html(3, 0))
        self.assertIn(windmap.BANDS[0][1], windmap.arrow_html(3, 0))

    def test_request_asks_for_mph(self):
        self.assertIn("wind_speed_unit=mph", windmap.url_for([(33.4, -112.0)]))

    def test_frames_per_time(self):
        hours = [f"2026-10-22T{h:02d}:00" for h in range(8, 24)]
        data = [{"hourly": {"time": hours, "wind_speed_10m": list(range(len(hours))),
                            "wind_direction_10m": [90] * len(hours)}}] * 2
        frames = windmap.frames_from(data, "2026-10-22T08:00")
        self.assertEqual(frames["0"], [(0, 90), (0, 90)])
        self.assertEqual(frames["3"], [(3, 90), (3, 90)])
        self.assertEqual(frames["12"], [(12, 90), (12, 90)])

    def test_fresh_saved_copy_is_used_without_a_request(self):
        saved = {"lat": 33.4, "lon": -112.0, "fetched": 1000.0, "frames": {"0": []}}
        with mock.patch.object(windmap, "_saved", return_value=saved), mock.patch.object(windmap, "_fetch") as fetch:
            self.assertIs(windmap.load(33.4, -112.0, 1500.0, None), saved)
        fetch.assert_not_called()


class NearbyAirportTests(unittest.TestCase):
    FEATURES = {"features": [
        {"properties": {"stationIdentifier": "KXYZ", "name": "Corner Field"}, "geometry": {"coordinates": [-112.0, 33.41]}},
        {"properties": {"stationIdentifier": "KPHX", "name": "Phoenix Sky Harbor Airport"},
         "geometry": {"coordinates": [-112.01, 33.44]}},
    ]}

    def test_airport_is_preferred_when_nearby(self):
        with mock.patch.object(nws, "_get", return_value=self.FEATURES):
            found = nws.nearest_airport_station("https://example/stations", 33.43, -112.0, "")
        self.assertEqual(found["id"], "KPHX")
        self.assertTrue(found["airport"])

    def test_nearest_station_used_when_no_airport_is_close(self):
        far = {"features": [{"properties": {"stationIdentifier": "KFAR", "name": "Distant Airport"},
                             "geometry": {"coordinates": [-100.0, 40.0]}}] + self.FEATURES["features"][:1]}
        with mock.patch.object(nws, "_get", return_value=far):
            found = nws.nearest_airport_station("https://example/stations", 33.43, -112.0, "")
        self.assertEqual(found["id"], "KXYZ")
        self.assertFalse(found["airport"])

    def test_compass_points(self):
        self.assertEqual(nws.compass(0), "N")
        self.assertEqual(nws.compass(225), "SW")
        self.assertEqual(nws.compass(359), "N")
        self.assertEqual(nws.compass(None), "")

    def test_observation_is_converted_to_us_units(self):
        data = {"properties": {"timestamp": "2026-10-22T15:00:00+00:00", "textDescription": "Sunny",
                               "temperature": {"value": 30.0}, "relativeHumidity": {"value": 12.0},
                               "windSpeed": {"value": 16.09344}, "windGust": {"value": None},
                               "windDirection": {"value": 270}}}
        got = nws.parse_observation(data)
        self.assertAlmostEqual(got["temp_f"], 86.0)
        self.assertAlmostEqual(got["wind_mph"], 10.0, places=3)
        self.assertIsNone(got["gust_mph"])
        self.assertEqual(got["text"], "Sunny")

    def test_points_lists_the_observation_stations(self):
        points = {"properties": {"forecast": "https://x/forecast", "forecastZone": "https://x/zones/forecast/AZZ540",
                                 "observationStations": "https://x/gridpoints/PSR/1,2/stations"}}
        with mock.patch.object(nws, "_get", return_value=points):
            got = nws.points(33.4, -112.0, "")
        self.assertEqual(got["stations"], "https://x/gridpoints/PSR/1,2/stations")


class HealthTests(unittest.TestCase):
    def test_new_checks_appear_only_when_turned_on(self):
        names = [c["name"] for c in health_check.evaluate({}, 0)]
        self.assertNotIn("Weather warnings", names)
        checks = health_check.evaluate({"nws_on": True, "nws_error": "No connection", "reports_on": True,
                                        "archive_days": 30}, 0)
        by_name = {c["name"]: c["state"] for c in checks}
        self.assertEqual(by_name["Weather warnings"], "warn")
        self.assertEqual(by_name["Automatic reports"], "ok")
        self.assertEqual(by_name["Reading archive"], "ok")


if __name__ == "__main__":
    unittest.main()
