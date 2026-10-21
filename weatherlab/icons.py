"""Makes the app icons for the phone home screen. Writes plain PNG files with no extra libraries."""

import struct
import zlib
from pathlib import Path

BACKGROUND = (11, 61, 145)
SUN = (255, 209, 102)


def write_png(path: Path, size: int) -> None:
    """A square icon: a sun on a blue background."""
    centre, radius = size / 2, size * 0.26
    rows = []
    for y in range(size):
        row = bytearray(b"\x00")
        for x in range(size):
            inside = (x + 0.5 - centre) ** 2 + (y + 0.5 - centre) ** 2 <= radius ** 2
            row += bytes(SUN if inside else BACKGROUND)
        rows.append(bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
                     + chunk(b"IDAT", zlib.compress(b"".join(rows))) + chunk(b"IEND", b""))


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "static"
    out.mkdir(exist_ok=True)
    for name, size in [("icon-192.png", 192), ("icon-512.png", 512), ("apple-touch-icon.png", 180)]:
        write_png(out / name, size)
        print("wrote", out / name)
