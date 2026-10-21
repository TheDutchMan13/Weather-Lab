"""Heat safety, sun and UV, wind rose, alert rules and the tropics feed. Offline; nothing is downloaded."""

import json
import tempfile
import time
import unittest
from pathlib import Path

from weatherlab import alert_rules, heat_safety, sun_uv, tropics, wind_rose

# A remote point in central Nevada. The test doesn't use a real home location.
TEST_HOME = (39.5, -116.5)


class HeatTests(unittest.TestCase):
    def test_levels_follow_nws_categories(self):
        self.assertEqual(heat_safety.level_for(79)[0], "Comfortable")
        self.assertEqual(heat_safety.level_for(80)[0], "Caution")
        self.assertEqual(heat_safety.level_for(90)[0], "Caution")
        self.assertEqual(heat_safety.level_for(91)[0], "Extreme caution")
        self.assertEqual(heat_safety.level_for(104)[0], "Danger")
        self.assertEqual(heat_safety.level_for(125)[0], "Extreme danger")

    def test_status_uses_heat_index(self):
        self.assertEqual(heat_safety.status(95, 60)["level"], "Danger")
        self.assertEqual(heat_safety.status(70, 20)["level"], "Comfortable")

    def test_missing_data(self):
        self.assertEqual(heat_safety.status(None, 20)["level"], "No data")


class SunTests(unittest.TestCase):
    def test_burn_time(self):
        self.assertIsNone(sun_uv.burn_minutes(None, "Type II (burns easily)"))
        self.assertAlmostEqual(sun_uv.burn_minutes(10, "Type II (burns easily)"), 16.67, places=1)

    def test_sunshine_counts_only_sunny_intervals(self):
        self.assertAlmostEqual(sun_uv.sunshine_hours([(0, 200), (60, 200), (120, 50)]), 120 / 3600)

    def test_long_gap_is_capped(self):
        self.assertAlmostEqual(sun_uv.sunshine_hours([(0, 200), (3600, 200)]), 600 / 3600)


class WindTests(unittest.TestCase):
    def test_rose_counts_and_skips_missing(self):
        counts, total = wind_rose.rose([{"winddir": 0, "windspeedmph": 3},
                                        {"winddir": 180, "windspeedmph": 12},
                                        {"windspeedmph": 5}])
        self.assertEqual(total, 2)
        self.assertEqual(counts[0][0], 1)   # 0-5 mph, from the north
        self.assertEqual(counts[2][8], 1)   # 10-15 mph, from the south

    def test_dominant_and_percentages(self):
        counts, total = wind_rose.rose([{"winddir": 90, "windspeedmph": 7}] * 3 + [{"winddir": 270, "windspeedmph": 7}])
        self.assertEqual(wind_rose.dominant(counts), "E")
        self.assertEqual(wind_rose.percentages(counts, total)[1][4], 75.0)


class AlertTests(unittest.TestCase):
    def test_valid_rule(self):
        self.assertIsNone(alert_rules.valid_rule({"name": "Hot", "metric": "tempf", "op": ">=", "value": 110}))
        self.assertIsNotNone(alert_rules.valid_rule({"metric": "nope", "op": ">=", "value": 1}))
        self.assertIsNotNone(alert_rules.valid_rule({"metric": "tempf", "op": "==", "value": 1}))
        self.assertIsNotNone(alert_rules.valid_rule({"metric": "tempf", "op": ">=", "value": "hot"}))

    def test_fires_once_per_cooldown(self):
        rule = {"name": "Hot", "metric": "tempf", "op": ">=", "value": 110}
        last = {}
        self.assertEqual(len(alert_rules.evaluate([rule], {"tempf": 112}, 1000, last)), 1)
        self.assertEqual(alert_rules.evaluate([rule], {"tempf": 113}, 1060, last), [])
        self.assertEqual(len(alert_rules.evaluate([rule], {"tempf": 113}, 1000 + alert_rules.COOLDOWN_S, last)), 1)

    def test_heat_index_rule_and_missing_values(self):
        rule = {"name": "Dangerous heat", "metric": "heat_index", "op": ">=", "value": 110}
        self.assertEqual(len(alert_rules.evaluate([rule], {"tempf": 95, "humidity": 60}, 0, {})), 1)
        self.assertEqual(alert_rules.evaluate([rule], {"tempf": 95}, 0, {}), [])

    def test_below_rule_and_bad_rules_are_skipped(self):
        rule = {"name": "Frost", "metric": "tempf", "op": "<=", "value": 35}
        self.assertEqual(len(alert_rules.evaluate([rule, {"metric": "bad"}], {"tempf": 33}, 0, {})), 1)
        self.assertEqual(alert_rules.describe(rule), "Frost: Temperature at or below 35°F")


class TropicsTests(unittest.TestCase):
    RAW = {"activeStorms": [
        {"name": "Test Storm", "classification": "TS", "intensity": "50", "latitudeNumeric": 20,
         "longitudeNumeric": -110, "movementDir": 270, "movementSpeed": 10, "lastUpdate": "today"},
        {"name": "No position"},
    ]}

    def test_parse_measures_from_home(self):
        rows = tropics.parse(self.RAW, TEST_HOME)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["wind_mph"], 58)
        self.assertIn(rows[0]["direction"], {"S", "SSE", "SE"})
        self.assertGreater(rows[0]["miles"], 500)

    def test_refresh_uses_saved_copy_then_keeps_it_on_failure(self):
        def never():
            raise AssertionError("should not download again within 30 minutes")

        def down():
            raise OSError("no network")

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "tropics.json"
            first = tropics.refresh(TEST_HOME, path, fetch=lambda: self.RAW)
            self.assertTrue(first["ok"])
            again = tropics.refresh(TEST_HOME, path, fetch=never)
            self.assertEqual(again["storms"][0]["name"], "Test Storm")
            old = dict(first, checked_ts=time.time() - 7200)
            path.write_text(json.dumps(old), encoding="utf-8")
            broken = tropics.refresh(TEST_HOME, path, fetch=down)
            self.assertFalse(broken["ok"])
            self.assertEqual(broken["storms"][0]["name"], "Test Storm")


if __name__ == "__main__":
    unittest.main()
