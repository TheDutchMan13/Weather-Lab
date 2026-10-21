"""Station offline watch: one message when readings stop, one when they resume."""

import unittest

from weatherlab import station_watch as sw


class StationWatchTests(unittest.TestCase):
    def test_offline_once_then_back(self):
        was, text = sw.check(False, 1000, 1000 + 901)
        self.assertTrue(was)
        self.assertIn("15 minutes", text)
        was, text = sw.check(True, 1000, 1000 + 1200)
        self.assertTrue(was)
        self.assertIsNone(text)
        was, text = sw.check(True, 1000, 1000 + 100)
        self.assertFalse(was)
        self.assertIn("sending readings again", text)

    def test_unknown_last_reading_is_quiet(self):
        self.assertEqual(sw.check(False, None, 5000), (False, None))


if __name__ == "__main__":
    unittest.main()
