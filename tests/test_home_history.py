"""Home and the combined History page (0.37.31): the pages exist once, in the right sections."""
import ast
import unittest
from pathlib import Path

from weatherlab import nav_groups

ROOT = Path(__file__).resolve().parent.parent


class HomeHistoryTests(unittest.TestCase):
    def test_home_opens_first(self):
        self.assertEqual(nav_groups.DEFAULT_PAGE, "Home")
        self.assertEqual(nav_groups.GROUPS["Now"][0], "Home")

    def test_merged_pages_are_gone_from_the_menu(self):
        pages = [p for names in nav_groups.GROUPS.values() for p in names]
        for old in ("Live", "Briefing", "Daily", "Records", "Rankings", "My year", "Climate charts"):
            self.assertNotIn(old, pages)
        self.assertEqual(nav_groups.GROUPS["History"], ["History"])
        for old in ("Coverage", "Rewind"):
            self.assertNotIn(old, pages)

    def test_history_views(self):
        tree = ast.parse((ROOT / "weatherlab/screens/history.py").read_text(encoding="utf-8"))
        views = next(ast.literal_eval(n.value) for n in tree.body
                     if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "HISTORY_VIEWS")
        self.assertEqual(views, ["Daily", "Records", "Rankings", "Compare", "Month", "Year", "Rewind", "Coverage"])


if __name__ == "__main__":
    unittest.main()
