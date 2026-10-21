"""CWOP tests. No network: the socket is replaced with a fake."""

import unittest
from datetime import datetime, timezone
from unittest import mock

from weatherlab import cwop

READING = {"tempf": 88.4, "humidity": 22, "winddir": 270, "windspeedmph": 5.2, "windgustmph": 9.0,
           "dailyrainin": 0.12, "baromrelin": 29.92}
NOW = datetime(2026, 10, 20, 20, 45, tzinfo=timezone.utc)


class FakeLink:
    def __init__(self, replies):
        self._replies = list(replies)
        self.sent = []

    def readline(self):
        return self._replies.pop(0) if self._replies else b""

    def write(self, data):
        self.sent.append(data)

    def flush(self):
        pass


class FakeSocket:
    def __init__(self, link):
        self.link = link

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def makefile(self, mode):
        return self.link


class CwopTests(unittest.TestCase):
    def test_passcode_known_value(self):
        self.assertEqual(cwop.passcode("N0CALL"), 13023)

    def test_passcode_ignores_ssid(self):
        self.assertEqual(cwop.passcode("N0CALL-13"), cwop.passcode("N0CALL"))

    def test_coordinates(self):
        self.assertEqual(cwop._lat(33.5), "3330.00N")
        self.assertEqual(cwop._lon(-112.25), "11215.00W")

    def test_packet_fields(self):
        p = cwop.weather_packet("cw1234", READING, 33.5, -112.25, NOW)
        self.assertTrue(p.startswith("CW1234>APRS,TCPIP*:@202045z3330.00N/11215.00W_270/005"), p)
        self.assertIn("g009", p)
        self.assertIn("t088", p)
        self.assertIn("P012", p)
        self.assertIn("h22", p)
        self.assertTrue(p.endswith("b10132"), p)

    def test_missing_values_are_dots(self):
        p = cwop.weather_packet("CW1234", {}, 33.5, -112.25, NOW)
        self.assertIn("t...", p)
        self.assertIn("h..", p)

    def test_needs_callsign_and_location(self):
        with self.assertRaises(cwop.CwopError):
            cwop.send_reading("", READING, 33.5, -112.25)
        with self.assertRaises(cwop.CwopError):
            cwop.send_reading("CW1234", READING, None, None)

    def test_rejected_login_sends_nothing_else(self):
        link = FakeLink([b"# aprsc\r\n", b"# logresp CW1234 unverified, server\r\n"])
        with mock.patch.object(cwop.socket, "create_connection", return_value=FakeSocket(link)):
            with self.assertRaises(cwop.CwopError):
                cwop.send_reading("CW1234", READING, 33.5, -112.25, NOW)
        self.assertEqual(len(link.sent), 1)

    def test_verified_login_sends_packet(self):
        link = FakeLink([b"# aprsc\r\n", b"# logresp CW1234 verified, server\r\n"])
        with mock.patch.object(cwop.socket, "create_connection", return_value=FakeSocket(link)):
            packet = cwop.send_reading("CW1234", READING, 33.5, -112.25, NOW)
        self.assertIn(b"pass ", link.sent[0])
        self.assertEqual(link.sent[-1], (packet + "\r\n").encode("ascii"))

    def test_unreachable_network(self):
        with mock.patch.object(cwop.socket, "create_connection", side_effect=OSError("down")):
            with self.assertRaises(cwop.CwopError):
                cwop.send_reading("CW1234", READING, 33.5, -112.25, NOW)


if __name__ == "__main__":
    unittest.main()
