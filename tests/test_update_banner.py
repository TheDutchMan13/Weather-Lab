"""The update line on Home (0.37.48)."""
import pathlib
import unittest

from weatherlab import updates

NOW = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class UpdateBanner(unittest.TestCase):
    def test_shows_only_for_a_newer_version(self):
        self.assertEqual(updates.banner_text("0.38.0", "0.37.48"), "Weather Lab 0.38.0 is available. You have 0.37.48.")
        self.assertIsNone(updates.banner_text("0.37.48", "0.37.48"))
        self.assertIsNone(updates.banner_text("0.37.2", "0.37.48"))
        self.assertIsNone(updates.banner_text("", "0.37.48"))

    def test_official_address_is_the_latest_release(self):
        self.assertTrue(updates.OFFICIAL_URL.endswith("/releases/latest/download/latest.json"))

    def test_banner_is_at_the_top_of_the_refreshing_part_of_home(self):
        start = NOW.index("def live_now() -> None:")
        body = NOW[start:NOW.index("\n@st.fragment", start + 10)]
        self.assertLess(body.index("_update_banner()"), body.index("_hero(s, row"))


if __name__ == "__main__":
    unittest.main()
