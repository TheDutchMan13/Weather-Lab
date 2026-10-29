"""Two dials for the Home page: the feels-like dial and the pressure trend dial. Ported from the dashboard's
utils/visuals.py (ZONES, feels_like_html) and utils/visuals3.py (PRESSURE_BANDS, pressure_dial_html). Inputs are in °F and inHg; the text
uses the chosen units. Each builder returns (html, height)."""

import html as _h
import math

from weatherlab import units as U

FEELS_LO, FEELS_HI = 60.0, 130.0
FEELS_ZONES = [(85.0, "#60a5fa", "Comfortable", "No special precautions."),
               (95.0, "#fbbf24", "Warm", "Drink water, take shade breaks."),
               (105.0, "#f97316", "Hot", "Limit time in direct sun."),
               (115.0, "#dc2626", "Dangerous", "Heat illness is possible. Avoid strenuous activity outdoors."),
               (130.0, "#7f1d1d", "Extreme", "Stay indoors in cooling if you can.")]
PRESSURE_BANDS = [(-0.10, -0.06, "#ef4444", "Falling fast", "Falling fast. Storms or strong wind are possible."),
                  (-0.06, -0.02, "#f97316", "Falling", "Falling slowly. The weather may be turning."),
                  (-0.02, 0.02, "#34d399", "Steady", "No storm signal from the barometer."),
                  (0.02, 0.06, "#7dd3fc", "Rising", "Rising. Skies are likely clearing or drying."),
                  (0.06, 0.10, "#6366f1", "Rising fast", "Rising fast. Gusty, clearing winds are possible.")]


def _colors(dark: bool) -> dict:
    if dark:
        return dict(text="#eceef1", muted="#9aa1ab")
    return dict(text="#14171c", muted="#5b626d")


def feels_zone(feels_f: float) -> tuple[str, str, str]:
    """(name, tip, colour) for a feels-like temperature in °F."""
    if feels_f < FEELS_LO:
        return "Cool", "Pleasant to chilly.", "#60a5fa"
    for upper, color, name, tip in FEELS_ZONES:
        if feels_f <= upper:
            return name, tip, color
    last = FEELS_ZONES[-1]
    return last[2], last[3], last[1]


def feels_dial_html(feels_f: float, actual_f=None, humidity=None, dark: bool = False,
                    metric: bool = False) -> tuple[str, int]:
    """Semicircle dial coloured by heat zone, with the needle at the feels-like temperature."""
    c = _colors(dark)
    unit = U.unit("tempf", metric)
    v = max(FEELS_LO, min(FEELS_HI, float(feels_f)))
    cx, cy, r_out, r_in = 110, 112, 96, 72

    def ang(t: float) -> float:
        return math.pi * (1 - (t - FEELS_LO) / (FEELS_HI - FEELS_LO))

    def pt(t: float, rr: float) -> tuple[float, float]:
        a = ang(t)
        return cx + rr * math.cos(a), cy - rr * math.sin(a)

    def band(a: float, b: float, color: str) -> str:
        x1, y1 = pt(a, r_out)
        x2, y2 = pt(b, r_out)
        x3, y3 = pt(b, r_in)
        x4, y4 = pt(a, r_in)
        return (f'<path d="M{x1:.1f} {y1:.1f} A{r_out} {r_out} 0 0 1 {x2:.1f} {y2:.1f} '
                f'L{x3:.1f} {y3:.1f} A{r_in} {r_in} 0 0 0 {x4:.1f} {y4:.1f}Z" fill="{color}" opacity=".9"/>')

    bands, low = [], FEELS_LO
    for upper, color, _name, _tip in FEELS_ZONES:
        top = min(upper, FEELS_HI)
        bands.append(band(low, top, color))
        low = top
    deg = 180 * (v - FEELS_LO) / (FEELS_HI - FEELS_LO) - 90  # degrees from straight up, clockwise
    needle = (f'<polygon points="{cx - 3},{cy} {cx + 3},{cy} {cx},{cy - (r_in - 6)}" fill="{c["text"]}" '
              f'transform="rotate({deg:.1f} {cx} {cy})"/><circle cx="{cx}" cy="{cy}" r="5" fill="{c["text"]}"/>')
    name, tip, color = feels_zone(feels_f)
    value = f"{U.convert('tempf', feels_f, metric):.0f}{unit}"
    sub = []
    if actual_f is not None:
        sub.append(f"actual {U.convert('tempf', actual_f, metric):.0f}{unit}")
    if humidity is not None:
        sub.append(f"humidity {humidity:.0f}%")
    svg = (f'<svg viewBox="0 0 220 124" width="100%" style="max-width:260px" role="img" '
           f'aria-label="Feels like {_h.escape(value)}, {_h.escape(name)}">' + "".join(bands) + needle + "</svg>")
    body = (f'<div style="font-family:system-ui,sans-serif;color:{c["text"]};text-align:center">'
            f'<div style="font-size:12px;color:{c["muted"]}">Feels like</div>{svg}'
            f'<div style="font-size:22px;font-weight:700;margin-top:-4px">{_h.escape(value)}</div>'
            f'<div style="font-size:13px;color:{color};font-weight:600">{_h.escape(name)}</div>'
            f'<div style="font-size:12px;color:{c["muted"]};margin-top:2px">{_h.escape(" · ".join(sub))}</div>'
            f'<div style="font-size:12px;color:{c["muted"]};margin-top:4px">{_h.escape(tip)}</div></div>')
    return body, 260


