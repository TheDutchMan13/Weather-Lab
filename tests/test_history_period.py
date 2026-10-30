"""One Period control at the top of History (0.37.50)."""
import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from weatherlab import daily_ranges as dr

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None


TODAY = date(2026, 10, 30)
DAYS = [(TODAY - timedelta(days=n), {"tempf_max": 90 + n}) for n in range(1, 61)]


class PeriodLogic(unittest.TestCase):
    TODAY, DAYS = TODAY, DAYS

    def test_period_days(self):
        self.assertEqual(dr.period_days("30 days"), 30)
        self.assertIsNone(dr.period_days("All"))
        self.assertIsNone(dr.period_days(None))      # nothing picked: the default, all time
        self.assertIsNone(dr.period_days("nonsense"))

    def test_in_period_keeps_the_last_n_days(self):
        self.assertEqual(len(dr.in_period(self.DAYS, 7, self.TODAY)), 7)
        self.assertEqual(len(dr.in_period(self.DAYS, 30, self.TODAY)), 30)
        self.assertEqual(len(dr.in_period(self.DAYS, None, self.TODAY)), 60)
        self.assertEqual(min(d for d, _ in dr.in_period(self.DAYS, 7, self.TODAY)), self.TODAY - timedelta(days=7))

    def test_which_views_show_the_control(self):
        for view in ("Records", "Rankings", "Coverage"):
            self.assertTrue(dr.shows_period(view, None))
        self.assertFalse(dr.shows_period("Daily", "1 day"))
        self.assertTrue(dr.shows_period("Daily", "Several days"))
        for view in ("Compare", "Month", "Year", "Rewind"):
            self.assertFalse(dr.shows_period(view, None))


def _history_app():
    from weatherlab.screens.history import history_page
    history_page()


@unittest.skipIf(AppTest is None, "streamlit is not installed")
class HistoryPageControl(unittest.TestCase):
    def setUp(self):
        self._old = os.environ.get("APPDATA")
        os.environ["APPDATA"] = tempfile.mkdtemp()
        from weatherlab import storage
        db = storage.connect()
        today = date.today()
        with db:
            for n in range(1, 61):  # 60 days; the hottest day is 50 days ago
                d = today - timedelta(days=n)
                db.execute("INSERT INTO daily (date, data) VALUES (?, ?)",
                           (d.isoformat(), json.dumps({"tempf_max": 120 if n == 50 else 80 + n % 7, "tempf_min": 60,
                                                       "rain_in": 0.0, "gust_max": 10.0})))
        db.close()

    def tearDown(self):
        if self._old is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = self._old
        from streamlit.runtime.caching import cache_data
        cache_data.clear()

    def test_rankings_follow_the_period(self):
        at = AppTest.from_function(_history_app, default_timeout=30).run()
        at.radio(key="history_view").set_value("Rankings").run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("segmented_control")), 1)
        page = " ".join(m.value for m in at.markdown)
        self.assertIn("120 °F", page)                    # the hot day 50 days ago ranks first over all time
        at.get("segmented_control")[0].set_value("30 days").run()
        self.assertFalse(at.exception)
        page = " ".join(m.value for m in at.markdown)
        self.assertNotIn("120 °F", page)                 # and drops out over the last 30 days
        at.get("segmented_control")[0].set_value("90 days").run()
        self.assertIn("120 °F", " ".join(m.value for m in at.markdown))

    def test_records_and_coverage_take_the_period(self):
        at = AppTest.from_function(_history_app, default_timeout=30).run()
        for view in ("Records", "Coverage"):
            at.radio(key="history_view").set_value(view).run()
            self.assertFalse(at.exception, view)
            at.get("segmented_control")[0].set_value("7 days").run()
            self.assertFalse(at.exception, view)

    def test_compare_has_no_period_control(self):
        at = AppTest.from_function(_history_app, default_timeout=30).run()
        at.radio(key="history_view").set_value("Compare").run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.get("segmented_control")), 0)


if __name__ == "__main__":
    unittest.main()
