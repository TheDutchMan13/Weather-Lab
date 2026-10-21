"""The installer build finds the project folder, its version and its build output from the right place."""

import unittest

from weatherlab import build_installer
from weatherlab.config import APP_VERSION


class BuildInstallerPathTests(unittest.TestCase):
    def test_root_is_the_project_folder(self) -> None:
        self.assertTrue((build_installer.ROOT / "app.py").exists())
        self.assertTrue((build_installer.ROOT / "installer.iss").exists())

    def test_version_is_read_from_config(self) -> None:
        self.assertEqual(build_installer.app_version(), APP_VERSION)


if __name__ == "__main__":
    unittest.main()
