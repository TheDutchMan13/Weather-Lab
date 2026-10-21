"""Sensor battery and signal warnings. Synthetic readings only."""

import unittest

from weatherlab import gateway_sensors as gs


class SensorWarningTests(unittest.TestCase):
    def test_low_battery_and_weak_signal_are_reported(self):
        sensors = [{"name": "Outdoor array", "batt": 1, "signal": 4, "rssi": -60},
                   {"name": "Lightning sensor", "batt": 2, "signal": 1, "rssi": None},
                   {"name": "Indoor sensor", "batt": 5, "signal": 4, "rssi": -55}]
        out = gs.warnings(sensors)
        self.assertEqual(len(out), 3)
        self.assertIn("Outdoor array: battery is low", out[0])
        self.assertIn("Lightning sensor: battery is getting low", out[1])
        self.assertIn("Lightning sensor: signal is weak", out[2])

    def test_mains_powered_and_unknown_sensors_are_quiet(self):
        self.assertEqual(gs.warnings([{"name": "Rain", "batt": 6, "signal": 4},
                                      {"name": "Spare", "batt": None, "signal": None}]), [])


if __name__ == "__main__":
    unittest.main()
