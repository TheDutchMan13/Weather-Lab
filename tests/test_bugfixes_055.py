"""Bug fixes in 0.37.55: midnight rain, alert rules at the limit, readings without outdoor temperature."""
import unittest

from weatherlab import alert_rules, daily


class MidnightRainTests(unittest.TestCase):
    def test_yesterdays_total_at_midnight_is_left_out(self):
        rows = [(0, {"dailyrainin": 1.2}), (60, {"dailyrainin": 1.2})] + [(120 + i * 60, {"dailyrainin": 0.0}) for i in range(100)]
        self.assertEqual(daily.day_rain(rows), 0.0)

    def test_rain_later_in_the_day_counts(self):
        rows = [(0, {"dailyrainin": 1.2})] + [(60 + i * 60, {"dailyrainin": 0.0}) for i in range(50)] + \
               [(4000 + i * 60, {"dailyrainin": 0.3}) for i in range(10)]
        self.assertEqual(daily.day_rain(rows), 0.3)

    def test_rain_just_after_midnight_is_kept(self):
        rows = [(0, {"dailyrainin": 0.0}), (60, {"dailyrainin": 0.05}), (120, {"dailyrainin": 0.1})]
        self.assertEqual(daily.day_rain(rows), 0.1)

    def test_no_rain_values(self):
        self.assertEqual(daily.day_rain([(0, {"tempf": 70})]), 0.0)


class HoveringRuleTests(unittest.TestCase):
    RULE = {"metric": "tempf", "op": ">=", "value": 110}

    def test_hovering_at_the_limit_sends_once_an_hour(self):
        state, sent = {}, 0
        for minute in range(10):
            reading = {"tempf": 110.1 if minute % 2 == 0 else 109.9}
            sent += len(alert_rules.evaluate([self.RULE], reading, 1000 + minute * 60, state))
        self.assertEqual(sent, 1)

    def test_a_new_event_after_it_stays_clear(self):
        state = {}
        self.assertEqual(len(alert_rules.evaluate([self.RULE], {"tempf": 111}, 0, state)), 1)
        alert_rules.evaluate([self.RULE], {"tempf": 100}, 60, state)
        alert_rules.evaluate([self.RULE], {"tempf": 100}, 60 + alert_rules.CLEAR_RESET_S, state)
        self.assertEqual(state, {})
        self.assertEqual(len(alert_rules.evaluate([self.RULE], {"tempf": 111}, 2000 + alert_rules.CLEAR_RESET_S, state)), 1)


if __name__ == "__main__":
    unittest.main()
