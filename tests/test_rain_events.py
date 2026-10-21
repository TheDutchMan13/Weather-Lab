"""Rain events: showers separated by a dry gap, and the daily total starting again at midnight."""

import unittest

from weatherlab import rain_events


class RainEventTests(unittest.TestCase):
    def test_two_showers_separated_by_a_long_dry_spell(self):
        rows = [
            (0, {"dailyrainin": 0.0, "rainratein": 0.0}),
            (300, {"dailyrainin": 0.05, "rainratein": 0.6}),
            (600, {"dailyrainin": 0.10, "rainratein": 0.4}),
            (900, {"dailyrainin": 0.10, "rainratein": 0.0}),
            (1200, {"dailyrainin": 0.10, "rainratein": 0.0}),
            (8400, {"dailyrainin": 0.30, "rainratein": 0.8}),
        ]
        found = rain_events.events(rows)
        self.assertEqual([e["start"] for e in found], [300, 8400])
        self.assertEqual([e["inches"] for e in found], [0.1, 0.2])
        self.assertEqual([e["peak_rate"] for e in found], [0.6, 0.8])

    def test_short_gaps_stay_in_one_event(self):
        rows = [(0, {"dailyrainin": 0.0}), (300, {"dailyrainin": 0.1, "rainratein": 0.5}),
                (600, {"dailyrainin": 0.1, "rainratein": 0.0}), (900, {"dailyrainin": 0.2, "rainratein": 0.3})]
        found = rain_events.events(rows)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["inches"], 0.2)

    def test_total_starting_again_at_midnight_is_not_negative_rain(self):
        rows = [(0, {"dailyrainin": 0.5}), (300, {"dailyrainin": 0.0, "rainratein": 0.0}),
                (600, {"dailyrainin": 0.02, "rainratein": 0.1})]
        found = rain_events.events(rows)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["inches"], 0.02)


if __name__ == "__main__":
    unittest.main()
