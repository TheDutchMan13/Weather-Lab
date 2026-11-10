"""Place search parsing for the setup wizard (0.37.60)."""

import json
import unittest
from unittest import mock

from weatherlab import geocode


SAMPLE = json.dumps({"results": [
    {"name": "Springfield", "admin1": "Illinois", "country": "United States", "latitude": 39.80172,
     "longitude": -89.64371, "timezone": "America/Chicago", "elevation": 182.0},
    {"name": "Springfield", "admin1": "Missouri", "country": "United States", "latitude": 37.21533,
     "longitude": -93.29824, "timezone": "America/Chicago"},
    {"name": "Broken"},
]})


class GeocodeTests(unittest.TestCase):
    def test_parse(self):
        places = geocode.parse(SAMPLE)
        self.assertEqual(len(places), 2)
        self.assertEqual(places[0]["label"], "Springfield, Illinois, United States")
        self.assertEqual((places[0]["lat"], places[0]["lon"], places[0]["timezone"]), (39.80172, -89.64371, "America/Chicago"))
        self.assertEqual(places[0]["elevation"], 182.0)
        self.assertIsNone(places[1]["elevation"])

    def test_nothing_found_and_blank(self):
        self.assertEqual(geocode.parse("{}"), [])
        self.assertEqual(geocode.search("   "), [])

    def test_network_failure_is_plain(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError()):
            with self.assertRaises(geocode.GeocodeError) as ctx:
                geocode.search("Springfield")
        self.assertIn("didn't answer in time", str(ctx.exception))
        self.assertNotIn("TimeoutError", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
