"""Counting the earlier days behind "usual for this hour" for the progress note on the Live 24-hour tiles."""
import time
import unittest
from zoneinfo import ZoneInfo

from weatherlab import sparks

TZ = ZoneInfo("America/Phoenix")


def earlier_days(now: float, count: int, value: float = 78.0) -> list:
    """One reading at this clock hour on each of count earlier days (all before the 24-hour cutoff)."""
    return sorted((now - d * 86400, {"tempf": value}) for d in range(2, count + 2))


class UsualProgressTests(unittest.TestCase):
    def setUp(self):
        self.now = time.time()

    def test_no_history_counts_zero_days(self):
        self.assertEqual(sparks.usual_days([], "tempf", TZ, self.now), 0)

    def test_counts_each_earlier_day_once(self):
        rows = earlier_days(self.now, 3) + [(self.now, {"tempf": 84.0})]
        self.assertEqual(sparks.usual_days(rows, "tempf", TZ, self.now), 3)

    def test_usual_stays_hidden_until_five_days(self):
        rows = earlier_days(self.now, 4) + [(self.now, {"tempf": 84.0})]
        self.assertIsNone(sparks.hourly_usual(rows, "tempf", TZ, self.now))
        self.assertEqual(sparks.usual_days(rows, "tempf", TZ, self.now), 4)

    def test_usual_appears_at_five_days(self):
        rows = earlier_days(self.now, 5) + [(self.now, {"tempf": 84.0})]
        current, usual, days = sparks.hourly_usual(rows, "tempf", TZ, self.now)
        self.assertEqual((current, usual, days), (84.0, 78.0, 5))


if __name__ == "__main__":
    unittest.main()
