"""Every Live reading card with history is a chart, not a plain number (0.37.19)."""
import pathlib
import unittest

SRC = (pathlib.Path(__file__).resolve().parents[1] / "weatherlab" / "screens" / "now.py").read_text(encoding="utf-8")


class LiveChartCards(unittest.TestCase):
    def test_air_and_wind_cards_use_trend_cards(self):
        start = SRC.index("        air, wind = [], []")
        end = SRC.index("        compact = st.toggle", start)
        body = SRC[start:end]
        self.assertIn("_trend_card(s, key, label, unit, data, day", body)
        self.assertIn("_tile(label, text)", body)  # fallback when there is no series

    def test_rain_shows_two_decimals(self):
        self.assertIn('decimals = 2 if key == "dailyrainin" else 0', SRC)

    def test_trend_colours_cover_the_live_cards(self):
        for key in ("tempf", "humidity", "windspeedmph", "windgustmph", "dailyrainin"):
            self.assertIn(f'"{key}": "#', SRC)


if __name__ == "__main__":
    unittest.main()
