"""Static checks on app.py and the screen modules: every name resolves, imports point at real names, no import loops."""

import ast
import unittest
from pathlib import Path

from tests import static_check as sc

ROOT = Path(__file__).resolve().parents[1]


def screen_files() -> dict[str, Path]:
    files = {"app": ROOT / "app.py"}
    for path in sorted((ROOT / "weatherlab" / "screens").glob("*.py")):
        files[f"weatherlab.screens.{path.stem}"] = path
    return files


class StaticNameTests(unittest.TestCase):
    def test_every_name_in_app_and_screens_resolves(self):
        for name, path in screen_files().items():
            with self.subTest(module=name):
                self.assertEqual(sc.undefined_names(path.read_text(encoding="utf-8"), str(path)), [])

    def test_imports_between_weatherlab_modules_point_at_real_names(self):
        for name, path in screen_files().items():
            with self.subTest(module=name):
                tree = ast.parse(path.read_text(encoding="utf-8"))
                self.assertEqual(sc.bad_weatherlab_imports(tree), [])

    def test_screen_modules_do_not_import_each_other_in_a_loop(self):
        modules = {name: ast.parse(path.read_text(encoding="utf-8")) for name, path in screen_files().items()}
        self.assertEqual(sc.import_cycles(modules), [])

    def test_the_checker_catches_an_undefined_name(self):
        sample = "import os\ndef f():\n    return missing_thing + os.sep\n"
        self.assertIn("missing_thing (in f)", sc.undefined_names(sample, "sample.py"))

    def test_the_checker_accepts_locals_comprehensions_and_builtins(self):
        sample = ("import os\n"
                  "def f(x):\n"
                  "    y = [v * 2 for v in x if v]\n"
                  "    return len(y) + len(os.sep)\n")
        self.assertEqual(sc.undefined_names(sample, "sample.py"), [])


if __name__ == "__main__":
    unittest.main()
