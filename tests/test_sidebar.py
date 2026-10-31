"""The sidebar's pins and folding groups (0.37.53)."""
import unittest

from weatherlab import sidebar


class PinTests(unittest.TestCase):
    def test_pin_and_unpin(self):
        pins = sidebar.toggle_pin([], "Home")
        self.assertEqual(pins, ["Home"])
        pins = sidebar.toggle_pin(pins, "Radar")
        self.assertEqual(pins, ["Home", "Radar"])
        self.assertEqual(sidebar.toggle_pin(pins, "Home"), ["Radar"])

    def test_clean_drops_unknown_and_repeats(self):
        self.assertEqual(sidebar.clean_pins(["Setup", "Home", "Home", "Radar"]), ["Home", "Radar"])

    def test_at_most_max(self):
        from weatherlab.nav_groups import all_pages
        many = all_pages()[:sidebar.MAX_PINS + 3]
        self.assertEqual(len(sidebar.clean_pins(many)), sidebar.MAX_PINS)
        self.assertEqual(sidebar.toggle_pin(many[:sidebar.MAX_PINS], many[-1]), many[:sidebar.MAX_PINS])


class GroupTests(unittest.TestCase):
    def test_open_unless_closed(self):
        self.assertTrue(sidebar.is_open("Storms", [], "Home"))
        self.assertFalse(sidebar.is_open("Storms", ["Storms"], "Home"))

    def test_group_of_open_page_stays_open(self):
        self.assertTrue(sidebar.is_open("Storms", ["Storms"], "Radar"))

    def test_set_open(self):
        closed = sidebar.set_open([], "History", False)
        self.assertEqual(closed, ["History"])
        self.assertEqual(sidebar.set_open(closed, "History", True), [])
        self.assertEqual(sidebar.set_open(["Gone", "History"], "Storms", False), ["History", "Storms"])


if __name__ == "__main__":
    unittest.main()