def pressure_band(change: float) -> tuple[str, str]:
    """(name, text) for a 3-hour pressure change in inHg."""
    for _a, b, _color, name, text in PRESSURE_BANDS:
        if change < b:
            return name, text
    return PRESSURE_BANDS[-1][3], PRESSURE_BANDS[-1][4]


def pressure_dial_html(now_inhg: float, change_inhg: float, dark: bool = False,
                       metric: bool = False) -> tuple[str, int]:
    """Pressure trend dial: falling on the left, rising on the right, with the needle at the 3-hour change."""
    c = _colors(dark)
    cx, cy, r = 130, 118, 100

    def ang(v: float) -> float:
        return math.pi * (1 - (max(-0.1, min(0.1, v)) + 0.1) / 0.2)

    def pt(v: float, rr: float) -> tuple[float, float]:
        a = ang(v)
        return cx + rr * math.cos(a), cy - rr * math.sin(a)

    bands = []
    for a, b, color, _name, _text in PRESSURE_BANDS:
        x1, y1 = pt(a, r)
        x2, y2 = pt(b, r)
        x3, y3 = pt(b, r - 22)
        x4, y4 = pt(a, r - 22)
        bands.append(f'<path d="M{x1:.1f} {y1:.1f} A{r} {r} 0 0 1 {x2:.1f} {y2:.1f} L{x3:.1f} {y3:.1f} '
                     f'A{r - 22} {r - 22} 0 0 0 {x4:.1f} {y4:.1f}Z" fill="{color}" opacity=".85"/>')
    v = max(-0.1, min(0.1, change_inhg))
    deg = 180 * (v + 0.1) / 0.2 - 90
    needle = (f'<polygon points="{cx - 3},{cy} {cx + 3},{cy} {cx},{cy - (r - 30)}" fill="{c["text"]}" '
              f'transform="rotate({deg:.1f} {cx} {cy})"/><circle cx="{cx}" cy="{cy}" r="6" fill="{c["text"]}"/>')
    scale = (f'<text x="14" y="146" font-size="10" fill="{c["muted"]}">Falling fast</text>'
             f'<text x="246" y="146" font-size="10" text-anchor="end" fill="{c["muted"]}">Rising fast</text>')
    svg = (f'<svg viewBox="0 0 260 156" width="260" style="max-width:100%;height:auto" role="img" aria-label="Pressure trend">'
           + "".join(bands) + needle + scale + "</svg>")
    name, text = pressure_band(change_inhg)
    unit = U.unit("baromrelin", metric)
    dec = 1 if metric else 2
    now_txt = f"{U.convert('baromrelin', now_inhg, metric):.{dec}f} {unit}"
    chg = U.convert("baromrelin", change_inhg, metric)
    chg_txt = f"{'+' if chg > 0 else ''}{chg:.{dec}f} {unit}"
    body = (f'<div style="font-family:system-ui,sans-serif;color:{c["text"]};display:flex;gap:14px;'
            f'align-items:center;flex-wrap:wrap">{svg}'
            f'<div style="flex:1 1 180px;font-size:13px;line-height:1.5"><div style="font-size:20px;font-weight:700">'
            f'{_h.escape(name)}</div><div>{now_txt} now, {chg_txt} in the last 3 hours.</div>'
            f'<div style="color:{c["muted"]};margin-top:4px">{_h.escape(text)}</div></div></div>')
    return body, 200
