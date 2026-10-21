"""Stuck sensor check. Synthetic readings only."""

import unittest

from weatherlab import stuck


class StuckTests(unittest.TestCase):
    def test_unchanging_temperature_over_three_hours_is_flagged(self):
        rows = [(t, {"tempf": 72.4, "humidity": 30 + (t // 300) % 7}) for t in range(0, 11401, 300)]
        self.assertEqual(stuck.stuck_keys(rows), ["tempf"])

    def test_changing_readings_are_fine(self):
        rows = [(t, {"tempf": 70 + (t // 300) % 5, "humidity": 30 + (t // 300) % 7}) for t in range(0, 11401, 300)]
        self.assertEqual(stuck.stuck_keys(rows), [])

    def test_too_short_a_span_is_not_judged(self):
        rows = [(t, {"tempf": 72.4}) for t in range(0, 3600, 300)]
        self.assertEqual(stuck.stuck_keys(rows), [])


if __name__ == "__main__":
    unittest.main()
