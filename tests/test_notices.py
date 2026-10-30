"""Notices in one strip under the hero (0.37.47), the hero line without a stray dot, and one High contrast scheme."""
import ast
import collections
import pathlib
import unittest

from weatherlab import card_order, hero

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOW = (ROOT / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class Notices(unittest.TestCase):
    def test_label(self):
        self.assertEqual(card_order.notice_label(1), "1 notice")
        self.assertEqual(card_order.notice_label(3), "3 notices")

    def test_strip_comes_after_the_hero(self):
        start = NOW.index("def live_now() -> None:")
        body = NOW[start:NOW.index("\n@st.fragment", start + 10)]
        self.assertIn("    _hero(s, row, short, night, alerts)\n    _notices(s, poller, status)\n", body)
        self.assertNotIn("st.warning(", body)
        self.assertNotIn("_warnings(", NOW)


class HeroLine(unittest.TestCase):
    def test_no_trailing_dot_without_a_label(self):
        out, _ = hero.hero_html({"temp_text": "69°", "feels": "71 °F"})
        self.assertIn("Feels like 71 °F</div>", out)
        self.assertNotIn("Feels like 71 °F · </div>", out)

    def test_parts_are_joined_once(self):
        out, _ = hero.hero_html({"temp_text": "69°", "feels": "71 °F", "label": "Sunny", "place": "Goodyear"})
        self.assertIn("Feels like 71 °F · Sunny · Goodyear</div>", out)


class OneHighContrast(unittest.TestCase):
    def test_no_scheme_is_defined_twice(self):
        src = (ROOT / "weatherlab" / "theme.py").read_text(encoding="utf-8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SCHEMES":
                keys = [k.value for k in node.value.keys]
                self.assertEqual([k for k, c in collections.Counter(keys).items() if c > 1], [])


if __name__ == "__main__":
    unittest.main()
