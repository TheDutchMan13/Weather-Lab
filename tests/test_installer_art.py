"""The installer's artwork: the files exist, have the sizes Inno Setup expects, and the script uses them."""

import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "assets" / "installer"


class InstallerArtTests(unittest.TestCase):
    def test_side_panel_is_164_by_314_bmp(self):
        img = Image.open(ART / "wizard-large.bmp")
        self.assertEqual((img.format, img.size), ("BMP", (164, 314)))

    def test_corner_image_is_55_by_58_bmp(self):
        img = Image.open(ART / "wizard-small.bmp")
        self.assertEqual((img.format, img.size), ("BMP", (55, 58)))

    def test_setup_icon_has_the_standard_sizes(self):
        img = Image.open(ART / "weatherlab.ico")
        self.assertEqual(img.format, "ICO")
        self.assertTrue({(16, 16), (32, 32), (48, 48), (256, 256)} <= set(img.info["sizes"]))

    def test_script_points_at_the_artwork(self):
        script = (ROOT / "installer.iss").read_text(encoding="utf-8")
        for name in ("weatherlab.ico", "wizard-large.bmp", "wizard-small.bmp"):
            self.assertIn(f"assets\\installer\\{name}", script)
            self.assertTrue((ART / name).exists())


if __name__ == "__main__":
    unittest.main()
