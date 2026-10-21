"""Finding the station: the address list for the local network. No network access in tests."""

import unittest

from weatherlab import discover


class DiscoverTests(unittest.TestCase):
    def test_candidates_cover_the_range_except_this_computer(self):
        hosts = discover.candidates("192.168.1.50")
        self.assertEqual(len(hosts), 253)
        self.assertNotIn("192.168.1.50", hosts)
        self.assertIn("192.168.1.1", hosts)
        self.assertIn("192.168.1.254", hosts)


if __name__ == "__main__":
    unittest.main()
