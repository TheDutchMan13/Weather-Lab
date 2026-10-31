"""Find a setting (0.37.53) and notice ages."""
import unittest

from weatherlab import card_order, settings_index
from weatherlab.screens import system


class SettingsIndexTests(unittest.TestCase):
    def test_every_tab_exists(self):
        for name, tab in settings_index.ENTRIES:
            self.assertIsNotNone(system.area_for_tab(tab.lower())[0], name)

    def test_names_are_unique(self):
        names = [n for n, _ in settings_index.ENTRIES]
        self.assertEqual(len(names), len(set(names)))

    def test_tab_of(self):
        self.assertEqual(settings_index.tab_of("Quiet hours"), "Alerts")
        self.assertIsNone(settings_index.tab_of("Nope"))


class AgoTests(unittest.TestCase):
    def test_ago(self):
        self.assertEqual(card_order.ago(30), "just now")
        self.assertEqual(card_order.ago(12 * 60 + 5), "12 min ago")
        self.assertEqual(card_order.ago(2 * 3600), "2 h ago")
        self.assertEqual(card_order.ago(2 * 3600 + 5 * 60), "2 h 5 min ago")
        self.assertEqual(card_order.ago(-5), "just now")


if __name__ == "__main__":
    unittest.main()
