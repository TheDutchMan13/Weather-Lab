import unittest

from weatherlab import digest


class WeeklyTests(unittest.TestCase):
    def test_summarises_the_week(self):
        days = [{"tempf_max": 100, "tempf_min": 70, "rain_in": 0.5},
                {"tempf_max": 104, "tempf_min": 68, "rain_in": 0.25}]
        text = digest.weekly_text("Oct 15 to Oct 21", days, metric=False)
        self.assertIn("high 104", text)
        self.assertIn("low 68", text)
        self.assertIn("2 of 7 days recorded", text)
        self.assertTrue(text.startswith("Last 7 days (Oct 15 to Oct 21)"))

    def test_no_data_gives_nothing(self):
        self.assertEqual(digest.weekly_text("x", [{}, {}], metric=False), "")
        self.assertEqual(digest.weekly_text("x", [], metric=True), "")

    def test_rain_only_still_counts(self):
        text = digest.weekly_text("x", [{"rain_in": 1.0}], metric=False)
        self.assertIn("rain", text)
        self.assertIn("1 of 7 days recorded", text)


if __name__ == "__main__":
    unittest.main()
