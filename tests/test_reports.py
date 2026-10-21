"""Monthly and yearly report tests. Offline; skipped if reportlab isn't installed."""

import unittest
from datetime import date

try:
    from weatherlab import report
except ImportError:
    report = None

HOT = {"tempf_max": 112.0, "tempf_min": 80.0, "tempf_avg": 95.0, "rain_in": 0.0, "gust_max": 22.0,
       "sun_hours": 11.0, "humidity_min": 10.0, "humidity_max": 40.0}
COOL = {"tempf_max": 65.0, "tempf_min": 30.0, "tempf_avg": 48.0, "rain_in": 0.5, "gust_max": 10.0,
        "sun_hours": 4.0, "humidity_min": 50.0, "humidity_max": 95.0}


@unittest.skipIf(report is None, "reportlab is not installed")
class ReportTests(unittest.TestCase):
    def test_stats_totals(self):
        rows = [(date(2026, 10, 1), HOT), (date(2026, 10, 2), COOL)]
        st = report._stats(rows)
        self.assertEqual(st["days"], 2)
        self.assertEqual(st["high"], 112.0)
        self.assertEqual(st["low"], 30.0)
        self.assertAlmostEqual(st["rain"], 0.5)
        self.assertEqual(st["rainy"], 1)
        self.assertEqual(st["hot"], 1)
        self.assertEqual(st["cold"], 1)
        self.assertEqual(st["windy"], 1)

    def test_stats_with_no_rows(self):
        st = report._stats([])
        self.assertEqual(st["days"], 0)
        self.assertIsNone(st["high"])

    def test_monthly_pdf(self):
        pdf = report.monthly_pdf(2026, 10, [(date(2026, 10, 1), HOT), (date(2026, 10, 2), COOL)])
        self.assertTrue(pdf.startswith(b"%PDF"))

    def test_yearly_pdf_with_breakdown(self):
        pdf = report.yearly_pdf(2026, [(date(2026, 9, 30), HOT), (date(2026, 10, 2), COOL)])
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
