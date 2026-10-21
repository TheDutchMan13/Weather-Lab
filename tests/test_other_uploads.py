"""PWSweather and Weathercloud uploads: formats, conversions and how replies are read."""

import unittest
import urllib.error
from datetime import datetime, timezone
from unittest import mock

from weatherlab import pwsweather, uploads, weathercloud

NOW = datetime(2026, 10, 21, 22, 5, 9, tzinfo=timezone.utc)
READING = {"tempf": 70.0, "dewpointf": 50.0, "humidity": 40, "windspeedmph": 10.0, "windgustmph": 15.0,
           "winddir": 180, "baromrelin": 29.92, "dailyrainin": 0.5, "rainratein": 0.1,
           "solarradiation": 500.0, "uv": 3}


def reply(body: bytes):
    cm = mock.MagicMock()
    cm.__enter__.return_value.read.return_value = body
    return cm


class WeathercloudValuesTests(unittest.TestCase):
    def test_metric_values_times_ten(self):
        v = weathercloud.values("1234", "k", READING, NOW)
        self.assertEqual(v["temp"], "211")       # 70 F is 21.1 C
        self.assertEqual(v["dew"], "100")        # 50 F is 10.0 C
        self.assertEqual(v["wspd"], "45")        # 10 mph is 4.47 m/s
        self.assertEqual(v["wspdhi"], "67")      # 15 mph is 6.71 m/s
        self.assertEqual(v["bar"], "10132")      # 29.92 inHg is 1013.2 hPa
        self.assertEqual(v["rain"], "127")       # 0.5 in is 12.7 mm
        self.assertEqual(v["rainrate"], "25")    # 0.1 in is 2.5 mm
        self.assertEqual(v["solarrad"], "5000")
        self.assertEqual(v["uvi"], "30")

    def test_time_and_fixed_fields(self):
        v = weathercloud.values("1234", "k", READING, NOW)
        self.assertEqual(v["time"], "20261021 220509")
        self.assertEqual(v["type"], "481")
        self.assertEqual(v["wid"], "1234")
        self.assertEqual(v["key"], "k")

    def test_missing_fields_are_left_out(self):
        v = weathercloud.values("1234", "k", {"tempf": 32}, NOW)
        self.assertEqual(v["temp"], "0")
        self.assertNotIn("bar", v)
        self.assertNotIn("uvi", v)


class WeathercloudSendTests(unittest.TestCase):
    def test_200_is_accepted(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", return_value=reply(b"200")):
            weathercloud.send_reading("1234", "k", READING, NOW)

    def test_other_reply_is_reported(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", return_value=reply(b"401")):
            with self.assertRaisesRegex(uploads.UploadError, "401"):
                weathercloud.send_reading("1234", "k", READING, NOW)

    def test_missing_id_or_key_stops_before_the_request(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen") as opened:
            with self.assertRaises(uploads.UploadError):
                weathercloud.send_reading("", "k", READING, NOW)
        opened.assert_not_called()


class PwsweatherSendTests(unittest.TestCase):
    def test_empty_reply_is_accepted(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", return_value=reply(b"")):
            pwsweather.send_reading("ABC", "secret", READING, NOW)

    def test_success_reply_is_accepted(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", return_value=reply(b"success")):
            pwsweather.send_reading("ABC", "secret", READING, NOW)

    def test_rejection_is_reported_without_the_key(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", return_value=reply(b"INVALID PASSWORD")):
            with self.assertRaises(uploads.UploadError) as ctx:
                pwsweather.send_reading("ABC", "secret", READING, NOW)
        self.assertIn("INVALID PASSWORD", str(ctx.exception))
        self.assertNotIn("secret", str(ctx.exception))

    def test_uses_the_weather_underground_format(self):
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", return_value=reply(b"")) as opened:
            pwsweather.send_reading("ABC", "secret", READING, NOW)
        url = opened.call_args.args[0].full_url
        self.assertTrue(url.startswith(pwsweather.URL + "?"))
        self.assertIn("action=updateraw", url)
        self.assertIn("dateutc=2026-10-21+22%3A05%3A09", url)

    def test_network_error_is_reported_by_name(self):
        error = urllib.error.HTTPError("https://x/?PASSWORD=secret", 503, "busy", {}, None)
        with mock.patch("weatherlab.uploads.urllib.request.urlopen", side_effect=error):
            with self.assertRaisesRegex(uploads.UploadError, "PWSweather returned an error \\(503\\)"):
                pwsweather.send_reading("ABC", "secret", READING, NOW)


if __name__ == "__main__":
    unittest.main()
