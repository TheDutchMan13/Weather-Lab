"""The Daily page's range data: charts and wind for 'all', and the rain totals (Weather Lab 0.37.22)."""
import unittest

from tests.test_api_pages import ApiHelpers


class DailyRange(ApiHelpers, unittest.TestCase):
    def test_charts_all_covers_every_day(self):
        self.seed_days()
        code, body = self.get("/api/v1/charts/all")
        self.assertEqual(code, 200)
        self.assertGreater(len(body["days"]), 1)
        self.assertEqual(body["temp_points"], [])
        dates = [d["date"] for d in body["days"]]
        self.assertEqual(dates, sorted(dates))

    def test_charts_have_rain_totals(self):
        self.seed_days()
        for path in ("/api/v1/charts/7", "/api/v1/charts/30", "/api/v1/charts/all"):
            _, body = self.get(path)
            self.assertEqual(set(body["rain_totals"]), {"today", "last_7_days", "this_month", "this_year"})

    def test_charts_all_with_no_data(self):
        code, body = self.get("/api/v1/charts/all")
        self.assertEqual(code, 200)
        self.assertEqual(len(body["days"]), 1)

    def test_wind_all(self):
        self.seed_readings()
        code, body = self.get("/api/v1/wind/all")
        self.assertEqual(code, 200)
        self.assertEqual(body["days"], 0)
        self.assertEqual(len(body["directions"]), 16)

    def test_unknown_ranges_still_404(self):
        self.assertEqual(self.get("/api/v1/charts/9")[0], 404)
        self.assertEqual(self.get("/api/v1/wind/9")[0], 404)


if __name__ == "__main__":
    unittest.main()
