"""Round gauges for the Live page. The temperature ring is ported from the dashboard's wxdash/live.py
(temp_gauge_html). Inputs are in °F; the text shows the chosen units. Returns (html, height)."""

import html as _h
import math

from weatherlab import units as U

TEMP_RAMP = ["#4f9cf0", "#7fd1c8", "#f3d36b", "#f08a3c", "#d9385a"]  # cold to hot
TEMP_MIN, TEMP_MAX = 20.0, 120.0  # °F range around the ring
DIAL = {  # colours per theme, from the dashboard's DIAL
    "dark": dict(face="#111318", text="#eceef1", muted="#9aa1ab", chip="#1d2027", chip_edge="#2a2e36"),
    "light": dict(face="#ffffff", text="#14171c", muted="#5b626d", chip="#f4f6f8", chip_edge="#dfe3e8"),
}


def _ramp(pos: float) -> str:
    pos = min(max(pos, 0.0), 1.0) * (len(TEMP_RAMP) - 1)
    i = min(int(pos), len(TEMP_RAMP) - 2)
    f = pos - i
    a, b = TEMP_RAMP[i], TEMP_RAMP[i + 1]
    return "#" + "".join(f"{round(int(a[k:k + 2], 16) * (1 - f) + int(b[k:k + 2], 16) * f):02x}" for k in (1, 3, 5))


def temp_ring_html(t: float, high=None, low=None, feels=None, dew=None, hum=None,
                   vis=None, vis_note: str = "", dark: bool = False, metric: bool = False) -> tuple[str, int]:
    """Temperature ring: the arc fills clockwise from the top as it warms, coloured cold to hot. Today's high and
    low sit inside the ring, and feels like, dew point, humidity and visibility sit below it."""
    c = DIAL["dark" if dark else "light"]
    unit = U.unit("tempf", metric)

    def shown(v):
        return U.convert("tempf", v, metric)

    cx, cy, rad, n = 150, 150, 118, 90
    frac = min(max((t - TEMP_MIN) / (TEMP_MAX - TEMP_MIN), 0), 1)
    segs = []
    for i in range(n):
        p0, p1 = i / n, (i + 1) / n
        a0, a1 = p0 * 360 + 0.1, p1 * 360 - 0.1
        (x0, y0), (x1, y1) = ((cx + rad * math.sin(math.radians(a)), cy - rad * math.cos(math.radians(a)))
                              for a in (a0, a1))
        on = p1 <= frac + 1 / n / 2
        color = _ramp((p0 + p1) / 2) if on else c["chip_edge"]
        segs.append(f'<path d="M{x0:.1f} {y0:.1f} A{rad} {rad} 0 0 1 {x1:.1f} {y1:.1f}" fill="none" '
                    f'stroke="{color}" stroke-width="22"/>')

    def mark(v):  # a small tick across the ring at a temperature
        a = math.radians(min(max((v - TEMP_MIN) / (TEMP_MAX - TEMP_MIN), 0), 1) * 360)
        (x0, y0), (x1, y1) = ((cx + r * math.sin(a), cy - r * math.cos(a)) for r in (rad - 16, rad + 16))
        return (f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{c["text"]}" '
                f'stroke-width="3" stroke-linecap="round"/>')

    marks = (mark(high) if high is not None else "") + (mark(low) if low is not None else "")
    hi_txt = (f'<text x="150" y="108" text-anchor="middle" font-size="19" font-weight="600" fill="{c["muted"]}">'
              f'↑ {shown(high):.0f}{unit}</text>') if high is not None else ""
    lo_txt = (f'<text x="150" y="212" text-anchor="middle" font-size="19" font-weight="600" fill="{c["muted"]}">'
              f'↓ {shown(low):.0f}{unit}</text>') if low is not None else ""

    def chip(label: str, value: str) -> str:
        return f'<div class="chip"><div class="lab">{label}</div><div class="val">{value}</div></div>'

    chips = (chip("Feels like", f"{shown(feels):.0f}{unit}" if feels is not None else "–")
             + chip("Dew point", f"{shown(dew):.0f}{unit}" if dew is not None else "–")
             + chip("Humidity", f"{hum:.0f}%" if hum is not None else "–"))
    if vis is not None:
        note = f'<div style="font-size:.68em;font-weight:500;opacity:.75;margin-top:2px">{_h.escape(vis_note)}</div>' \
            if vis_note else ""
        chips += chip("Visibility", f'<span style="color:{"#FFB020" if vis < 5 else "inherit"}">{vis:.1f} mi</span>{note}')
    label = _h.escape(f"Outdoor temperature {shown(t):.1f} {unit}.")
    out = f"""<style>
  body {{ margin:0; background:transparent; font-family: system-ui, -apple-system, 'Segoe UI', sans-serif; color:{c['text']}; }}
  .wrap {{ display:flex; flex-direction:column; align-items:center; gap:10px; }}
  svg {{ width:100%; max-width:300px; height:auto; }}
  .row {{ display:flex; gap:8px; width:100%; max-width:380px; }}
  .chip {{ flex:1; box-sizing:border-box; padding:8px 10px; text-align:center; background:{c['chip']};
           border:1px solid {c['chip_edge']}; border-radius:12px; }}
  .lab {{ font-size:10px; font-weight:600; letter-spacing:.1em; text-transform:uppercase; color:{c['muted']}; }}
  .val {{ font-size:20px; font-weight:600; margin-top:2px; font-variant-numeric:tabular-nums; }}
</style>
<div class="wrap" role="img" aria-label="{label}">
<svg viewBox="0 0 300 300">{''.join(segs)}{marks}{hi_txt}
  <text x="150" y="176" text-anchor="middle" font-size="64" font-weight="600" fill="{c['text']}"
        style="font-variant-numeric:tabular-nums">{shown(t):.1f}<tspan font-size="26" dy="-24">{unit}</tspan></text>{lo_txt}
</svg>
<div class="row">{chips}</div>
</div>"""
    return out, 420 + (40 if vis is not None else 0)
