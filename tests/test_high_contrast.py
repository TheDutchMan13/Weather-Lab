import unittest

try:
    from weatherlab import theme
except ImportError:
    theme = None


def ratio(a: str, b: str) -> float:
    def lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


@unittest.skipIf(theme is None, "streamlit is not installed")
class HighContrastTests(unittest.TestCase):
    def test_listed_as_a_scheme(self):
        self.assertIn("High contrast", theme.SCHEMES)

    def test_text_and_accent_meet_wcag_aaa_on_both_backgrounds(self):
        for dark in (False, True):
            pg = theme.page_palette(dark, "High contrast")
            for key in ("text", "text_muted", "accent"):
                self.assertGreaterEqual(ratio(pg[key], pg["background"]), 7, (dark, key))
                self.assertGreaterEqual(ratio(pg[key], pg["surface"]), 7, (dark, key))

    def test_css_builds(self):
        self.assertIn("#000000", theme.css(False, "High contrast"))


if __name__ == "__main__":
    unittest.main()
