"""Alert rules with several conditions, time windows, escalation, and pressure and temperature falls."""

import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from weatherlab import alert_rules

PHOENIX = ZoneInfo("America/Phoenix")


def at(hour: int) -> float:
    """A timestamp on 2026-10-22 at this local Phoenix hour."""
    return datetime(2026, 10, 22, hour, 0, tzinfo=PHOENIX).timestamp()


HOT_AND_DRY = {"name": "Hot and dry",
               "conditions": [{"metric": "tempf", "op": ">=", "value": 105},
                              {"metric": "humidity", "op": "<=", "value": 20}],
               "combine": "AND", "window": "any", "months": [], "escalate": False}


class ConditionTests(unittest.TestCase):
    def test_simple_rule_still_works(self):
        rule = {"name": "Hot", "metric": "tempf", "op": ">=", "value": 110}
        self.assertTrue(alert_rules.triggered(rule, {"tempf": 111}))
        self.assertFalse(alert_rules.triggered(rule, {"tempf": 109}))

    def test_and_needs_every_condition(self):
        self.assertTrue(alert_rules.triggered(HOT_AND_DRY, {"tempf": 106, "humidity": 15}))
        self.assertFalse(alert_rules.triggered(HOT_AND_DRY, {"tempf": 106, "humidity": 40}))

    def test_or_needs_one_condition(self):
        rule = dict(HOT_AND_DRY, combine="OR")
        self.assertTrue(alert_rules.triggered(rule, {"tempf": 90, "humidity": 15}))
        self.assertFalse(alert_rules.triggered(rule, {"tempf": 90, "humidity": 40}))

    def test_missing_reading_does_not_fire(self):
        self.assertFalse(alert_rules.triggered(HOT_AND_DRY, {"tempf": 106}))

    def test_describe_joins_conditions(self):
        self.assertEqual(alert_rules.describe(HOT_AND_DRY),
                         "Hot and dry: Temperature at or above 105°F and Humidity at or below 20%")
        self.assertIn(" or ", alert_rules.describe(dict(HOT_AND_DRY, combine="OR")))

    def test_valid_rule_checks_every_condition(self):
        bad = dict(HOT_AND_DRY, conditions=[{"metric": "tempf", "op": ">=", "value": 1},
                                            {"metric": "nope", "op": ">=", "value": 1}])
        self.assertIsNotNone(alert_rules.valid_rule(bad))
        self.assertIsNone(alert_rules.valid_rule(HOT_AND_DRY))
        self.assertIsNotNone(alert_rules.valid_rule(dict(HOT_AND_DRY, combine="MAYBE")))
        self.assertIsNotNone(alert_rules.valid_rule(dict(HOT_AND_DRY, window="months", months=[])))


class WindowTests(unittest.TestCase):
    def test_daytime_window(self):
        rule = dict(HOT_AND_DRY, window="day")
        self.assertTrue(alert_rules.in_window(rule, at(12), PHOENIX))
        self.assertFalse(alert_rules.in_window(rule, at(2), PHOENIX))

    def test_night_window(self):
        rule = dict(HOT_AND_DRY, window="night")
        self.assertTrue(alert_rules.in_window(rule, at(2), PHOENIX))
        self.assertFalse(alert_rules.in_window(rule, at(12), PHOENIX))

    def test_months_window(self):
        rule = dict(HOT_AND_DRY, window="months", months=[7, 8, 9])
        self.assertFalse(alert_rules.in_window(rule, at(12), PHOENIX))  # October
        self.assertTrue(alert_rules.in_window(dict(rule, months=[10]), at(12), PHOENIX))

    def test_evaluate_respects_the_window(self):
        rule = dict(HOT_AND_DRY, window="day")
        reading = {"tempf": 106, "humidity": 15}
        self.assertEqual(alert_rules.evaluate([rule], reading, at(2), {}, False, PHOENIX), [])
        self.assertEqual(len(alert_rules.evaluate([rule], reading, at(12), {}, False, PHOENIX)), 1)

    def test_window_is_described(self):
        self.assertTrue(alert_rules.describe(dict(HOT_AND_DRY, window="night")).endswith("(night, 6 PM to 6 AM)"))


