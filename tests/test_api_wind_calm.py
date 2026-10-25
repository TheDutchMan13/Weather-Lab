"""The calm share in the wind data (Weather Lab 0.37.24)."""
import unittest

from tests.test_api_pages import ApiHelpers
from weatherlab import storage


class WindCalm(ApiHelpers, unittest.TestCase):
    def test_calm_share_is_counted_but_not_drawn(self):
        for i in range(20):
            speed = 0.0 if i < 5 else 8.0  # a quarter of the readings are calm
            storage.store_reading(self.db, {"windspeedmph": speed, "winddir": 270.0}, int(self.now - 600 * (i + 1)))
        code, body = self.get("/api/v1/wind/1")
        self.assertEqual(code, 200)
        self.assertEqual(body["total"], 20)
        self.assertEqual(body["calm"], 5)
        self.assertEqual(body["calm_percent"], 25.0)
        self.assertEqual(len(body["bins"]), 4)
        self.assertAlmostEqual(sum(d["percent"] for d in body["directions"]), 75.0, places=1)

    def test_no_readings(self):
        _, body = self.get("/api/v1/wind/1")
        self.assertEqual(body["calm_percent"], 0.0)


if __name__ == "__main__":
    unittest.main()
