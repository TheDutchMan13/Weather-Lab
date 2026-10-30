"""Setup and Settings are one page from 0.37.52: a ?tab= link opens the right half and tab."""
import unittest

from weatherlab import checklist, nav_groups
from weatherlab.screens import system


class AreaForTabTests(unittest.TestCase):
    def test_station_tabs(self):
        self.assertEqual(system.area_for_tab("station"), ("Station", "Station"))
        self.assertEqual(system.area_for_tab("Access"), ("Station", "Access"))

    def test_app_tabs(self):
        self.assertEqual(system.area_for_tab("updates"), ("App", "Updates"))
        self.assertEqual(system.area_for_tab("phone alerts"), ("App", "Phone alerts"))

    def test_unknown_or_empty(self):
        self.assertEqual(system.area_for_tab(""), (None, None))
        self.assertEqual(system.area_for_tab("nope"), (None, None))

    def test_tab_names_do_not_overlap(self):
        self.assertFalse({n.lower() for n in system.STATION_TABS} & {n.lower() for n in system.APP_TABS})


class SetupIsGoneTests(unittest.TestCase):
    def test_setup_not_in_sidebar(self):
        self.assertNotIn("Setup", [p for pages in nav_groups.GROUPS.values() for p in pages])

    def test_checklist_links_resolve(self):
        class S:
            latitude = None; longitude = None; update_url = ""
        for item in checklist.items(S(), False, False):
            if item.page == "Settings":
                self.assertIsNotNone(system.area_for_tab(item.tab)[0], item.key)


if __name__ == "__main__":
    unittest.main()
