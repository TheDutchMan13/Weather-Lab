"""The icon writer makes a valid PNG of the requested size."""

import struct
import tempfile
import unittest
from pathlib import Path

from weatherlab import icons


class IconTests(unittest.TestCase):
    def test_png_signature_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "icon.png"
            icons.write_png(path, 16)
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(struct.unpack(">II", data[16:24]), (16, 16))


if __name__ == "__main__":
    unittest.main()
