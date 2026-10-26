"""The shareable year card: a picture of one year's best numbers, saved as a PNG."""

import io
from datetime import date

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1080, 1350
BACKGROUND, PANEL, TEXT, MUTED, ACCENT = "#0b3d91", "#13508f", "#ffffff", "#b9d2f2", "#ffd166"
FONT_FILES = [  # first that exists: Windows, then Linux fallbacks
    ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
]


def _font(size: int, bold: bool = False):
    for regular, heavy in FONT_FILES:
        try:
            return ImageFont.truetype(heavy if bold else regular, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}"


def facts(card: dict) -> list:
    """[(label, value, note)] for the card, skipping anything the year doesn't have."""
    t, r, w = card.get("temp_unit", ""), card.get("rain_unit", ""), card.get("wind_unit", "")
    out = []
    if card.get("hottest"):
        out.append(("Hottest day", f"{card['hottest']['value']:g}{t}", _day(card["hottest"]["date"])))
    hot = "38°C" if t == "°C" else "100°F"
    out.append((f"Days at {hot} or more", str(card.get("days_100", 0)), ""))
    if card.get("longest_hot"):
        h = card["longest_hot"]
        out.append(("Longest hot streak", f"{h['days']} days", f"{_day(h['from'])} to {_day(h['to'])}"))
    if card.get("wettest"):
        out.append(("Wettest day", f"{card['wettest']['value']:g} {r}", _day(card["wettest"]["date"])))
    if card.get("rain") is not None:
        out.append(("Rain this year", f"{card['rain']:g} {r}", f"{card.get('rainy_days', 0)} rainy days"))
    if card.get("windiest"):
        out.append(("Highest gust", f"{card['windiest']['value']:g} {w}", _day(card["windiest"]["date"])))
    return out


def render(card: dict, station_name: str = "") -> bytes:
    """PNG bytes for a year_card dict (as api_pages.year_card returns it)."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    d = ImageDraw.Draw(img)
    d.text((72, 70), "MY WEATHER YEAR", font=_font(34, True), fill=MUTED)
    d.text((72, 120), str(card["year"]), font=_font(190, True), fill=TEXT)
    if station_name:
        d.text((72, 335), station_name, font=_font(34), fill=MUTED)
    rows = facts(card)
    top, gap = 410, 14
    height = (HEIGHT - 150 - top - gap * 5) // 6
    for i, (label, value, note) in enumerate(rows[:6]):
        y = top + i * (height + gap)
        d.rounded_rectangle((72, y, WIDTH - 72, y + height), radius=26, fill=PANEL)
        d.text((108, y + 10), label, font=_font(30), fill=MUTED)
        d.text((108, y + 52), value, font=_font(54, True), fill=ACCENT if i == 0 else TEXT)
        if note:
            d.text((WIDTH - 108, y + 64), note, font=_font(30), fill=MUTED, anchor="ra")
    d.text((72, HEIGHT - 90), "Made with Weather Lab", font=_font(30), fill=MUTED)
    out = io.BytesIO()
    img.save(out, "PNG")
    return out.getvalue()
