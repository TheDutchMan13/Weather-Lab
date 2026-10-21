"""Version comparison for the version check. No network access in tests."""

import unittest

from weatherlab import updates


class UpdateTests(unittest.TestCase):
    def test_newer_versions(self):
        self.assertTrue(updates.newer("0.6.0", "0.5.0"))
        self.assertTrue(updates.newer("v1.0", "0.9.9"))
        self.assertFalse(updates.newer("0.5.0", "0.5.0"))
        self.assertFalse(updates.newer("0.4.9", "0.5.0"))
        self.assertFalse(updates.newer("not a version", "0.5.0"))


if __name__ == "__main__":
    unittest.main()
