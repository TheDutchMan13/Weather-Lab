"""Tests for the features added in 0.22.0: NWS warning pushes, automatic reports, the reading archive, NOAA history,
the regional wind map, and the nearby airport reading. Nothing here calls the network."""

import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from weatherlab import auto_reports, health_check, history_series, noaa, nws, nws_push, record_board, storage, windmap


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


class HealthGroupTests(unittest.TestCase):
    def test_every_check_is_in_exactly_one_group(self):
        names = [name for _, names in health_check.GROUPS for name in names]
        self.assertEqual(len(names), len(set(names)))
        checks = [{"name": n, "state": "ok", "detail": ""} for n in names] + [{"name": "New one", "state": "ok", "detail": ""}]
        groups = health_check.grouped(checks)
        self.assertEqual(sum(len(rows) for _, rows in groups), len(checks))
        self.assertEqual(groups[-1][0], "Other")

    def test_groups_keep_their_order_and_skip_empty_ones(self):
        checks = [{"name": "Updates", "state": "info", "detail": ""}, {"name": "Database", "state": "ok", "detail": ""}]
        self.assertEqual([title for title, _ in health_check.grouped(checks)], ["Storage", "This app"])


class DashboardPaletteTests(unittest.TestCase):
    """Read from the source, so these run without Streamlit or Plotly installed."""
    ROOT = Path(__file__).resolve().parent.parent

    def _source(self, name):
        return (self.ROOT / "weatherlab" / name).read_text(encoding="utf-8")

    def test_measures_use_the_dashboard_colours(self):
        text = self._source("charts.py")
        self.assertIn('"temp": PAL["amber"]', text)
        self.assertIn('"rain": PAL["violet"]', text)
        self.assertIn('"wind": PAL["quiet"]', text)
        self.assertIn('CHART_COLORS = ["#8a5cf0", "#2e9e63", "#e8a53c", "#fb923c", "#f87171", "#dc2626"]', text)

    def test_accent_is_the_dashboard_blue(self):
        self.assertIn('ACCENT_COLOR = "#4ea1ff"', self._source("config.py"))
        theme_text = self._source("theme.py")
        self.assertNotIn("#4a9eff", theme_text)
        self.assertNotIn("#58a6ff", theme_text)


class HistorySeriesTests(unittest.TestCase):
    def test_thin_keeps_the_latest_reading_in_each_bucket(self):
        points = [(0, 1.0), (300, 2.0), (600, 3.0), (900, 4.0), (1200, 5.0)]
        self.assertEqual(history_series.thin(points, 600), [(300, 2.0), (900, 4.0), (1200, 5.0)])

    def test_summary_gives_highest_lowest_and_average(self):
        got = history_series.summary([(10, 60.0), (20, 75.0), (30, 50.0)])
        self.assertEqual(got["high"], (20, 75.0))
        self.assertEqual(got["low"], (30, 50.0))
        self.assertAlmostEqual(got["average"], 61.6667, places=3)
        self.assertIsNone(history_series.summary([]))


class RecordBoardTests(unittest.TestCase):
    TODAY = date(2026, 10, 22)

    def _days(self):
        # 10 dry days, a 3-day wet spell ending Jun 14, then 2 dry days; plus a rainy September and an October so far
        out = []
        start = date(2026, 6, 1)
        for i in range(10):
            out.append((start + timedelta(days=i), {"rain_in": 0.0, "tempf_max": 90.0 + i, "tempf_min": 60.0,
                                                    "gust_max": 10.0 + i, "humidity_max": 50.0, "humidity_min": 20.0,
                                                    "baro_max": 29.9, "baro_min": 29.8, "uvi": 9.0,
                                                    "wind_run_mi": 20.0, "wind_max": 8.0, "rainrate_max": 0.0}))
        out.append((date(2026, 6, 11), {"rain_in": 0.5, "tempf_max": 80.0, "tempf_min": 65.0, "rainrate_max": 1.0}))
        out.append((date(2026, 6, 12), {"rain_in": 0.2, "tempf_max": 82.0, "tempf_min": 66.0, "rainrate_max": 0.4}))
        out.append((date(2026, 6, 13), {"rain_in": 0.1, "tempf_max": 84.0, "tempf_min": 64.0, "rainrate_max": 0.3}))
        out.append((date(2026, 6, 14), {"rain_in": 0.0, "tempf_max": 99.0, "tempf_min": 61.0}))
        out.append((date(2026, 9, 5), {"rain_in": 1.25, "tempf_max": 95.0, "tempf_min": 70.0}))
        out.append((date(2026, 10, 3), {"rain_in": 0.75, "tempf_max": 88.0, "tempf_min": 62.0}))
        return out

    def test_highlights_and_groups(self):
        got = record_board.board(self._days(), self.TODAY)
        names = [h["name"] for h in got["highlights"]]
        self.assertEqual(names, ["hi_temp", "lo_temp", "uv_hi", "wet_day", "gust_hi", "dry_spell"])
        self.assertEqual([title for title, _ in got["groups"]], ["Temperature", "Rain", "Wind", "Humidity and pressure"])
        self.assertTrue(all(r["group"] for r in got["records"]))

    def test_highest_temperature_has_its_day(self):
        got = {r["name"]: r for r in record_board.board(self._days(), self.TODAY)["records"]}
        self.assertEqual(got["hi_temp"]["value"], 99.0)
        self.assertEqual(got["hi_temp"]["when"], "Jun 14, 2026")
        self.assertTrue(got["hi_temp"]["high"])
        self.assertFalse(got["lo_temp"]["high"])

    def test_longest_dry_spell_ends_when_the_rain_came(self):
        got = {r["name"]: r for r in record_board.board(self._days(), self.TODAY)["records"]}
        self.assertEqual(got["dry_spell"]["value"], 10)
        self.assertEqual(got["dry_spell"]["when"], "ended Jun 11, 2026")
        self.assertEqual(got["wet_spell"]["value"], 3)
        self.assertEqual(got["wet_spell"]["when"], "ended Jun 14, 2026")

    def test_wettest_month_leaves_out_the_month_so_far(self):
        got = {r["name"]: r for r in record_board.board(self._days(), self.TODAY)["records"]}
        self.assertEqual(got["wet_month"]["when"], "Sep 2026")
        self.assertAlmostEqual(got["wet_month"]["value"], 1.25)

    def test_new_means_set_in_the_last_30_days(self):
        got = {r["name"]: r for r in record_board.board(self._days(), self.TODAY)["records"]}
        self.assertTrue(got["wet_month"]["new"] is False)
        self.assertTrue(got["hi_temp"]["new"] is False)
        recent = self._days() + [(date(2026, 10, 20), {"rain_in": 1.5})]
        got = {r["name"]: r for r in record_board.board(recent, self.TODAY)["records"]}
        self.assertTrue(got["wet_day"]["new"])

    def test_no_days_gives_no_records(self):
        got = record_board.board([], self.TODAY)
        self.assertEqual(got["records"], [])
        self.assertEqual(got["highlights"], [])


if __name__ == "__main__":
    unittest.main()
