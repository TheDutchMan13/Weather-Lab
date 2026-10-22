"""Make the installer's artwork from assets/logo.jpg.

Writes assets/installer/weatherlab.ico (the installer's own icon), wizard-large.bmp (the 164 x 314 side panel)
and wizard-small.bmp (the 55 x 58 corner image). Run it again after the logo changes:

    python tools/make_installer_art.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "logo.jpg"
OUT = ROOT / "assets" / "installer"
CENTER = (705, 385)  # the middle of the badge in logo.jpg (1408 x 768)
RADIUS = 280  # half the badge's width in logo.jpg


def round_badge(size: int) -> Image.Image:
    """The badge cut out of its background as a circle with transparent corners, at the given size."""
    img = Image.open(SOURCE).convert("RGB")
    cx, cy = CENTER
    badge = img.crop((cx - RADIUS, cy - RADIUS, cx + RADIUS, cy + RADIUS)).resize((size, size), Image.LANCZOS)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    badge = badge.convert("RGBA")
    badge.putalpha(mask)
    return badge


def on_white(width: int, height: int, logo: Image.Image, x: int, y: int) -> Image.Image:
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    canvas.paste(logo, (x, y), logo)
    return canvas


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    round_badge(256).save(OUT / "weatherlab.ico", format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (256, 256)])
    on_white(164, 314, round_badge(150), 7, 82).save(OUT / "wizard-large.bmp", format="BMP")
    on_white(55, 58, round_badge(50), 2, 4).save(OUT / "wizard-small.bmp", format="BMP")
    print(f"Wrote the installer artwork to {OUT}")


if __name__ == "__main__":
    main()
