"""The Records and analysis data for the Android app (Weather Lab 0.37.20)."""
import unittest

from tests.test_api_pages import ApiHelpers


class RecordsAnalysisTests(ApiHelpers, unittest.TestCase):
    def test_summary_events_and_distribution(self):
        self.seed_days()
        code, body = self.get("/api/v1/records/analysis")
        self.assertEqual(code, 200)
        self.assertEqual(body["summary"]["days100"], 2)
        self.assertEqual(body["summary"]["days110"], 1)
        self.assertEqual(body["summary"]["hottest"]["value"], 112)
        self.assertEqual(body["counts"]["heat"], 1)
        self.assertEqual(body["events"]["heat"][0]["value"], 112)
        self.assertEqual(body["units"]["temp"], "°F")
        self.assertEqual(sum(x["count"] for x in body["distribution"]), 4)
        self.assertEqual(body["limits"]["heat"], 105)

    def test_metric_units(self):
        from dataclasses import replace
        self.seed_days()
        code, body = self.get("/api/v1/records/analysis", replace(self.s, units="Metric"))
        self.assertEqual(code, 200)
        self.assertTrue(body["metric"])
        self.assertEqual(body["units"]["temp"], "°C")
        self.assertAlmostEqual(body["summary"]["hottest"]["value"], 44.4, delta=0.2)

    def test_empty(self):
        code, body = self.get("/api/v1/records/analysis")
        self.assertEqual(code, 200)
        self.assertEqual(body["counts"], {"heat": 0, "cold": 0, "wind": 0, "rain": 0})
        self.assertIsNone(body["summary"]["hottest"])
        self.assertEqual(body["distribution"], [])

    def test_needs_token(self):
        from weatherlab import api
        code, _ = api.route("/api/v1/records/analysis", None, self.db, self.s, self.now)
        self.assertEqual(code, 401)


if __name__ == "__main__":
    unittest.main()
