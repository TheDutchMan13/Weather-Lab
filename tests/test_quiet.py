"""Quiet hours, including windows that cross midnight."""

import unittest

from weatherlab import quiet


class QuietTests(unittest.TestCase):
    def test_window_inside_one_day(self):
        self.assertTrue(quiet.is_quiet(12, 9, 17))
        self.assertFalse(quiet.is_quiet(20, 9, 17))

    def test_window_crossing_midnight(self):
        self.assertTrue(quiet.is_quiet(23, 22, 6))
        self.assertTrue(quiet.is_quiet(3, 22, 6))
        self.assertFalse(quiet.is_quiet(7, 22, 6))

    def test_same_start_and_end_means_off(self):
        self.assertFalse(quiet.is_quiet(5, 6, 6))


if __name__ == "__main__":
    unittest.main()
