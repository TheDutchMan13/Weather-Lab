"""What's New entries: the newest matches the app version, and every entry has items."""

import unittest

from weatherlab import whats_new
from weatherlab.config import APP_VERSION


class WhatsNewTests(unittest.TestCase):
    def test_newest_entry_matches_the_app_version(self):
        self.assertEqual(whats_new.ENTRIES[0]["version"], APP_VERSION)

    def test_every_entry_has_a_date_and_items(self):
        for entry in whats_new.ENTRIES:
            self.assertTrue(entry["date"])
            self.assertTrue(entry["items"])


if __name__ == "__main__":
    unittest.main()
