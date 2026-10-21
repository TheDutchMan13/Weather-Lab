"""Day coverage: exact, estimated and missing days. Synthetic data only."""

import unittest
from datetime import date

from weatherlab import coverage as cov


class CoverageTests(unittest.TestCase):
    def test_status_of_a_day(self):
        self.assertEqual(cov.status(None), cov.MISSING)
        self.assertEqual(cov.status({"tempf_max": 90}), cov.EXACT)
        self.assertEqual(cov.status({"tempf_max": 90, "estimated": True}), cov.ESTIMATED)

    def test_range_reports_gaps_and_estimates(self):
        days = {date(2026, 10, 1): {"tempf_max": 90},
                date(2026, 10, 2): {"tempf_max": 91, "estimated": True},
                date(2026, 10, 4): {"tempf_max": 88}}
        rows = cov.coverage(days, date(2026, 10, 1), date(2026, 10, 4))
        self.assertEqual([state for _, state in rows],
                         [cov.EXACT, cov.ESTIMATED, cov.MISSING, cov.EXACT])
        self.assertEqual(rows[2][0], date(2026, 10, 3))

    def test_counts_and_percent(self):
        rows = [(date(2026, 1, 1), cov.EXACT), (date(2026, 1, 2), cov.ESTIMATED),
                (date(2026, 1, 3), cov.MISSING), (date(2026, 1, 4), cov.MISSING)]
        counted = cov.counts(rows)
        self.assertEqual(counted, {cov.EXACT: 1, cov.ESTIMATED: 1, cov.MISSING: 2})
        self.assertEqual(cov.percent(counted, 4), 50.0)
        self.assertEqual(cov.percent(counted, 0), 0.0)

    def test_end_before_start_is_empty(self):
        self.assertEqual(cov.coverage({}, date(2026, 5, 2), date(2026, 5, 1)), [])


if __name__ == "__main__":
    unittest.main()
