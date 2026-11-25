"""Release descriptions come from What's New (0.37.65)."""

import importlib.util
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("release_notes", Path(__file__).resolve().parent.parent / "tools" / "release_notes.py")
rn = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rn)


class ReleaseNotes(unittest.TestCase):
    def test_one_version(self):
        text = rn.notes("v0.37.65", "v0.37.64")
        self.assertIn("## What's new in 0.37.65", text)
        self.assertNotIn("0.37.64 (", text)
        self.assertIn("compare/v0.37.64...v0.37.65", text)

    def test_skipped_versions_are_included(self):
        text = rn.notes("v0.37.60", "v0.37.57")
        for v in ("0.37.58", "0.37.59", "0.37.60"):
            self.assertIn(f"## What's new in {v}", text)
        self.assertIn("This release includes 0.37.58, 0.37.59, 0.37.60.", text)

    def test_workflow_uses_it(self):
        flow = (Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("tools/release_notes.py", flow)
        self.assertNotIn("--generate-notes", flow)
