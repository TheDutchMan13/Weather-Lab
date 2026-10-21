"""US and metric display. Offline."""

import unittest

from weatherlab import units


class UnitTests(unittest.TestCase):
    def test_us_is_unchanged(self):
        self.assertEqual(units.format_value("tempf", 72.5, False), "72.5 °F")
        self.assertEqual(units.format_value("windspeedmph", 10, False), "10 mph")
        self.assertEqual(units.convert("windspeedmph", 10, False), 10)

    def test_metric_conversions(self):
        self.assertEqual(units.format_value("tempf", 32, True, 0), "0 °C")
        self.assertEqual(units.format_value("windspeedmph", 10, True), "16.1 km/h")
        self.assertEqual(units.format_value("dailyrainin", 1, True), "25.4 mm")
        self.assertEqual(units.format_value("baromrelin", 30, True), "1015.9 hPa")
        self.assertEqual(units.format_value("miles", 100, True, 0), "161 km")

    def test_missing_values_and_other_readings(self):
        self.assertEqual(units.format_value("tempf", None, True), "--")
        self.assertEqual(units.convert("humidity", 50, True), 50)
        self.assertTrue(units.converts("heat_index"))
        self.assertFalse(units.converts("humidity"))
        self.assertTrue(units.is_metric("Metric"))
        self.assertFalse(units.is_metric("US"))
        self.assertEqual(units.speed_unit(True), "km/h")
        self.assertEqual(units.speed_factor(False), 1.0)


if __name__ == "__main__":
    unittest.main()
