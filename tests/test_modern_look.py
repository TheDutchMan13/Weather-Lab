"""The modern look (0.37.33): one set of corner sizes and shadows, and well-formed styles for every scheme."""
import importlib
import sys
import types
import unittest


def _theme():
    """weatherlab.theme, with a stand-in for Streamlit when it isn't installed. The stand-in is removed again so
    other tests still see that Streamlit is missing."""
    try:
        importlib.import_module("streamlit")
        return importlib.import_module("weatherlab.theme")
    except ImportError:
        pass
    st = types.ModuleType("streamlit")
    st.context = None
    st.get_option = lambda key: None
    sys.modules["streamlit"] = st
    try:
        return importlib.import_module("weatherlab.theme")
    finally:
        del sys.modules["streamlit"]


class ModernLookTests(unittest.TestCase):
    def test_tokens(self):
        theme = _theme()
        self.assertEqual(theme.RADIUS["md"], 14)
        self.assertTrue(theme.RADIUS["sm"] < theme.RADIUS["md"] < theme.RADIUS["lg"])
        self.assertEqual(set(theme.SHADOW), {True, False})

    def test_styles_are_well_formed(self):
        theme = _theme()
        for dark in (True, False):
            for scheme in theme.SCHEMES:
                out = theme.css(dark, scheme)
                self.assertEqual(out.count("{"), out.count("}"), (dark, scheme))
                self.assertIn(".wl-card{", out)
                self.assertIn("@keyframes wl-fade", out)

    def test_high_contrast_has_no_shadows(self):
        theme = _theme()
        tile = next(r for r in theme.css(True, "High contrast").split("}") if r.startswith(".wl-tile{"))
        self.assertIn("box-shadow:none", tile)

    def test_skeleton(self):
        html = _theme().skeleton_html((40, 60))
        self.assertEqual(html.count('class="wl-skel"'), 2)
        self.assertIn('aria-hidden="true"', html)


if __name__ == "__main__":
    unittest.main()
