"""The temperature ring: text, units, and the chips. Offline."""

import unittest

from weatherlab import gauges


class TempRingTests(unittest.TestCase):
    def test_shows_temperature_and_chips_in_fahrenheit(self):
        out, height = gauges.temp_ring_html(83.0, high=95.0, low=70.0, feels=82.9, dew=59.4, hum=45)
        self.assertIn("83.0", out)
        self.assertIn("°F", out)
        self.assertIn("↑ 95°F", out)
        self.assertIn("↓ 70°F", out)
        self.assertIn("Feels like", out)
        self.assertIn("45%", out)
        self.assertNotIn("Visibility", out)
        self.assertGreater(height, 400)

    def test_metric_converts_and_visibility_shows(self):
        out, height = gauges.temp_ring_html(32.0, vis=10.0, vis_note="Goodyear Airport", metric=True)
        self.assertIn("0.0", out)
        self.assertIn("°C", out)
        self.assertIn("Visibility", out)
        self.assertIn("Goodyear Airport", out)
        self.assertGreater(height, 440)

    def test_missing_values_show_dashes_and_escape_note(self):
        out, _ = gauges.temp_ring_html(70.0, vis=3.0, vis_note="<x>")
        self.assertIn("–", out)
        self.assertIn("&lt;x&gt;", out)
        self.assertIn("#FFB020", out)


if __name__ == "__main__":
    unittest.main()
