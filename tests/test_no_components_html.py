"""Streamlit is removing st.components.v1.html, so Weather Lab uses st.iframe instead (0.37.41)."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class NoComponentsHtml(unittest.TestCase):
    def test_no_code_uses_components_html(self):
        files = [ROOT / "app.py", *sorted((ROOT / "weatherlab").rglob("*.py"))]
        for f in files:
            src = f.read_text(encoding="utf-8")
            self.assertNotIn("components.v1", src, f.name)
            self.assertNotIn("components.html(", src, f.name)


if __name__ == "__main__":
    unittest.main()
