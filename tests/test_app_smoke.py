"""Starts the whole app headlessly with Streamlit's AppTest and checks the first page draws without an error.
Skipped where Streamlit isn't installed, and unless WEATHERLAB_APP_SMOKE=1, which the Tests workflow sets. The
Release build does not set it, so this check can never block a release. Uses an empty data folder, so it is the first-run experience that is checked."""
import os
import tempfile
import unittest
from pathlib import Path

try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None

APP = Path(__file__).resolve().parent.parent / "app.py"


@unittest.skipIf(AppTest is None, "streamlit is not installed")
@unittest.skipUnless(os.environ.get("WEATHERLAB_APP_SMOKE") == "1", "set WEATHERLAB_APP_SMOKE=1 to run")
class AppSmokeTests(unittest.TestCase):
    def test_first_run_page_draws_without_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("APPDATA")
            os.environ["APPDATA"] = tmp
            try:
                at = AppTest.from_file(str(APP), default_timeout=60).run()
            finally:
                if old is None:
                    os.environ.pop("APPDATA", None)
                else:
                    os.environ["APPDATA"] = old
            self.assertEqual([e.value for e in at.exception], [])


if __name__ == "__main__":
    unittest.main()
