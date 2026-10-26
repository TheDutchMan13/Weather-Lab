"""12-hour and 24-hour times (0.37.29)."""
import unittest
from datetime import datetime
from pathlib import Path

from weatherlab import timefmt
from weatherlab.settings import Settings


class TimeFormatTests(unittest.TestCase):
    def test_12_hour(self):
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 14, 30, 36), h24=False), "2:30 PM")
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 14, 30, 36), seconds=True, h24=False), "2:30:36 PM")
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 0, 5), h24=False), "12:05 AM")
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 12, 0), h24=False), "12:00 PM")
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 9, 7), h24=False), "9:07 AM")

    def test_24_hour(self):
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 14, 30, 36), h24=True), "14:30")
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 14, 30, 36), seconds=True, h24=True), "14:30:36")
        self.assertEqual(timefmt.time_text(datetime(2026, 10, 26, 0, 5), h24=True), "00:05")

    def test_stamp_and_hover(self):
        dt = datetime(2026, 10, 26, 14, 30)
        self.assertEqual(timefmt.stamp(dt, h24=False), "Oct 26, 2:30 PM")
        self.assertEqual(timefmt.stamp(dt, "%a %b %d, %Y", sep=" at ", h24=True), "Mon Oct 26, 2026 at 14:30")
        self.assertEqual(timefmt.hover_format(False), "%b %d, %-I:%M %p")
        self.assertEqual(timefmt.hover_format(True), "%b %d, %H:%M")

    def test_default_is_12_hour(self):
        self.assertFalse(Settings().time_24h)

    def test_screens_use_it_and_settings_has_the_switch(self):
        root = Path(__file__).resolve().parent.parent / "weatherlab"
        self.assertIn("timefmt.time_text", (root / "screens" / "common.py").read_text(encoding="utf-8"))
        system = (root / "screens" / "system.py").read_text(encoding="utf-8")
        self.assertIn('"Time format"', system)
        self.assertIn("time_24h=time_24h", system)
        for name in ("common", "data", "hazards", "now", "outlook", "live_history", "explore"):
            text = (root / "screens" / f"{name}.py").read_text(encoding="utf-8")
            self.assertNotIn("%H:%M", text, name)
            self.assertNotIn("%I:%M", text, name)


if __name__ == "__main__":
    unittest.main()
