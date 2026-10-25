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
        self.assertEqual(list(nav_groups.GROUPS), ["Now", "History", "Air, sun and heat", "Forecast and storms",
                                                   "Season", "Tools", "Health", "Settings"])

    def test_no_page_twice_and_default_is_first(self):
        pages = nav_groups.all_pages()
        self.assertEqual(len(pages), len(set(pages)))
        self.assertEqual(pages[0], nav_groups.DEFAULT_PAGE)

    def test_every_page_has_a_function_and_an_icon(self):
        source = (Path(__file__).resolve().parent.parent / "app.py").read_text(encoding="utf-8")
        pages = set(nav_groups.all_pages())
        self.assertEqual(pages, _dict_keys(source, "PAGE_FUNCS"))
        self.assertLessEqual(pages, _dict_keys(source, "PAGE_ICONS"))
