import unittest
from unittest import mock

from weatherlab import keepalive


class KeepaliveTests(unittest.TestCase):
    def test_beat_line_counts_collectors_and_shows_api(self):
        line = keepalive.format_beat(0, ["MainThread", "weatherlab-poller-main", "weatherlab-heartbeat"], "Running on port 8600.")
        self.assertIn("threads=3", line)
        self.assertIn("collectors=1", line)
        self.assertTrue(line.startswith("heartbeat "))
        self.assertTrue(line.endswith("api=Running on port 8600."))

    def test_keep_awake_does_nothing_off_windows(self):
        with mock.patch.object(keepalive.sys, "platform", "linux"):
            self.assertFalse(keepalive.keep_awake())


if __name__ == "__main__":
    unittest.main()
