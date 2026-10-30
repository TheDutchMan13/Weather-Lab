"""Getting started on Home (0.37.49)."""
import pathlib
import unittest
from dataclasses import replace

from weatherlab import checklist
from weatherlab.settings import Settings

NOW = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class Items(unittest.TestCase):
    def test_a_new_install_has_everything_to_do(self):
        todo = checklist.pending(checklist.items(Settings(), has_topic=False, has_backup=False))
        self.assertEqual([i.key for i in todo], ["location", "alerts", "backup", "updates"])

    def test_items_tick_off(self):
        s = replace(Settings(), latitude=33.4, longitude=-112.0, update_url="https://example.com/latest.json")
        todo = checklist.pending(checklist.items(s, has_topic=True, has_backup=True))
        self.assertEqual(todo, [])

    def test_location_needs_both_numbers(self):
        s = replace(Settings(), latitude=33.4)
        self.assertFalse(checklist.items(s, True, True)[0].done)

    def test_links_name_real_pages_and_tabs(self):
        from weatherlab import nav_groups
        pages = nav_groups.all_pages()
        for item in checklist.items(Settings(), False, False):
            self.assertIn(item.page, pages, item.key)
        settings_src = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "system.py").read_text(encoding="utf-8")
        for item in checklist.items(Settings(), False, False):
            if item.tab:
                self.assertIn(f'"{item.tab.capitalize()}"', settings_src, item.tab)


class Wiring(unittest.TestCase):
    def test_list_sits_under_the_reading_and_can_be_hidden(self):
        start = NOW.index("def home_page() -> None:")
        body = NOW[start:NOW.index("def alerts_log_page", start)]
        self.assertLess(body.index("live_now()"), body.index("_checklist(s)"))
        self.assertIn("checklist_hidden=True", NOW)
        self.assertIn("home_show_checklist", NOW)

    def test_default_is_shown(self):
        self.assertFalse(Settings().checklist_hidden)


if __name__ == "__main__":
    unittest.main()
