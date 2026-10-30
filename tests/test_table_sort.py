"""Sorting a table by the value in its text cells (0.37.45)."""
import pathlib
import unittest

from weatherlab import table_sort as ts

ROOT = pathlib.Path(__file__).resolve().parents[1]


class SortValue(unittest.TestCase):
    def test_numbers_with_units_and_commas(self):
        self.assertEqual(ts.sort_value("12.3 mph"), (False, 12.3))
        self.assertEqual(ts.sort_value("1,204"), (False, 1204.0))
        self.assertEqual(ts.sort_value("-5 \u00b0F"), (False, -5.0))
        self.assertEqual(ts.sort_value("\u22125%"), (False, -5.0))

    def test_ten_sorts_above_nine_unlike_text(self):
        self.assertGreater(ts.sort_value("10 mph")[1], ts.sort_value("9 mph")[1])
        self.assertLess("10 mph", "9 mph")  # plain text order is the bug this avoids

    def test_times_and_durations(self):
        self.assertLess(ts.sort_value("9:05 AM")[1], ts.sort_value("12:10 PM")[1])
        self.assertLess(ts.sort_value("12:10 AM")[1], ts.sort_value("1:00 AM")[1])
        self.assertEqual(ts.sort_value("1 h 5 min"), (False, 65.0))
        self.assertEqual(ts.sort_value("45 min"), (False, 45.0))
        self.assertLess(ts.sort_value("45 min")[1], ts.sort_value("1 h 5 min")[1])

    def test_dates_with_a_year(self):
        self.assertLess(ts.sort_value("Mon Dec 29, 2025")[1], ts.sort_value("Thu Jan 01, 2026")[1])
        self.assertLess(ts.sort_value("2026-01-02")[1], ts.sort_value("2026-01-10")[1])

    def test_missing_and_unreadable(self):
        self.assertEqual(ts.sort_value("--"), (True, 0.0))
        self.assertIsNone(ts.sort_value("Mon Oct 29"))  # no year, so no safe order
        self.assertIsNone(ts.sort_value("Heat index peak"))


class Columns(unittest.TestCase):
    ROWS = [{"Day": "Mon Oct 27, 2026", "Rain": "0.20 in", "Note": "wet"},
            {"Day": "Tue Oct 28, 2026", "Rain": "--", "Note": "dry"},
            {"Day": "Wed Oct 29, 2026", "Rain": "1.10 in", "Note": "wet"}]

    def test_only_readable_columns_are_offered(self):
        self.assertEqual(ts.sortable_columns(self.ROWS), ["Day", "Rain"])

    def test_a_column_with_no_values_is_not_offered(self):
        self.assertEqual(ts.sortable_columns([{"A": "--"}, {"A": "--"}]), [])

    def test_sort_highest_first_keeps_missing_last(self):
        self.assertEqual([r["Rain"] for r in ts.sort_rows(self.ROWS, "Rain", True)], ["1.10 in", "0.20 in", "--"])

    def test_sort_lowest_first_still_keeps_missing_last(self):
        self.assertEqual([r["Rain"] for r in ts.sort_rows(self.ROWS, "Rain", False)], ["0.20 in", "1.10 in", "--"])

    def test_equal_values_keep_their_order(self):
        rows = [{"n": "1", "id": "a"}, {"n": "1", "id": "b"}, {"n": "2", "id": "c"}]
        self.assertEqual([r["id"] for r in ts.sort_rows(rows, "n", True)], ["c", "a", "b"])


class Wiring(unittest.TestCase):
    def test_long_tables_ask_for_a_sort_control(self):
        for name, key in (("screens/history.py", "ranking"), ("screens/history.py", "daily_rows"),
                          ("screens/explore.py", "rain_events"), ("screens/explore.py", "unusual_days")):
            src = (ROOT / "weatherlab" / name).read_text(encoding="utf-8")
            self.assertIn(f'sort_key="{key}"', src, key)

    def test_short_tables_have_no_control(self):
        from weatherlab import theme
        self.assertGreaterEqual(theme.SORT_MIN_ROWS, 6)


if __name__ == "__main__":
    unittest.main()
