"""The dew point moved from the top of the Live page to a card at the bottom (0.37.16)."""
import pathlib
import unittest

SRC = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class LiveDewCard(unittest.TestCase):
    def test_no_dew_line_at_top(self):
        start = SRC.index("def home_page() -> None:")
        end = SRC.index("def alerts_log_page", start)
        self.assertNotIn("_dew_line", SRC[start:end])

    def test_dew_card_is_in_live_readings_with_trend(self):
        start = SRC.index("def live_readings() -> None:")
        end = SRC.index("def _status_dot", start)
        body = SRC[start:end]
        self.assertIn('_trend_card(s, "dewpointf"', body)
        self.assertLess(body.index('_trend_card(s, "dewpointf"'), body.index("live_history.show_pending()"))

    def test_version_entry(self):
        from weatherlab import config, whats_new
        self.assertEqual(whats_new.ENTRIES[0]["version"], config.APP_VERSION)


class LiveRoomyCards(unittest.TestCase):
    def test_live_page_injects_roomier_card_css(self):
        start = SRC.index("def home_page() -> None:")
        self.assertIn("LIVE_ROOMY_CSS", SRC[start:SRC.index("def alerts_log_page", start)])
        self.assertIn(".wl-tile{padding:16px 18px !important}", SRC)


if __name__ == "__main__":
    unittest.main()
