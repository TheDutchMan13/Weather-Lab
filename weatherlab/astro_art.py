"""Two small pictures for the Astronomy pages: the sun's path across the sky and the moon's phase. Plain SVG that
takes its colours from the surrounding text, so it works in light and dark."""

import html
import math


def sun_arc_svg(progress, rise_text: str, set_text: str) -> str:
    """A dashed arch from sunrise to sunset. `progress` is 0 to 1 through the day, or None at night."""
    def point(t):  # a point on the quadratic curve from (20,100) over (160,-30) to (300,100)
        x = (1 - t) ** 2 * 20 + 2 * (1 - t) * t * 160 + t ** 2 * 300
        y = (1 - t) ** 2 * 100 + 2 * (1 - t) * t * -30 + t ** 2 * 100
        return x, y

    dot = path = ""
    if progress is not None:
        t = min(max(progress, 0.0), 1.0)
        x, y = point(t)
        cx = (1 - t) * 20 + t * 160   # control point of the part already travelled
        cy = (1 - t) * 100 + t * -30
        path = f'<path d="M20 100 Q{cx:.1f} {cy:.1f} {x:.1f} {y:.1f}" fill="none" stroke="#EF9F27" stroke-width="3" stroke-linecap="round"/>'
        dot = f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="#FAC775" stroke="#BA7517" stroke-width="2"/>'
    label = ("The sun is up" if progress is not None else "The sun is down")
    return (f'<svg viewBox="0 0 320 124" width="100%" role="img" aria-label="{label}. Sunrise {html.escape(rise_text)}, '
            f'sunset {html.escape(set_text)}" style="max-width:420px;display:block">'
            f'<path d="M20 100 Q160 -30 300 100" fill="none" stroke="currentColor" stroke-opacity=".35" stroke-width="1.5" stroke-dasharray="4 4"/>'
            f'<line x1="12" y1="100" x2="308" y2="100" stroke="currentColor" stroke-opacity=".25"/>{path}{dot}'
            f'<text x="20" y="118" font-size="12" fill="currentColor" fill-opacity=".7">{html.escape(rise_text)}</text>'
            f'<text x="300" y="118" font-size="12" fill="currentColor" fill-opacity=".7" text-anchor="end">{html.escape(set_text)}</text></svg>')


def moon_svg(illumination: float, waxing: bool, size: int = 64) -> str:
    """The moon as seen from the northern hemisphere: the lit side is on the right while it grows."""
    r = 28.0
    k = max(0.0, min(illumination, 100.0)) / 100.0
    rx = abs(1 - 2 * k) * r   # width of the curved edge that splits light from dark
    if k <= 0.005:
        lit = ""
    elif k >= 0.995:
        lit = f'<circle cx="32" cy="32" r="{r:.0f}" fill="#B4B2A9"/>'
    else:
        outer = 1 if waxing else 0           # the side that is lit
        inner = 1 - outer if k < 0.5 else outer   # a crescent's inner curve bulges toward the lit side, a gibbous toward the dark side
        lit = (f'<path d="M32 4 A{r:.0f} {r:.0f} 0 0 {outer} 32 60 A{rx:.1f} {r:.0f} 0 0 {inner} 32 4 Z" fill="#B4B2A9"/>')
    return (f'<svg viewBox="0 0 64 64" width="{size}" height="{size}" role="img" aria-label="Moon, {illumination:.0f}% lit">'
            f'<circle cx="32" cy="32" r="{r:.0f}" fill="currentColor" fill-opacity=".08" stroke="currentColor" stroke-opacity=".35"/>{lit}</svg>')
