"""Station status, sensors, record alerts, sun and moon, rain calendar, replay and the Ecowitt export. Offline."""

import sqlite3
import unittest
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from weatherlab import astro, ecowitt_import, gateway_sensors, rain_calendar, record_alerts, replay, station_status

PHOENIX = ZoneInfo("America/Phoenix")


class SensorTests(unittest.TestCase):
    def test_parse_skips_unpaired_and_reads_battery(self):
        rows = gateway_sensors.parse_sensors([[{"id": "A1", "img": "wh65", "batt": "3", "rssi": "-60", "signal": "4",
                                                "name": "Outdoor"}, {"id": "FFFFFFFF", "img": "wh26"}]])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["batt"], 3)
        self.assertEqual(rows[0]["name"], "Outdoor")

    def test_mains_and_empty_battery(self):
        self.assertEqual(gateway_sensors.battery_state(6)[0], "dc")
        self.assertEqual(gateway_sensors.battery_state(None)[0], "unknown")
        self.assertEqual(gateway_sensors.battery_state(1)[0], "low")
        self.assertEqual(gateway_sensors.signal_state(4, -60)[0], "good")
        self.assertEqual(gateway_sensors.signal_state(4, -95)[0], "weak")


class StatusTests(unittest.TestCase):
    def test_all_good(self):
        self.assertEqual(station_status.summary("ok", [], []), (True, []))

    def test_silent_station_and_sensor_problems(self):
        ok, problems = station_status.summary("silent", ["Feed down"],
                                              [{"name": "Outdoor", "battery": "low", "signal": "weak"}])
        self.assertFalse(ok)
        self.assertEqual(len(problems), 4)
        self.assertIn("Outdoor: battery is low.", problems)


class RecordTests(unittest.TestCase):
    DAYS = [(date(2026, 10, 1), {"tempf_max": 100.0, "humidity_min": 12.0}),
            (date(2026, 10, 2), {"tempf_max": 104.0})]

    def test_bests_are_the_best_day(self):
        best = record_alerts.bests(self.DAYS)
        self.assertEqual(best["tempf_max"], 104.0)
        self.assertEqual(best["humidity_min"], 12.0)

    def test_new_high_and_low_records(self):
        best = record_alerts.bests(self.DAYS)
        hits = record_alerts.check(best, {"tempf": 106})
        self.assertEqual([(k, v) for k, v, _ in hits], [("tempf_max", 106)])
        self.assertIn("106°F", hits[0][2])
        self.assertEqual([k for k, _, _ in record_alerts.check(best, {"humidity": 8})], ["humidity_min"])
        self.assertEqual(record_alerts.check(best, {"tempf": 103}), [])

    def test_combine_keeps_the_better_value(self):
        merged = record_alerts.combine({"tempf_max": 104.0, "tempf_min": 50.0},
                                       {"tempf_max": 107.0, "tempf_min": 55.0})
        self.assertEqual(merged, {"tempf_max": 107.0, "tempf_min": 50.0})


class AstroTests(unittest.TestCase):
    def test_phoenix_summer_sun_times(self):
        rise, set_ = astro.sun_times(33.45, -112.07, date(2026, 6, 21))
        mst = timezone(timedelta(hours=-7))
        rise_h = rise.astimezone(mst).hour + rise.astimezone(mst).minute / 60
        set_h = set_.astimezone(mst).hour + set_.astimezone(mst).minute / 60
        self.assertTrue(4.5 < rise_h < 6.0, rise_h)
        self.assertTrue(18.5 < set_h < 20.0, set_h)

    def test_no_sunset_far_north_in_summer(self):
        self.assertEqual(astro.sun_times(80, 0, date(2026, 6, 21)), (None, None))

    def test_moon_phases(self):
        new = astro.moon_phase(astro.NEW_MOON_REF)
        self.assertEqual(new["name"], "New moon")
        self.assertLess(new["illumination"], 1)
        full_time = astro.NEW_MOON_REF + timedelta(days=astro.FULL_AGE)
        self.assertGreater(astro.moon_phase(full_time)["illumination"], 99.9)
        nxt = astro.next_phase(astro.NEW_MOON_REF, astro.FULL_AGE)
        self.assertTrue(date(2000, 1, 20) <= nxt.date() <= date(2000, 1, 22))  # first full moon after 6 Jan 2000


class RainCalendarTests(unittest.TestCase):
    def test_month_grid_starts_on_sunday(self):
        weeks = rain_calendar.month_cells(2026, 10, {})
        self.assertEqual(len(weeks), 5)
        self.assertIsNone(weeks[0][0])
        self.assertEqual(weeks[0][4], (1, None))  # October 1, 2026 is a Thursday
        self.assertEqual(weeks[4][6], (31, None))

    def test_year_totals(self):
        totals, rainy = rain_calendar.year_totals({date(2026, 1, 1): 0.5, date(2026, 1, 2): 0.0,
                                                   date(2025, 5, 1): 1.25, date(2025, 5, 2): None})
        self.assertEqual(totals, {2026: 0.5, 2025: 1.25})
        self.assertEqual(rainy, {2026: 1, 2025: 1})


class ReplayTests(unittest.TestCase):
    def test_day_is_24_hours(self):
        start, end = replay.day_bounds(date(2026, 10, 20), PHOENIX)
        self.assertEqual(end - start, 86400)
        start, end = replay.day_bounds(date(2026, 10, 20), timezone.utc)
        self.assertEqual(end - start, 86400)


class EcowittTests(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(ecowitt_import.slug("Outdoor", "Temperature Low(℉)"), "outdoor_temperature_low")

    def test_daily_rows_map_to_summary_keys(self):
        rows = [["Time", "Outdoor", "Outdoor", "Outdoor"],
                [None, "Temperature(℉)", "Temperature Low(℉)", "Temperature High(℉)"],
                ["2026-10-08 17:00", 80.0, 62.0, 99.0]]
        days = ecowitt_import.parse_daily_rows(rows)
        self.assertEqual(days[date(2026, 10, 9)], {"tempf_avg": 80.0, "tempf_min": 62.0, "tempf_max": 99.0})

    def test_finer_rows_are_refused(self):
        rows = [["Time", "Outdoor"], [None, "Temperature(℉)"], ["2026-10-08 12:00", 80.0]]
        with self.assertRaises(ValueError):
            ecowitt_import.parse_daily_rows(rows)

    def test_store_never_replaces_a_day(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE daily (date TEXT PRIMARY KEY, data TEXT NOT NULL)")
        day = date(2026, 10, 9)
        self.assertEqual(ecowitt_import.store_days(db, {day: {"tempf_max": 95.0}}), 1)
        self.assertEqual(ecowitt_import.store_days(db, {day: {"tempf_max": 50.0}}), 0)
        self.assertIn("95.0", db.execute("SELECT data FROM daily").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
