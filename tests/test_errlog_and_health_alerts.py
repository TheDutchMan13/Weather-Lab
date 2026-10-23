"""The error log, its Health check line, and the phone alerts for disk and backup problems."""
import tempfile
import unittest

from weatherlab import errlog, health_check

NOW = 1_800_000_000.0
MB = 1024 * 1024


class ErrlogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_logs_and_reads_newest_first(self):
        errlog.log("a", ValueError("one"), self.tmp.name, now=NOW - 100)
        errlog.log("b", KeyError("two"), self.tmp.name, now=NOW - 10)
        rows = errlog.recent(NOW - 200, self.tmp.name)
        self.assertEqual([r[1] for r in rows], ["b", "a"])
        self.assertIn("ValueError: one", rows[1][2])

    def test_old_lines_are_left_out(self):
        errlog.log("a", ValueError("old"), self.tmp.name, now=NOW - 90000)
        self.assertEqual(errlog.recent(NOW - 86400, self.tmp.name), [])

    def test_missing_file_is_empty(self):
        self.assertEqual(errlog.recent(0, self.tmp.name), [])

    def test_newlines_stay_on_one_line(self):
        errlog.log("a", ValueError("x\ny"), self.tmp.name, now=NOW)
        self.assertEqual(len(errlog.recent(0, self.tmp.name)), 1)

    def test_big_file_is_trimmed(self):
        for i in range(600):
            errlog.log("a", ValueError("z" * 250), self.tmp.name, now=NOW + i)
        rows = errlog.recent(0, self.tmp.name)
        self.assertLess(len(rows), 600)
        self.assertEqual(rows[0][0], NOW + 599)

    def test_logging_never_raises(self):
        errlog.log("a", ValueError("x"), "/proc/definitely/not/writable")


class HealthTests(unittest.TestCase):
    def check(self, facts, name):
        return next(c for c in health_check.evaluate(facts, NOW) if c["name"] == name)

    def test_recent_errors_none(self):
        self.assertEqual(self.check({"recent_errors": []}, "Recent errors")["state"], "ok")

    def test_recent_errors_warns(self):
        c = self.check({"recent_errors": [(NOW - 60, "background collector", "OSError: disk")]}, "Recent errors")
        self.assertEqual(c["state"], "warn")
        self.assertIn("OSError: disk", c["detail"])

    def test_no_fact_no_check(self):
        names = [c["name"] for c in health_check.evaluate({}, NOW)]
        self.assertNotIn("Recent errors", names)

    def test_alert_sent_once_until_it_clears(self):
        bad = health_check.evaluate({"disk_free_bytes": 10 * MB}, NOW)
        msgs, failing = health_check.alert_messages(bad, set())
        self.assertEqual(len(msgs), 1)
        self.assertIn("Disk space", msgs[0])
        self.assertEqual(health_check.alert_messages(bad, failing)[0], [])
        good = health_check.evaluate({"disk_free_bytes": 50 * 1024 * MB}, NOW)
        msgs, failing = health_check.alert_messages(good, failing)
        self.assertEqual((msgs, failing), ([], set()))
        self.assertEqual(len(health_check.alert_messages(bad, failing)[0]), 1)

    def test_backup_failure_alerts(self):
        checks = health_check.evaluate({"backup_enabled": True, "backup_error": "no space"}, NOW)
        msgs, _ = health_check.alert_messages(checks, set())
        self.assertTrue(any("Backups" in m for m in msgs))

    def test_other_failures_do_not_alert(self):
        checks = health_check.evaluate({"poller_alive": False}, NOW)
        self.assertEqual(health_check.alert_messages(checks, set())[0], [])


if __name__ == "__main__":
    unittest.main()
