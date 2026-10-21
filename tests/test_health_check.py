"""The health check: what each fact turns into, and how ages read."""

import unittest

from weatherlab import health_check

NOW = 1_000_000.0
GOOD = {"poller_alive": True, "latest_reading_ts": NOW - 60, "last_poll_ok": NOW - 30, "db_exists": True,
        "db_bytes": 5 * 1024 ** 2, "disk_free_bytes": 50 * 1024 ** 3, "backup_enabled": True,
        "backup_newest_ts": NOW - 3600, "settings_writable": True, "notifications_ok": True,
        "airnow_key": True}


def by_name(checks):
    return {c["name"]: c for c in checks}


class AgeTests(unittest.TestCase):
    def test_age_words(self):
        self.assertEqual(health_check.age_text(30), "just now")
        self.assertEqual(health_check.age_text(12 * 60), "12 min ago")
        self.assertEqual(health_check.age_text(3 * 3600), "3 h ago")
        self.assertEqual(health_check.age_text(3 * 86400), "3 days ago")


class EvaluateTests(unittest.TestCase):
    def test_healthy_app_has_no_problems(self):
        checks = health_check.evaluate(GOOD, NOW)
        self.assertEqual(health_check.summary(checks), "Everything is working.")

    def test_stopped_collector_is_a_problem(self):
        facts = dict(GOOD, poller_alive=False)
        self.assertEqual(by_name(health_check.evaluate(facts, NOW))["Background collector"]["state"], "fail")

    def test_station_readings_age(self):
        late = dict(GOOD, latest_reading_ts=NOW - 1200)
        silent = dict(GOOD, latest_reading_ts=NOW - 7200)
        self.assertEqual(by_name(health_check.evaluate(late, NOW))["Station readings"]["state"], "warn")
        self.assertEqual(by_name(health_check.evaluate(silent, NOW))["Station readings"]["state"], "fail")

    def test_disk_space_levels(self):
        low = dict(GOOD, disk_free_bytes=100 * 1024 ** 2)
        mid = dict(GOOD, disk_free_bytes=500 * 1024 ** 2)
        self.assertEqual(by_name(health_check.evaluate(low, NOW))["Disk space"]["state"], "fail")
        self.assertEqual(by_name(health_check.evaluate(mid, NOW))["Disk space"]["state"], "warn")

    def test_old_or_failed_backup(self):
        old = dict(GOOD, backup_newest_ts=NOW - 3 * 86400)
        failed = dict(GOOD, backup_error="disk full")
        self.assertEqual(by_name(health_check.evaluate(old, NOW))["Backups"]["state"], "warn")
        self.assertEqual(by_name(health_check.evaluate(failed, NOW))["Backups"]["state"], "fail")

    def test_second_folder_only_checked_when_set(self):
        self.assertNotIn("Second backup folder", by_name(health_check.evaluate(GOOD, NOW)))
        unplugged = dict(GOOD, copy_folder="E:\\Backups", copy_folder_ok=False)
        self.assertEqual(by_name(health_check.evaluate(unplugged, NOW))["Second backup folder"]["state"], "warn")

    def test_summary_counts_problems(self):
        facts = dict(GOOD, poller_alive=False, notifications_ok=False)
        self.assertEqual(health_check.summary(health_check.evaluate(facts, NOW)), "2 to check.")


if __name__ == "__main__":
    unittest.main()
