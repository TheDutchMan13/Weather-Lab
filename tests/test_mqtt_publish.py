"""MQTT publishing: topics, Home Assistant discovery, the packets, and a round trip to a fake broker."""

import json
import socket
import threading
import unittest

from weatherlab import mqtt_publish, uploads

READING = {"tempf": 84.2, "humidity": 31, "windspeedmph": 7, "windgustmph": 12, "winddir": 225,
           "dailyrainin": 0.0, "baromrelin": 29.94, "uv": 6, "solarradiation": 612}


def read_packet(conn) -> tuple[int, bytes]:
    """Read one MQTT packet from a socket: its first byte and its body."""
    first = conn.recv(1)[0]
    length, shift = 0, 0
    while True:
        byte = conn.recv(1)[0]
        length += (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            break
    body = b""
    while len(body) < length:
        body += conn.recv(length - len(body))
    return first, body


def fake_broker(reply_code: int, received: list):
    """A one-connection broker on localhost. Records every packet after CONNECT, and answers CONNACK."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)

    def run():
        conn, _ = server.accept()
        with conn:
            first, body = read_packet(conn)
            received.append((first, body))
            conn.sendall(bytes([0x20, 0x02, 0x00, reply_code]))
            if reply_code == 0:
                while True:
                    try:
                        first, body = read_packet(conn)
                    except IndexError:
                        break
                    received.append((first, body))
                    if first == 0xE0:
                        break
        server.close()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return server.getsockname()[1], thread


class TopicTests(unittest.TestCase):
    def test_readings_become_topics_with_plain_values(self):
        pairs = dict(mqtt_publish.readings("weatherlab/home", READING))
        self.assertEqual(pairs["weatherlab/home/temperature"], "84.2")
        self.assertEqual(pairs["weatherlab/home/wind/direction"], "225")
        self.assertEqual(pairs["weatherlab/home/pressure"], "29.94")
        self.assertEqual(pairs["weatherlab/home/status/online"], "true")

    def test_missing_readings_are_skipped(self):
        pairs = dict(mqtt_publish.readings("p", {"tempf": 70}))
        self.assertEqual(set(pairs), {"p/temperature", "p/status/online"})

    def test_prefix_is_trimmed_and_checked(self):
        self.assertEqual(mqtt_publish.check_prefix(" /weatherlab/home/ "), "weatherlab/home")
        for bad in ("", "/", "a/+/b", "a/#", "a//b"):
            with self.assertRaises(uploads.UploadError, msg=bad):
                mqtt_publish.check_prefix(bad)


class DiscoveryTests(unittest.TestCase):
    def test_one_retained_config_per_sensor_points_at_the_state_topic(self):
        configs = mqtt_publish.discovery("weatherlab/home")
        self.assertEqual(len(configs), len(mqtt_publish.SENSORS))
        state_topics = {topic for topic, _ in mqtt_publish.readings("weatherlab/home", READING)}
        for topic, payload in configs:
            self.assertTrue(topic.startswith("homeassistant/sensor/weatherlab/"))
            self.assertTrue(topic.endswith("/config"))
            config = json.loads(payload)
            self.assertIn(config["state_topic"], state_topics)
            self.assertEqual(config["device"]["identifiers"], ["weatherlab"])
            self.assertEqual(config["state_class"], "measurement")

    def test_temperature_has_its_device_class(self):
        temp = next(json.loads(p) for t, p in mqtt_publish.discovery("x") if t.endswith("weatherlab_temperature/config"))
        self.assertEqual(temp["device_class"], "temperature")
        self.assertEqual(temp["unit_of_measurement"], "°F")


class PacketTests(unittest.TestCase):
    def test_remaining_length_uses_more_bytes_for_larger_bodies(self):
        self.assertEqual(mqtt_publish._remaining_length(5), b"\x05")
        self.assertEqual(mqtt_publish._remaining_length(128), b"\x80\x01")
        self.assertEqual(mqtt_publish._remaining_length(16383), b"\xff\x7f")

    def test_connect_flags_for_user_and_password(self):
        packet = mqtt_publish.connect_packet("cid", "user", "pw")
        self.assertEqual(packet[0], 0x10)
        self.assertIn(bytes([4, 0xC2]), packet)  # level 4, username, password, clean session

    def test_password_is_ignored_without_a_user(self):
        packet = mqtt_publish.connect_packet("cid", "", "pw")
        self.assertIn(bytes([4, 0x02]), packet)

    def test_publish_sets_the_retain_flag(self):
        self.assertEqual(mqtt_publish.publish_packet("a/b", "1")[0], 0x31)
        self.assertEqual(mqtt_publish.publish_packet("a/b", "1", retain=False)[0], 0x30)


class SendTests(unittest.TestCase):
    def test_messages_reach_a_broker_with_the_right_login(self):
        received = []
        port, thread = fake_broker(0, received)
        messages = mqtt_publish.readings("weatherlab/home", READING)
        mqtt_publish.send("127.0.0.1", port, "hans", "pw", messages, client_id="weatherlab-main")
        thread.join(5)
        connect_type, connect = received[0]
        self.assertEqual(connect_type, 0x10)
        self.assertIn(b"weatherlab-main", connect)
        self.assertIn(b"hans", connect)
        published = [(t, b) for t, b in received[1:] if t & 0xF0 == 0x30]
        self.assertEqual(len(published), len(messages))
        self.assertTrue(any(b"weatherlab/home/temperature" + b"84.2" in body for _, body in published))
        self.assertEqual(received[-1][0], 0xE0)

    def test_refused_login_is_reported_without_the_password(self):
        port, thread = fake_broker(5, [])
        with self.assertRaises(uploads.UploadError) as ctx:
            mqtt_publish.send("127.0.0.1", port, "hans", "secret-pw", [("a", "1")])
        thread.join(5)
        self.assertIn("isn't allowed", str(ctx.exception))
        self.assertNotIn("secret-pw", str(ctx.exception))

    def test_unreachable_broker_is_reported(self):
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()
        with self.assertRaisesRegex(uploads.UploadError, "Couldn't reach the MQTT broker"):
            mqtt_publish.send("127.0.0.1", port, "", "", [("a", "1")])

    def test_missing_address_is_an_error(self):
        with self.assertRaisesRegex(uploads.UploadError, "broker address"):
            mqtt_publish.send("  ", 1883, "", "", [])


if __name__ == "__main__":
    unittest.main()
