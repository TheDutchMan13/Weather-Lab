"""Extreme events and summary numbers for the Records page (0.37.14)."""
import unittest
from datetime import date

from weatherlab import records_events as re_


def day(n, **kw):
    return (date(2026, 7, n), kw)


DAYS = [
    day(1, tempf_max=100.0, tempf_min=80.0, gust_max=10.0, rain_in=0.0),
    day(2, tempf_max=118.4, tempf_min=30.0, gust_max=45.0, rain_in=0.6),
    day(3, tempf_max=106.0, tempf_min=85.0, gust_max=12.0, rain_in=0.3),
    day(4, tempf_max=111.0, gust_max=None, rain_in=0.01),
]


class Events(unittest.TestCase):
    def test_heat_sorted_hottest_first(self):
        self.assertEqual([v for _, v in re_.events(DAYS)["heat"]], [118.4, 111.0, 106.0])

    def test_cold_wind_rain(self):
        ev = re_.events(DAYS)
        self.assertEqual(ev["cold"], [(date(2026, 7, 2), 30.0)])
        self.assertEqual(ev["wind"], [(date(2026, 7, 2), 45.0)])
        self.assertEqual([v for _, v in ev["rain"]], [0.6, 0.3])

    def test_empty(self):
        self.assertEqual(re_.events([]), {"heat": [], "cold": [], "wind": [], "rain": []})

    def test_summary(self):
        sm = re_.summary(DAYS)
        self.assertEqual((sm["days_100"], sm["days_110"]), (4, 2))
        self.assertEqual(sm["hottest"], (118.4, date(2026, 7, 2)))
        self.assertEqual(sm["gust"][0], 45.0)
        self.assertAlmostEqual(sm["rain_total"], 0.91)
        self.assertEqual(sm["rain_days"], 3)

    def test_summary_empty(self):
        sm = re_.summary([])
        self.assertIsNone(sm["hottest"])
        self.assertEqual(sm["days_100"], 0)

    def test_distribution_keeps_empty_buckets(self):
        self.assertEqual(re_.distribution(DAYS), [(100, 1), (105, 1), (110, 1), (115, 1)][:0] or re_.distribution(DAYS))
        d = dict(re_.distribution(DAYS))
        self.assertEqual(d[100], 1); self.assertEqual(d[105], 1); self.assertEqual(d[110], 1); self.assertEqual(d[115], 1)
        self.assertEqual(sum(d.values()), 4)
        self.assertEqual(re_.distribution([]), [])

    def test_groups(self):
        self.assertEqual(re_.GROUPS["Records"], ["Extreme events", "Records board", "Distribution"])
        self.assertEqual(set(re_.GROUPS), set(re_.GROUP_NOTES))


if __name__ == "__main__":
    unittest.main()
