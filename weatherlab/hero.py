"""The "right now" panel at the top of Live: a sky-coloured card with the temperature, the sky icon, the alert pill,
today's range, the last-hour trend, the sunrise or sunset time and the main readings.

Ported from the dashboard's utils/live_cards.py (hero_html). Callers pass text that is already in the display units,
so this module converts nothing. Each builder returns (html, height); Home draws the panel straight into the page (0.37.39).
"""

import html as _h
import math
import random

FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"
GRADS = {"clear_day": ("#1d4f7a", "#3f5f86", "#a0603a"), "cloudy_day": ("#3b4a5e", "#4b566a", "#5e6676"),
         "rain": ("#24384f", "#2f4560", "#3b4f68"), "storm": ("#1f2433", "#2b2440", "#3b2448"),
         "night": ("#0f1a33", "#1d2350", "#2c2a5a"), "dawn": ("#33416e", "#9c5f86", "#f0a868"),
         "dusk": ("#262b55", "#7d4a78", "#e98a52")}


def _e(x) -> str:
    return _h.escape(str(x))


def pick_kind(night: bool, storm: bool, raining: bool, cloudy: bool) -> str:
    """The sky look. Storms and rain win over the time of day, then night, then cloudy or clear."""
    if storm:
        return "storm"
    if raining:
        return "rain"
    if night:
        return "night"
    return "cloudy_day" if cloudy else "clear_day"


def sky_phase(kind, now, sunrise, sunset):
    """Turn a calm-sky kind into dawn or dusk around sunrise and sunset. All times are naive local datetimes."""
    if kind not in ("clear_day", "cloudy_day", "night"):
        return kind
    if sunrise is not None:
        m = (now - sunrise).total_seconds() / 60
        if -30 <= m <= 50:
            return "dawn"
    if sunset is not None:
        m = (now - sunset).total_seconds() / 60
        if -60 <= m <= 25:
            return "dusk"
    return kind


def _stars_uri(n: int = 46, seed: int = 7) -> str:
    """A night sky as an SVG data URI. A few stars twinkle. It is a background layer, so it never covers text."""
    r = random.Random(seed)
    dots = []
    for i in range(n):
        x, y, rad = r.uniform(0, 1000), r.uniform(0, 300), r.choice((0.8, 1.0, 1.2, 1.6))
        op = r.uniform(.35, .9)
        tw = (f'<animate attributeName="opacity" values="{op:.2f};.15;{op:.2f}" dur="{r.uniform(2.5, 5):.1f}s" '
              f'repeatCount="indefinite"/>' if i % 5 == 0 else "")
        dots.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{rad}" fill="white" opacity="{op:.2f}">{tw}</circle>')
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 300" preserveAspectRatio="xMidYMid slice">'
           + "".join(dots) + "</svg>")
    enc = svg.replace('"', "%27").replace("#", "%23").replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")
    return "url('data:image/svg+xml;utf8," + enc + "')"


def sky_bg(kind: str, g: tuple) -> str:
    """CSS background: a gradient, plus stars at night and a low sun glow at dawn and dusk."""
    base = f"linear-gradient(120deg,{g[0]} 0%,{g[1]} 55%,{g[2]} 100%)"
    if kind == "night":
        return f"{_stars_uri()} center/cover no-repeat, {base}"
    if kind == "dawn":
        return f"radial-gradient(ellipse 45% 70% at 92% 115%, rgba(255,200,120,.55), rgba(255,200,120,0) 70%), {base}"
    if kind == "dusk":
        return f"radial-gradient(ellipse 45% 70% at 8% 115%, rgba(255,150,90,.55), rgba(255,150,90,0) 70%), {base}"
    return base


def _badge(d: dict) -> str:
    if d.get("alert"):
        if d.get("alert_tone") == "bad":
            bg, fg, edge = "rgba(217,45,32,.25)", "#ff9a8f", "rgba(217,45,32,.6)"
        else:
            bg, fg, edge = "rgba(240,140,0,.2)", "#ffc266", "rgba(240,140,0,.55)"
        return (f'<div style="display:inline-flex;font-size:13px;font-weight:600;background:{bg};color:{fg};'
                f'border:1px solid {edge};padding:4px 10px;border-radius:99px;margin-top:12px">{_e(d["alert"])}</div>')
    return ('<div style="display:inline-flex;font-size:12px;background:rgba(0,0,0,.2);color:#cfe8d6;padding:4px 10px;'
            'border-radius:99px;margin-top:12px">No weather alerts</div>')


