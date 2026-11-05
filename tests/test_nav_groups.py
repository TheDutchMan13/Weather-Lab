"""The sidebar sections (0.37.13): every page is in exactly one section, in the order of the AZ dashboard."""
import ast
import unittest
from pathlib import Path

from weatherlab import nav_groups


def _dict_keys(source: str, name: str) -> set:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", "") == name for t in node.targets) and isinstance(node.value, ast.Dict):
            return {k.value for k in node.value.keys}
    raise AssertionError(f"{name} not found in app.py")


class NavGroupTests(unittest.TestCase):
    def test_section_order(self):
        self.assertEqual(list(nav_groups.GROUPS), ["Now", "History", "Weather", "Storms", "Station"])

    def test_station_health_replaces_the_three_station_pages(self):
        pages = nav_groups.all_pages()
        self.assertIn("Station health", pages)
        for old in ("Sensors", "Status", "Health check"):
            self.assertNotIn(old, pages)
        source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
        self.assertEqual(_dict_keys(source, "STATION_VIEWS"), {"Status", "Sensors", "Health check"})

    def test_no_page_twice_and_default_is_first(self):
        pages = nav_groups.all_pages()
        self.assertEqual(len(pages), len(set(pages)))
        self.assertEqual(pages[0], nav_groups.DEFAULT_PAGE)

    def test_every_page_has_a_function_and_an_icon(self):
        source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
        pages = set(nav_groups.all_pages())
        plain = _dict_keys(source, "PAGE_FUNCS")
        self.assertEqual(pages, plain | set(nav_groups.TABS))  # a page is either plain or made of tabs (0.37.56)
        self.assertFalse(plain & set(nav_groups.TABS))
        self.assertLessEqual(pages, _dict_keys(source, "PAGE_ICONS"))


class TabbedPageTests(unittest.TestCase):
    """0.37.56: related pages became tabs of one page, so the sidebar has 19 pages instead of 28."""

    def setUp(self):
        self.source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")

    def test_sidebar_is_shorter(self):
        self.assertLessEqual(len(nav_groups.all_pages()), 20)

    def test_every_tab_has_a_function(self):
        tabs = {t for names in nav_groups.TABS.values() for t in names}
        self.assertEqual(tabs, _dict_keys(self.source, "VIEW_FUNCS"))

    def test_every_tabbed_page_is_in_the_sidebar(self):
        self.assertLessEqual(set(nav_groups.TABS), set(nav_groups.all_pages()))

    def test_no_tab_is_in_two_pages(self):
        tabs = [t for names in nav_groups.TABS.values() for t in names]
        self.assertEqual(len(tabs), len(set(tabs)))

    def test_old_pages_lead_to_their_tab(self):
        self.assertEqual(nav_groups.where("Rain calendar"), ("History", "Rain calendar"))
        self.assertEqual(nav_groups.where("Backup"), ("Data", "Backup"))
        self.assertEqual(nav_groups.where("What's New"), ("Help", "What's New"))
        self.assertEqual(nav_groups.where("Data"), ("Data", "Backup"))  # a tabbed page opens on its first tab
        self.assertEqual(nav_groups.where("Radar"), ("Radar", None))

    def test_every_page_from_before_still_has_a_place(self):
        before = {"Home", "Forecast", "Alert history", "Compare stations", "History", "Rain calendar", "Rain events",
                  "Unusual days", "Replay", "Ask", "Air", "Wind", "Wind map", "Sun", "Heat", "Astronomy", "Lightning",
                  "Fire", "Tropics", "Radar", "Station health", "Stations", "Settings", "Home layout", "Reports",
                  "Import", "Export", "Backup", "Help", "What's New"}
        here = set(nav_groups.all_pages()) | set(nav_groups.moved())
        self.assertLessEqual(before, here)

    def test_moved_names_have_icons(self):
        self.assertLessEqual(set(nav_groups.moved()), _dict_keys(self.source, "PAGE_ICONS"))

    def test_view_key_is_stable(self):
        self.assertEqual(nav_groups.view_key("Air and heat"), "view_air_and_heat")
