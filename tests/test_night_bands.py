import time
import unittest
from zoneinfo import ZoneInfo

try:
    import plotly.graph_objects as go
    from weatherlab import charts
except ImportError:
    charts = None

PHX = ZoneInfo("America/Phoenix")


@unittest.skipIf(charts is None, "plotly is not installed")
class NightBandTests(unittest.TestCase):
    def test_a_day_gets_about_one_night_band_per_night_in_range(self):
        fig = go.Figure()
        now = time.time()
        charts.night_bands(fig, 33.45, -112.07, PHX, now - 86400, now, False)
        self.assertGreaterEqual(len(fig.layout.shapes), 1)
        self.assertLessEqual(len(fig.layout.shapes), 4)

    def test_no_location_means_no_shading(self):
        fig = go.Figure()
        charts.night_bands(fig, None, None, PHX, 0, 86400, True)
        self.assertEqual(len(fig.layout.shapes or ()), 0)

    def test_polar_day_is_skipped_quietly(self):
        fig = go.Figure()
        charts.night_bands(fig, 89.9, 0, PHX, 1_720_000_000, 1_720_086_400, True)  # no sunset in summer


if __name__ == "__main__":
    unittest.main()
