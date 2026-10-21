"""app.py builds its page table when it loads, so every page function must be defined before the table names it."""

import ast
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"


class PageTableTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tree = ast.parse(APP.read_text(encoding="utf-8"))
        self.defined: dict[str, int] = {}
        for node in self.tree.body:
            if isinstance(node, ast.FunctionDef):
                self.defined.setdefault(node.name, node.lineno)

    def test_page_table_entries_are_defined_before_use(self) -> None:
        problems = []
        for node in self.tree.body:
            if not isinstance(node, ast.Assign):
                continue
            is_table = any(isinstance(t, ast.Name) and t.id == "PAGE_FUNCS" for t in node.targets)
            is_entry = any(isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name)
                           and t.value.id == "PAGE_FUNCS" for t in node.targets)
            if is_table and isinstance(node.value, ast.Dict):
                values = list(node.value.values)
            elif is_entry:
                values = [node.value]
            else:
                continue
            for value in values:
                if isinstance(value, ast.Name):
                    where = self.defined.get(value.id)
                    if where is None or where >= node.lineno:
                        problems.append(f"line {node.lineno}: {value.id} is used before it is defined")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
