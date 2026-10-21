"""Weather Underground upload: the query values and how errors are reported."""

import unittest
import urllib.error
from datetime import datetime, timezone
from unittest import mock

from weatherlab import wunderground

NOW = datetime(2026, 10, 21, 22, 5, 9, tzinfo=timezone.utc)
READING = {"tempf": 81.46, "dewpointf": 55.0, "humidity": 40, "windspeedmph": 5.2, "windgustmph": 9.0,
           "winddir": 180, "baromrelin": 29.912, "dailyrainin": 0.0, "solarradiation": 812.4, "uv": 6}


def fake_response(body: bytes):
    cm = mock.MagicMock()
    cm.__enter__.return_value.read.return_value = body
    return cm


class ValuesTests(unittest.TestCase):
    def test_maps_fields_and_formats_the_time_in_utc(self):
        v = wunderground.values("KAZTEST1", "secret", READING, NOW)
        self.assertEqual(v["ID"], "KAZTEST1")
        self.assertEqual(v["PASSWORD"], "secret")
        self.assertEqual(v["action"], "updateraw")
        self.assertEqual(v["dateutc"], "2026-10-21 22:05:09")
        self.assertEqual(v["tempf"], "81.46")
        self.assertEqual(v["dewptf"], "55")
        self.assertEqual(v["baromin"], "29.91")
        self.assertEqual(v["UV"], "6")
        self.assertEqual(v["winddir"], "180")

    def test_fields_the_station_did_not_report_are_left_out(self):
        v = wunderground.values("KAZTEST1", "secret", {"tempf": 70}, NOW)
        self.assertNotIn("humidity", v)
        self.assertNotIn("UV", v)
        self.assertEqual(v["tempf"], "70")

    def test_software_type_names_the_app_version(self):
        v = wunderground.values("KAZTEST1", "secret", READING, NOW)
        self.assertTrue(v["softwaretype"].startswith("WeatherLab "))


class SendTests(unittest.TestCase):
    def test_success_reply_is_accepted(self):
        with mock.patch("weatherlab.wunderground.urllib.request.urlopen", return_value=fake_response(b"success")) as opened:
            wunderground.send_reading("KAZTEST1", "secret", READING, NOW)
        self.assertEqual(opened.call_count, 1)
        self.assertIn("PASSWORD=secret", opened.call_args.args[0].full_url)

    def test_rejected_upload_is_reported_without_the_key(self):
        with mock.patch("weatherlab.wunderground.urllib.request.urlopen", return_value=fake_response(b"INVALID PASSWORD")):
            with self.assertRaises(wunderground.WuError) as ctx:
                wunderground.send_reading("KAZTEST1", "secret", READING, NOW)
        self.assertIn("INVALID PASSWORD", str(ctx.exception))
        self.assertNotIn("secret", str(ctx.exception))

    def test_http_error_is_reported_without_the_url(self):
        error = urllib.error.HTTPError("https://example/?PASSWORD=secret", 500, "boom", {}, None)
        with mock.patch("weatherlab.wunderground.urllib.request.urlopen", side_effect=error):
            with self.assertRaises(wunderground.WuError) as ctx:
                wunderground.send_reading("KAZTEST1", "secret", READING, NOW)
        self.assertIn("500", str(ctx.exception))
        self.assertNotIn("secret", str(ctx.exception))

    def test_no_network_is_reported(self):
        with mock.patch("weatherlab.wunderground.urllib.request.urlopen", side_effect=OSError("offline")):
            with self.assertRaisesRegex(wunderground.WuError, "Couldn't reach Weather Underground"):
                wunderground.send_reading("KAZTEST1", "secret", READING, NOW)

    def test_missing_station_or_key_is_an_error_before_any_request(self):
        with mock.patch("weatherlab.wunderground.urllib.request.urlopen") as opened:
            with self.assertRaises(wunderground.WuError):
                wunderground.send_reading("", "secret", READING, NOW)
            with self.assertRaises(wunderground.WuError):
                wunderground.send_reading("KAZTEST1", "  ", READING, NOW)
        opened.assert_not_called()


if __name__ == "__main__":
    unittest.main()
