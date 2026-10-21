"""Lightning by day."""

import unittest
from datetime import date
from zoneinfo import ZoneInfo

from weatherlab import lightning_history


class PerDayTests(unittest.TestCase):
    def test_counts_and_closest_per_day(self):
        utc = ZoneInfo("UTC")
        strikes = [(0, 3.0), (100, 1.0), (86400 + 5, 8.0)]
        self.assertEqual(lightning_history.per_day(strikes, utc),
                         [(date(1970, 1, 1), 2, 1.0), (date(1970, 1, 2), 1, 8.0)])

    def test_no_strikes_gives_nothing(self):
        self.assertEqual(lightning_history.per_day([], ZoneInfo("UTC")), [])


if __name__ == "__main__":
    unittest.main()
