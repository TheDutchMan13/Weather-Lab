"""The shareable year card (0.37.27)."""
import io
import unittest

from PIL import Image

from tests.test_api_pages import ApiHelpers
from weatherlab import api_pages, year_image

CARD = {"year": 2026, "found": True, "temp_unit": "°F", "rain_unit": "in", "wind_unit": "mph", "days_100": 88,
        "hottest": {"date": "2026-07-08", "value": 118.0}, "wettest": {"date": "2026-08-14", "value": 1.31},
        "longest_hot": {"days": 21, "from": "2026-06-20", "to": "2026-07-10"}, "rain": 6.2, "rainy_days": 24,
        "windiest": {"date": "2026-09-03", "value": 61.0}}


class YearImageTests(unittest.TestCase):
    def test_facts(self):
        rows = year_image.facts(CARD)
        self.assertEqual(rows[0], ("Hottest day", "118°F", "Jul 8"))
        self.assertIn(("Longest hot streak", "21 days", "Jun 20 to Jul 10"), rows)
        self.assertIn(("Wettest day", "1.31 in", "Aug 14"), rows)
        self.assertEqual(len(rows), 6)

    def test_facts_skip_missing(self):
        rows = year_image.facts({"year": 2026, "days_100": 0, "temp_unit": "°F"})
        self.assertEqual(rows, [("Days at 100°F or more", "0", "")])

    def test_render_is_a_png(self):
        png = year_image.render(CARD, "Home")
        img = Image.open(io.BytesIO(png))
        self.assertEqual(img.format, "PNG")
        self.assertEqual(img.size, (year_image.WIDTH, year_image.HEIGHT))

    def test_render_with_nothing_but_the_year(self):
        Image.open(io.BytesIO(year_image.render({"year": 2025})))


class YearCardApiTests(ApiHelpers, unittest.TestCase):
    def test_new_fields(self):
        self.seed_days()
        body = api_pages.year_card(self.db, self.s, self.now, self.today.year)
        self.assertTrue(body["found"])
        self.assertEqual(body["wettest"]["value"], 1.2)
        self.assertIn("longest_hot", body)

    def test_longest_hot(self):
        from datetime import date
        rows = [(date(2026, 6, d), {"tempf_max": 101 if d in (3, 4, 5, 9) else 90}) for d in range(1, 12)]
        self.assertEqual(api_pages._longest_hot(rows), (3, date(2026, 6, 3), date(2026, 6, 5)))


if __name__ == "__main__":
    unittest.main()


class PageWiringTests(unittest.TestCase):
    def test_my_year_offers_the_picture(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parent.parent / "weatherlab" / "screens" / "history.py").read_text(encoding="utf-8")
        self.assertIn("Save as image", source)
        self.assertIn("year_image.render", source)
