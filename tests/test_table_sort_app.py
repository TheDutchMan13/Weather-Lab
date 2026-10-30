"""The Sort by control on a table, run through Streamlit's own test runner (0.37.45)."""
import unittest

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # streamlit isn't installed
    AppTest = None


def _long_table():
    from weatherlab import theme
    rows = [{"Day": f"Mon Oct {d:02d}, 2026", "Rain": ("--" if d == 5 else f"{d % 4}.{d} in"), "Length": f"{d} min"}
            for d in range(1, 9)]
    theme.table(rows, sort_key="demo")


def _short_table():
    from weatherlab import theme
    theme.table([{"A": "1"}, {"A": "2"}], sort_key="short")


@unittest.skipIf(AppTest is None, "streamlit is not installed")
class SortControl(unittest.TestCase):
    def _table_html(self, at):
        return next(m.value for m in at.markdown if "<table" in m.value)

    def test_control_lists_readable_columns(self):
        at = AppTest.from_function(_long_table).run()
        self.assertFalse(at.exception)
        self.assertEqual(list(at.selectbox[0].options), ["Original order", "Day", "Rain", "Length"])

    def test_sorting_by_a_column_reorders_the_rows(self):
        at = AppTest.from_function(_long_table).run()
        before = self._table_html(at)
        self.assertLess(before.index("Oct 01"), before.index("Oct 08"))
        at.selectbox[0].select("Length").run()          # highest first by default
        after = self._table_html(at)
        self.assertLess(after.index("Oct 08"), after.index("Oct 01"))
        at.toggle[0].set_value(False).run()             # lowest first
        again = self._table_html(at)
        self.assertLess(again.index("Oct 01"), again.index("Oct 08"))

    def test_missing_values_stay_last_whichever_way(self):
        at = AppTest.from_function(_long_table).run()
        at.selectbox[0].select("Rain").run()
        for high in (True, False):
            at.toggle[0].set_value(high).run()
            html = self._table_html(at)
            self.assertGreater(html.index("Oct 05"), max(html.index(f"Oct 0{d}") for d in (1, 2, 3, 4, 6, 7, 8)))

    def test_a_short_table_has_no_control(self):
        at = AppTest.from_function(_short_table).run()
        self.assertEqual(len(at.selectbox), 0)


if __name__ == "__main__":
    unittest.main()
