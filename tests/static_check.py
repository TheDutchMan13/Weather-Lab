"""Static checks for modules that can't be imported in a test run (they need Streamlit): names must resolve,
imports between Weather Lab modules must point at names that exist, and modules must not import each other in a loop.
"""

import ast
import builtins
import symtable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}


def undefined_names(source: str, filename: str) -> list[str]:
    """Names that are used in the module but never defined in it or in Python itself."""
    top = symtable.symtable(source, filename, "exec")
    module_names = {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported()}
    problems: list[str] = []
    for sym in top.get_symbols():
        name = sym.get_name()
        if sym.is_referenced() and name not in module_names and name not in ALLOWED:
            problems.append(name)

    def walk(table) -> None:
        for sym in table.get_symbols():
            name = sym.get_name()
            if sym.is_referenced() and sym.is_global() and name not in module_names and name not in ALLOWED:
                problems.append(f"{name} (in {table.get_name()})")
        for child in table.get_children():
            walk(child)

    for child in top.get_children():
        walk(child)
    return sorted(set(problems))


def bindings(tree: ast.Module) -> set[str]:
    """Names a module defines at its top level: functions, classes, assignments and imports."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name))
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
    return names


def module_path(name: str) -> Path | None:
    """The file for a module or package name, or None when there isn't one."""
    base = ROOT / name.replace(".", "/")
    if base.with_suffix(".py").exists():
        return base.with_suffix(".py")
    if (base / "__init__.py").exists():
        return base / "__init__.py"
    return None


def bad_weatherlab_imports(tree: ast.Module) -> list[str]:
    """`from weatherlab... import x` statements that name something the target module doesn't define."""
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("weatherlab"):
            target = module_path(node.module)
            if target is None and not (ROOT / node.module.replace(".", "/")).is_dir():
                problems.append(f"{node.module} does not exist")
                continue
            defined = bindings(ast.parse(target.read_text(encoding="utf-8"))) if target else set()
            for alias in node.names:
                if alias.name not in defined and module_path(f"{node.module}.{alias.name}") is None:
                    problems.append(f"{node.module} has no {alias.name}")
    return problems


def import_cycles(modules: dict[str, ast.Module]) -> list[str]:
    """Cycles among the given modules, using their top-level imports only (the ones that run when a module loads)."""
    graph = {name: set() for name in modules}
    for name, tree in modules.items():
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module in modules:
                graph[name].add(node.module)
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("weatherlab"):
                for alias in node.names:
                    if f"{node.module}.{alias.name}" in modules:
                        graph[name].add(f"{node.module}.{alias.name}")
    found, state = [], {}

    def visit(name: str, trail: list[str]) -> None:
        state[name] = 1
        for nxt in sorted(graph.get(name, ())):
            if state.get(nxt) == 1:
                found.append(" -> ".join(trail + [nxt]))
            elif nxt not in state:
                visit(nxt, trail + [nxt])
        state[name] = 2

    for name in sorted(graph):
        if name not in state:
            visit(name, [name])
    return found
