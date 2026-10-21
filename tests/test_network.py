"""Home-network access tests. No network traffic: only local checks."""

import os
import unittest
from unittest import mock

from weatherlab import network
from weatherlab.settings import Settings


class NetworkTests(unittest.TestCase):
    def test_off_by_default(self):
        self.assertFalse(Settings().allow_network)

    def test_app_port_defaults_to_8501(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WEATHERLAB_PORT", None)
            self.assertEqual(network.app_port(), 8501)

    def test_app_port_reads_launcher_value(self):
        with mock.patch.dict(os.environ, {"WEATHERLAB_PORT": "9123"}):
            self.assertEqual(network.app_port(), 9123)

    def test_lan_address_is_a_string(self):
        self.assertIsInstance(network.lan_address(), str)
        self.assertTrue(network.lan_address())


if __name__ == "__main__":
    unittest.main()
