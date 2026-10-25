"""Hours in each level, dangerous days and today's chart points in the heat page data (Weather Lab 0.37.21)."""
import unittest

from tests.test_api_pages import ApiHelpers


class HeatExtras(ApiHelpers, unittest.TestCase):
    def test_new_fields(self):
        self.seed_readings()
        self.seed_days()
        code, body = self.get("/api/v1/heat")
        self.assertEqual(code, 200)
        self.assertEqual([h["level"] for h in body["hours"]],
                         ["Comfortable", "Caution", "Extreme caution", "Danger", "Extreme danger"])
        self.assertGreaterEqual(body["danger_hours"], 0)
        self.assertEqual(body["danger_limit"], 104)
        self.assertLessEqual(len(body["series"]), 150)
        for row in body["series"]:
            self.assertEqual(len(row), 3)

    def test_dangerous_days_sorted(self):
        self.seed_days()
        _, body = self.get("/api/v1/heat")
        values = [d["value"] for d in body["danger_days"]]
        self.assertEqual(values, sorted(values, reverse=True))
        self.assertTrue(all(v >= 104 for v in values))

    def test_empty_database(self):
        code, body = self.get("/api/v1/heat")
        self.assertEqual(code, 200)

    def test_long_day_is_thinned(self):
        from weatherlab import api_pages
        today = [(1000 + i * 30, {"tempf": 90.0, "humidity": 40.0}) for i in range(1000)]
        series = api_pages._heat_series(today, False)
        self.assertLessEqual(len(series), 150)
        self.assertGreater(len(series), 50)


if __name__ == "__main__":
    unittest.main()
