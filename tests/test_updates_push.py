"""One-click updates (checksum and manifest handling), phone alerts (request building), and Tailscale addresses."""

import hashlib
import tempfile
import unittest
from pathlib import Path

from weatherlab import network, push, updates

INSTALLER = b"installer bytes for the test"


class UpdateTests(unittest.TestCase):
    def test_plain_version_line(self):
        info = updates.info_from_text("0.11.0\n", "https://example.com/version.txt", "0.10.0")
        self.assertEqual(info["version"], "0.11.0")
        self.assertEqual(info["file"], "")

    def test_same_or_older_version_is_none(self):
        self.assertIsNone(updates.info_from_text("0.10.0", "https://example.com/v.txt", "0.10.0"))
        self.assertIsNone(updates.info_from_text("0.9.0", "https://example.com/v.txt", "0.10.0"))

    def test_manifest_resolves_the_installer_beside_it(self):
        text = '{"version": "0.11.0", "file": "WeatherLabSetup-0.11.0.exe", "sha256": "%s"}' % ("a" * 64)
        info = updates.info_from_text(text, "https://example.com/releases/latest.json", "0.10.0")
        self.assertEqual(info["installer_url"], "https://example.com/releases/WeatherLabSetup-0.11.0.exe")
        self.assertEqual(info["sha256"], "a" * 64)

    def test_manifest_without_a_valid_checksum_names_no_installer(self):
        text = '{"version": "0.11.0", "file": "WeatherLabSetup-0.11.0.exe", "sha256": "short"}'
        info = updates.info_from_text(text, "https://example.com/latest.json", "0.10.0")
        self.assertEqual(info["file"], "")

    def test_broken_manifest_raises(self):
        with self.assertRaises(ValueError):
            updates.info_from_text("{not json", "https://example.com/latest.json", "0.10.0")

    def test_install_options_close_and_restart_the_app(self):
        self.assertIn("/CLOSEAPPLICATIONS", updates.INSTALL_ARGS)
        self.assertIn("/RESTARTAPPLICATIONS", updates.INSTALL_ARGS)

    def test_download_keeps_only_a_matching_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "WeatherLabSetup-0.11.0.exe"
            source.write_bytes(INSTALLER)
            good = {"version": "0.11.0", "file": source.name, "sha256": hashlib.sha256(INSTALLER).hexdigest(),
                    "installer_url": source.as_uri()}
            target = updates.download(good, Path(tmp) / "updates")
            self.assertEqual(target.read_bytes(), INSTALLER)

            bad = dict(good, sha256="0" * 64, file="Other.exe")
            with self.assertRaises(ValueError):
                updates.download(bad, Path(tmp) / "updates")
            self.assertFalse((Path(tmp) / "updates" / "Other.exe").exists())


class PushTests(unittest.TestCase):
    def test_request_is_built_for_the_topic(self):
        url, headers, body = push.request_for("https://ntfy.example/", "weatherlab-abc", "Weather Lab", "Hot: 43°C")
        self.assertEqual(url, "https://ntfy.example/weatherlab-abc")
        self.assertEqual(headers["Title"], "Weather Lab")
        self.assertEqual(body, "Hot: 43°C".encode("utf-8"))

    def test_default_server(self):
        url, _, _ = push.request_for("", "weatherlab-abc", "Weather Lab", "x")
        self.assertEqual(url, "https://ntfy.sh/weatherlab-abc")

    def test_new_topic_is_long_and_prefixed(self):
        topic = push.new_topic()
        self.assertTrue(topic.startswith("weatherlab-"))
        self.assertGreaterEqual(len(topic), 30)
        self.assertNotEqual(topic, push.new_topic())

    def test_no_topic_sends_nothing(self):
        self.assertFalse(push.send("", "", "Weather Lab", "x"))


class TailscaleTests(unittest.TestCase):
    def test_only_addresses_in_the_tailscale_range_are_kept(self):
        text = "IPv4 100.101.102.103\n192.168.1.5 100.128.0.1 100.64.0.7 100.101.102.103"
        self.assertEqual(network.tailscale_addresses(text), ["100.101.102.103", "100.64.0.7"])


if __name__ == "__main__":
    unittest.main()
