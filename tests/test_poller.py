"""Poller failure handling. No network: parse.fetch is replaced with a fake.

Run with:  python -m unittest discover -s tests -v
"""

import unittest
from unittest import mock

from weatherlab import parse
from weatherlab.poller import Poller
from weatherlab.settings import Settings


class FakeDb:
    pass


class PollerTests(unittest.TestCase):
    def test_unreachable_station_is_reported(self):
        p = Poller()
        with mock.patch.object(parse, "fetch", side_effect=OSError("timed out")):
            p._poll_once(FakeDb(), Settings(station_ip="192.168.1.224"))
        self.assertIn("Can't reach the station", p.status.last_error)
        self.assertIsNotNone(p.status.last_attempt)

    def test_run_survives_an_unexpected_error(self):
        p = Poller()
        calls = {"n": 0}

        def flaky_poll(db, ip):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            raise SystemExit  # stop the loop on the second attempt

        with mock.patch.object(Poller, "_poll_once", side_effect=flaky_poll), \
                mock.patch("weatherlab.poller.storage.connect", return_value=FakeDb()), \
                mock.patch("weatherlab.poller.load_settings") as settings, \
                mock.patch("weatherlab.poller.time.sleep"):
            settings.return_value.station_ip = "192.168.1.224"
            settings.return_value.backup_enabled = False  # never copy the real database from a test
            settings.return_value.sensor_alerts = False  # never reach the station or NWS from a test
            settings.return_value.digest_enabled = False
            settings.return_value.latitude = None
            settings.return_value.quiet_enabled = False
            settings.return_value.stuck_alerts = False
            settings.return_value.offline_alerts = False
            settings.return_value.lightning_alerts = False
            with self.assertRaises(SystemExit):
                p.run()
        self.assertEqual(calls["n"], 2)
        self.assertIn("RuntimeError", p.status.last_error)


if __name__ == "__main__":
    unittest.main()