class EscalationTests(unittest.TestCase):
    def test_escalating_rule_steps_up_while_it_lasts(self):
        rule = dict(HOT_AND_DRY, escalate=True)
        reading = {"tempf": 106, "humidity": 15}
        state = {}
        start = at(12)
        first = alert_rules.evaluate([rule], reading, start, state, False, PHOENIX)
        self.assertTrue(first[0].startswith("Notice: "))
        self.assertEqual(alert_rules.evaluate([rule], reading, start + 1800, state, False, PHOENIX), [])
        second = alert_rules.evaluate([rule], reading, start + 3600, state, False, PHOENIX)
        self.assertTrue(second[0].startswith("Warning: "))
        third = alert_rules.evaluate([rule], reading, start + 3 * 3600, state, False, PHOENIX)
        self.assertTrue(third[0].startswith("Severe: "))
        self.assertEqual(alert_rules.evaluate([rule], reading, start + 4 * 3600, state, False, PHOENIX), [])
        again = alert_rules.evaluate([rule], reading, start + 6 * 3600, state, False, PHOENIX)
        self.assertTrue(again[0].startswith("Severe, still going: "))

    def test_escalation_resets_when_the_rule_clears(self):
        rule = dict(HOT_AND_DRY, escalate=True)
        state = {}
        start = at(12)
        alert_rules.evaluate([rule], {"tempf": 106, "humidity": 15}, start, state, False, PHOENIX)
        alert_rules.evaluate([rule], {"tempf": 90, "humidity": 15}, start + 3600, state, False, PHOENIX)  # clears
        restarted = alert_rules.evaluate([rule], {"tempf": 106, "humidity": 15}, start + 7200, state, False, PHOENIX)
        self.assertTrue(restarted[0].startswith("Notice: "))

    def test_plain_rule_repeats_at_most_once_an_hour(self):
        rule = {"name": "Hot", "metric": "tempf", "op": ">=", "value": 110}
        state = {}
        self.assertEqual(len(alert_rules.evaluate([rule], {"tempf": 112}, 1000, state)), 1)
        self.assertEqual(alert_rules.evaluate([rule], {"tempf": 112}, 1060, state), [])
        self.assertEqual(len(alert_rules.evaluate([rule], {"tempf": 112}, 1000 + alert_rules.COOLDOWN_S, state)), 1)


class RateTests(unittest.TestCase):
    def test_pressure_and_temperature_falls_over_the_hour(self):
        now = 10_000.0
        readings = [(now - 3600, {"baromrelin": 29.92, "tempf": 90.0}),
                    (now - 1800, {"baromrelin": 29.86, "tempf": 86.0}),
                    (now, {"baromrelin": 29.80, "tempf": 84.0})]
        got = alert_rules.rates(readings, now)
        self.assertAlmostEqual(got["pressure_drop"], 0.12, places=3)
        self.assertAlmostEqual(got["temp_drop"], 6.0, places=1)

    def test_rising_pressure_is_a_negative_fall(self):
        now = 10_000.0
        readings = [(now - 3600, {"baromrelin": 29.80}), (now, {"baromrelin": 29.92})]
        self.assertLess(alert_rules.rates(readings, now)["pressure_drop"], 0)

    def test_too_little_data_gives_no_rates(self):
        now = 10_000.0
        self.assertEqual(alert_rules.rates([(now, {"baromrelin": 29.9})], now), {})
        self.assertEqual(alert_rules.rates([(now - 300, {"baromrelin": 29.9}), (now, {"baromrelin": 29.8})], now), {})

    def test_pressure_fall_rule_fires_from_the_context(self):
        rule = {"name": "Pressure drop", "metric": "pressure_drop", "op": ">=", "value": 0.06}
        self.assertEqual(len(alert_rules.evaluate([rule], {}, 0, {}, False, None, {"pressure_drop": 0.1})), 1)
        self.assertEqual(alert_rules.evaluate([rule], {}, 0, {}, False, None, {"pressure_drop": 0.01}), [])

    def test_fall_rules_are_shown_in_metric_units(self):
        rule = {"name": "Drop", "metric": "pressure_drop", "op": ">=", "value": 0.06}
        self.assertIn("mb per hour", alert_rules.describe(rule, True))
        self.assertIn("inHg per hour", alert_rules.describe(rule, False))
        self.assertAlmostEqual(alert_rules.to_us_value("pressure_drop", 2.0, True), 0.059, places=3)


if __name__ == "__main__":
    unittest.main()