def _range_bar(d: dict, g: tuple) -> str:
    lo, hi, now = d.get("lo"), d.get("hi"), d.get("now")
    if lo is None or hi is None or now is None or hi <= lo:
        return ""
    pos = max(0.0, min(100.0, (now - lo) / (hi - lo) * 100))
    return (f'<div style="margin-top:14px;font-size:12px;color:#d6deea">Today {_e(d.get("lo_text", ""))} low → '
            f'{_e(d.get("hi_text", ""))} high</div>'
            '<div style="height:8px;border-radius:99px;background:linear-gradient(90deg,#5aa9e6,#f6d55c,#f07a3c);'
            f'position:relative;margin-top:6px"><i style="position:absolute;top:-4px;left:calc({pos:.0f}% - 8px);'
            f'width:16px;height:16px;border-radius:50%;background:#fff;border:3px solid {g[0]}"></i></div>')


def hero_html(d: dict) -> tuple[str, int]:
    """d keys: temp_text (required), kind, icon (HTML), feels (text), label, place, live_state ('ok'|'slow'|'silent'|'none'),
    live_text, alert (text), alert_tone ('warn'|'bad'), lo, hi, now (display units), lo_text, hi_text, tiles (list of
    (label, value, note)), trend, trend_col, sun_note, today_line. Lays out in two columns when the page is wide enough."""
    kind = d.get("kind", "clear_day")
    g = GRADS.get(kind, GRADS["clear_day"])
    dot = {"ok": "#3ddc84", "slow": "#f6d55c", "silent": "#e5633c"}.get(d.get("live_state"), "#9aa3b0")
    # One line, "Feels like 71 °F · Sunny · Goodyear", with no separator left over when a part is missing (0.37.47).
    feels = ""
    label_line = " · ".join(x for x in (f"Feels like {_e(d['feels'])}" if d.get("feels") else "",
                                         _e(d.get("label") or ""), _e(d.get("place") or "")) if x)
    tiles = "".join(
        '<div style="background:rgba(0,0,0,.22);border-radius:12px;padding:9px 13px;min-width:0">'
        f'<div style="font-size:12px;color:#c3cbd8">{_e(label)}</div>'
        '<div style="font-size:21px;font-weight:650;margin-top:2px;white-space:nowrap;overflow:hidden;'
        f'text-overflow:ellipsis">{_e(value)}</div>'
        '<div style="font-size:12px;color:#b8c2d0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'
        f'{_e(note)}</div></div>'
        for label, value, note in d.get("tiles", []))
    extra = ""
    if d.get("trend"):
        extra += (f'<div style="font-size:13px;font-weight:600;margin-top:10px;'
                  f'color:{d.get("trend_col", "#c3cbd8")}">{_e(d["trend"])}</div>')
    if d.get("sun_note"):
        extra += f'<div style="font-size:13px;margin-top:4px;color:#f6e7b8">{_e(d["sun_note"])}</div>'
    if d.get("today_line"):
        extra += f'<div style="font-size:12.5px;margin-top:6px;color:#c3cbd8">{_e(d["today_line"])}</div>'
    # Drawn straight into the page (0.37.39), so the styles are scoped to the panel and the two-column layout
    # follows the panel's own width (a container query), not the window's.
    out = (f'<style>.wl-hero-wrap{{container-type:inline-size;font-family:{FONT};margin-bottom:14px}}'
           '.wl-hero{display:grid;grid-template-columns:1fr;gap:22px;align-items:center}'
           '.wl-hero-tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}'
           '@container (min-width:720px){.wl-hero{grid-template-columns:320px 1fr}}</style>'
           '<div class="wl-hero-wrap">'
           f'<div class="wl-hero" style="border-radius:18px;padding:20px 24px;color:#fff;background:{sky_bg(kind, g)}">'
           '<div>'
           '<div style="display:inline-flex;align-items:center;gap:7px;font-size:12px;color:#e6f2ea;'
           'background:rgba(0,0,0,.25);padding:4px 10px;border-radius:99px;margin-bottom:8px">'
           f'<span style="width:8px;height:8px;border-radius:50%;background:{dot};box-shadow:0 0 0 3px {dot}40">'
           f'</span>{_e(d.get("live_text", "Live"))}</div>'
           '<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">'
           f'<div style="font-size:80px;font-weight:700;line-height:1;letter-spacing:-2px">{_e(d["temp_text"])}</div>'
           f'{d.get("icon", "")}</div>'
           f'<div style="color:#dce4ef;font-size:15px;margin-top:6px">{feels}{label_line}</div>'
           f'{_badge(d)}{_range_bar(d, g)}{extra}</div>'
           f'<div class="wl-hero-tiles">{tiles}</div></div></div>')
    rows = math.ceil(len(d.get("tiles", [])) / 2) or 1
    n_extra = sum(1 for k in ("trend", "sun_note", "today_line") if d.get(k))
    height = 300 + rows * 82 + 22 * n_extra  # tall enough for the stacked layout on phones
    return out, height
