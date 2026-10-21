"""Parser tests using a sample taken from a real GW2000 response.

Run with:  python -m unittest discover -s tests -v
These tests don't need Streamlit or the network.
"""

import unittest

from weatherlab import parse

SAMPLE = {
    "common_list": [
        {"id": "0x02", "val": "81.9", "unit": "F"},
        {"id": "0x07", "val": "42%"},
        {"id": "3", "val": "81.7", "unit": "F"},
        {"id": "0x03", "val": "56.7", "unit": "F"},
        {"id": "0x0B", "val": "6.26 mph"},
        {"id": "0x0C", "val": "1.12 mph"},
        {"id": "0x15", "val": "0.00 W/m2"},
        {"id": "0x17", "val": "0"},
        {"id": "0x0A", "val": "111"},
    ],
    "piezoRain": [
        {"id": "0x0E", "val": "0.00 in/Hr"},
        {"id": "0x10", "val": "0.00 in"},
        {"id": "0x13", "val": "3.55 in"},
    ],
    "wh25": [{"intemp": "80.8", "unit": "F", "inhumi": "42%", "abs": "28.90 inHg", "rel": "28.90 inHg"}],
}


class ParseTests(unittest.TestCase):
    def test_outdoor(self):
        r = parse.parse_livedata(SAMPLE)
        self.assertEqual(r["tempf"], 81.9)
        self.assertEqual(r["humidity"], 42.0)
        self.assertEqual(r["feelslikef"], 81.7)
        self.assertEqual(r["windspeedmph"], 6.26)
        self.assertEqual(r["winddir"], 111.0)

    def test_rain_uses_only_confirmed_ids(self):
        r = parse.parse_livedata(SAMPLE)
        self.assertEqual(r["rainratein"], 0.0)
        self.assertEqual(r["dailyrainin"], 0.0)
        self.assertNotIn("3.55", str(r))  # yearly rain (0x13) is not mapped yet

    def test_indoor(self):
        r = parse.parse_livedata(SAMPLE)
        self.assertEqual(r["tempinf"], 80.8)
        self.assertEqual(r["humidityin"], 42.0)
        self.assertEqual(r["baromrelin"], 28.9)

    def test_celsius_converted(self):
        r = parse.parse_livedata({"common_list": [{"id": "0x02", "val": "27", "unit": "C"}]})
        self.assertEqual(r["tempf"], 80.6)

    def test_kph_converted(self):
        r = parse.parse_livedata({"common_list": [{"id": "0x0b", "val": "10 km/h"}]})
        self.assertAlmostEqual(r["windspeedmph"], 6.21371, places=3)

    def test_missing_sections_are_skipped(self):
        self.assertEqual(parse.parse_livedata({}), {})

    def test_bad_value_is_skipped(self):
        self.assertEqual(parse.parse_livedata({"common_list": [{"id": "0x02", "val": "--"}]}), {})


class CleanTests(unittest.TestCase):
    def test_out_of_range_dropped(self):
        self.assertEqual(parse.clean({"tempf": 500.0, "humidity": 40.0}), {"humidity": 40.0})

    def test_implausible_without_temperature(self):
        self.assertFalse(parse.plausible({"humidity": 40.0}))

    def test_spike_rejected(self):
        import time
        prev = (time.time(), {"tempf": 80.0})
        self.assertFalse(parse.plausible({"tempf": 99.0}, prev))
        self.assertTrue(parse.plausible({"tempf": 82.0}, prev))


if __name__ == "__main__":
    unittest.main()
