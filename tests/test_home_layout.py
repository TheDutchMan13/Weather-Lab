"""Home layout (0.37.42): card rows with wide cards, the page in the sidebar, and Customize as a link."""
import pathlib
import unittest

from weatherlab import card_order, nav_groups

ROOT = pathlib.Path(__file__).resolve().parents[1]
NOW = (ROOT / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class Rows(unittest.TestCase):
    def test_small_cards_share_rows_of_three(self):
        self.assertEqual(card_order.rows(list("abcde"), set()), [["a", "b", "c"], ["d", "e"]])

    def test_a_wide_card_has_a_row_to_itself_and_order_is_kept(self):
        self.assertEqual(card_order.rows(list("abcde"), {"c"}), [["a", "b"], ["c"], ["d", "e"]])

    def test_none_keys_are_always_small(self):
        self.assertEqual(card_order.rows([None, "a"], {None}), [[None, "a"]])

    def test_groups(self):
        self.assertEqual(card_order.group_of("Wind gust"), "Wind and rain")
        self.assertEqual(card_order.group_of("Rain today"), "Wind and rain")
        self.assertEqual(card_order.group_of("Indoor temperature"), "Air")


class Wiring(unittest.TestCase):
    def test_page_is_in_station(self):
        self.assertIn("Home layout", nav_groups.GROUPS["Station"])

    def test_home_links_to_the_page_instead_of_a_popover(self):
        start = NOW.index("def home_page() -> None:")
        body = NOW[start:NOW.index("def alerts_log_page", start)]
        self.assertIn("_customize_link()", body)
        self.assertNotIn("st.popover", NOW)

    def test_humidity_is_only_in_the_last_24_hours_row(self):
        from weatherlab.settings import DEFAULT_CARDS
        self.assertNotIn("humidity", DEFAULT_CARDS)
        self.assertIn('if key in data and key != "humidity":', NOW)
        self.assertIn('choices = [k for k in CARD_LABELS if k != "humidity"]', NOW)

    def test_setting_exists_with_an_empty_default(self):
        from weatherlab.settings import Settings
        self.assertEqual(Settings().wide_cards, [])


if __name__ == "__main__":
    unittest.main()
