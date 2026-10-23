"""autostart, autofit and wx_icons: small modules that had no tests."""
import sys
import types
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


class AutofitTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.fake = types.SimpleNamespace(html=lambda body, *a, **k: self.calls.append(body))
        st = types.ModuleType("streamlit")
        comps = types.ModuleType("streamlit.components")
        v1 = types.ModuleType("streamlit.components.v1")
        v1.html = self.fake.html
        st.components = comps
        comps.v1 = v1
        patcher = mock.patch.dict(sys.modules, {"streamlit": st, "streamlit.components": comps,
                                                "streamlit.components.v1": v1})
        patcher.start()
        self.addCleanup(patcher.stop)
        sys.modules.pop("weatherlab.autofit", None)
        self.addCleanup(sys.modules.pop, "weatherlab.autofit", None)
        from weatherlab import autofit
        self.autofit, self.v1 = autofit, v1

    def test_adds_script_once_even_when_installed_twice(self):
        self.autofit.install()
        self.autofit.install()
        self.v1.html("<p>hi</p>")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.calls[0].count("<script>"), 1)
        self.assertTrue(self.calls[0].startswith("<p>hi</p>"))


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
