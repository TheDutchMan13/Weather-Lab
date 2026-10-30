"""The installer's version comes from config.py at build time (0.37.38): a hardcoded version in installer.iss
made the Release build look for the wrong file name."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class InstallerVersion(unittest.TestCase):
    def test_build_passes_the_app_version_to_inno_setup(self):
        src = (ROOT / "weatherlab" / "build_installer.py").read_text(encoding="utf-8")
        self.assertIn('f"/DAppVersion={version}"', src)

    def test_installer_script_only_falls_back_when_no_version_is_passed(self):
        iss = (ROOT / "installer.iss").read_text(encoding="utf-8")
        self.assertIn("#ifndef AppVersion", iss)
        self.assertIn("#define AppVersion", iss)


if __name__ == "__main__":
    unittest.main()
