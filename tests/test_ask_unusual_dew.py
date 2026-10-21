"""Ask, unusual days and dew point. Synthetic data only."""

import unittest
from datetime import date

from weatherlab import ask, dew, history_compare as hc

DAYS = [(date(2025, 7, 1), {"tempf_max": 108, "tempf_min": 80, "rain_in": 0.0}),
        (date(2025, 7, 2), {"tempf_max": 101, "tempf_min": 66, "rain_in": 0.5}),
        (date(2025, 8, 10), {"tempf_max": 104, "tempf_min": 70, "rain_in": 2.0}),
        (date(2025, 8, 11), {"tempf_max": 99, "tempf_min": 72, "rain_in": 0.3}),
        (date(2026, 3, 5), {"tempf_max": 70, "tempf_min": 40, "rain_in": 1.2})]
TODAY = date(2026, 10, 21)


class AskTests(unittest.TestCase):
    def test_extremes(self):
        self.assertIn("108 °F", ask.answer("warmest day", DAYS, TODAY))
        self.assertIn("40 °F", ask.answer("coldest night", DAYS, TODAY))
        self.assertIn("2.00", ask.answer("wettest day", DAYS, TODAY))

    def test_months(self):
        self.assertIn("August 2025", ask.answer("wettest month", DAYS, TODAY))
        self.assertIn("July 2025", ask.answer("hottest month", DAYS, TODAY))

    def test_rain_in_a_named_month(self):
        self.assertIn("1.20", ask.answer("rain in March 2026", DAYS, TODAY))

    def test_counting_days(self):
        self.assertIn("1 day reached 105", ask.answer("how many days over 105", DAYS, TODAY))

    def test_unknown_question_lists_examples(self):
        self.assertIn("I can answer", ask.answer("what is the meaning of life", DAYS, TODAY))


class UnusualTests(unittest.TestCase):
    def test_flags_large_departure_and_heavy_rain(self):
        days = [(date(2024, 10, 21), {"tempf_max": 90, "tempf_min": 60}),
                (date(2025, 10, 21), {"tempf_max": 92, "tempf_min": 62}),
                (date(2026, 10, 21), {"tempf_max": 106, "tempf_min": 61, "rain_in": 1.5})]
        self.assertEqual(hc.unusual(date(2026, 10, 21), days[2][1], days),
                         ["high +15 °F from usual", "1.50 in of rain"])

    def test_ordinary_day_is_not_listed(self):
        days = [(date(2024, 10, 21), {"tempf_max": 90, "tempf_min": 60}),
                (date(2025, 10, 21), {"tempf_max": 92, "tempf_min": 62}),
                (date(2026, 10, 21), {"tempf_max": 91, "tempf_min": 61})]
        self.assertEqual(hc.unusual(date(2026, 10, 21), days[2][1], days), [])


class DewTests(unittest.TestCase):
    def test_bands(self):
        self.assertEqual(dew.text(50), "dry and comfortable")
        self.assertEqual(dew.text(58), "comfortable")
        self.assertEqual(dew.text(67), "muggy")
        self.assertEqual(dew.text(72), "oppressive")


if __name__ == "__main__":
    unittest.main()
