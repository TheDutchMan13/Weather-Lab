"""On This Day: the same month and day in earlier years only."""

import unittest
from datetime import date

from weatherlab import history


class OnThisDayTests(unittest.TestCase):
    def test_same_month_and_day_in_earlier_years_only(self):
        days = [(date(2024, 10, 21), {"tempf_max": 90}), (date(2025, 10, 21), {"tempf_max": 91}),
                (date(2025, 10, 22), {}), (date(2026, 10, 21), {"tempf_max": 92}),
                (date(2023, 10, 21), {"tempf_max": 89})]
        out = history.same_day_before(days, date(2026, 10, 21))
        self.assertEqual([d.year for d, _ in out], [2023, 2024, 2025])


if __name__ == "__main__":
    unittest.main()
