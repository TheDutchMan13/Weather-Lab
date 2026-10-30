"""autostart and wx_icons: small modules that had no tests."""
import sys
import unittest
from unittest import mock

from weatherlab import autostart, wx_icons


class AutostartTests(unittest.TestCase):
    def test_not_supported_from_source(self):
        with mock.patch.object(sys, "frozen", False, create=True):
            self.assertFalse(autostart.supported())
            self.assertFalse(autostart.is_enabled())
            with self.assertRaises(RuntimeError):
                autostart.set_enabled(True)

    def test_enable_writes_the_exe_path_and_disable_removes_it(self):
        reg = mock.MagicMock()
        reg.OpenKey.return_value.__enter__.return_value = "key"
        reg.REG_SZ = 1
        with mock.patch.object(autostart, "supported", return_value=True), \
                mock.patch.dict(sys.modules, {"winreg": reg}):
            autostart.set_enabled(True)
            args = reg.SetValueEx.call_args[0]
            self.assertEqual(args[0:3], ("key", "WeatherLab", 0))
            self.assertTrue(args[4].startswith(chr(34)) and args[4].endswith(chr(34)))
            autostart.set_enabled(False)
            reg.DeleteValue.assert_called_once_with("key", "WeatherLab")

    def test_disable_when_missing_is_quiet(self):
        reg = mock.MagicMock()
        reg.DeleteValue.side_effect = FileNotFoundError
        with mock.patch.object(autostart, "supported", return_value=True), \
                mock.patch.dict(sys.modules, {"winreg": reg}):
            autostart.set_enabled(False)


class IconTests(unittest.TestCase):
    def test_unknown_kind_falls_back_to_a_sun(self):
        self.assertIn("<svg", wx_icons.now_icon("clear_day"))
        self.assertIn("<svg", wx_icons.now_icon("not_a_kind"))

    def test_forecast_words_pick_an_icon(self):
        rain = wx_icons.forecast_icon("Showers Likely")
        sun = wx_icons.forecast_icon("Sunny")
        self.assertNotEqual(rain, sun)
        self.assertNotEqual(wx_icons.forecast_icon("Clear", night=True), wx_icons.forecast_icon("Clear"))

    def test_empty_text_still_draws(self):
        self.assertIn("<svg", wx_icons.forecast_icon(None))


if __name__ == "__main__":
    unittest.main()
