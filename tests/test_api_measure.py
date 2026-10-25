"""One reading over 1, 7 or 30 days for the Android history sheet (Weather Lab 0.37.9)."""
import unittest

from tests.test_api_pages import ApiHelpers
from weatherlab import storage


class MeasureHistoryTests(ApiHelpers, unittest.TestCase):
    def _fill(self):
        for m in range(0, 3 * 24 * 60, 10):
            storage.store_reading(self.db, {"humidity": 40.0 + (m % 60) / 10, "tempf": 60.0 + (m % 100) / 10},
                                  int(self.now - m * 60))

    def test_one_day(self):
        self._fill()
        code, body = self.get("/api/v1/measure/humidity/1")
        self.assertEqual(code, 200)
        self.assertEqual(body["key"], "humidity")
        self.assertEqual(body["unit"], "%")
        self.assertGreater(len(body["points"]), 10)
        self.assertLessEqual(body["low"], body["average"])
        self.assertLessEqual(body["average"], body["high"])

    def test_seven_days_covers_more(self):
        self._fill()
        _, one = self.get("/api/v1/measure/tempf/1")
        _, seven = self.get("/api/v1/measure/tempf/7")
        self.assertGreater(seven["points"][-1][0] - seven["points"][0][0], one["points"][-1][0] - one["points"][0][0])

    def test_bad_input(self):
        self.assertIn("error", self.get("/api/v1/measure/nonsense/1")[1])
        self.assertIn("error", self.get("/api/v1/measure/humidity/5")[1])

    def test_empty(self):
        code, body = self.get("/api/v1/measure/humidity/1")
        self.assertEqual(code, 200)
        self.assertEqual(body["points"], [])
        self.assertIsNone(body["high"])
