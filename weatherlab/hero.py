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
    # One line, "Feels like 71 °F · Sunny · Springfield", with no separator left over when a part is missing (0.37.47).
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
    # Hero style (0.37.51): the sky gradient, or one plain colour from the same sky with no gradient, stars or glow.
    background = g[0] if d.get("plain") else sky_bg(kind, g)
    out = (f'<style>.wl-hero-wrap{{container-type:inline-size;font-family:{FONT};margin-bottom:14px}}'
           '.wl-hero{display:grid;grid-template-columns:1fr;gap:22px;align-items:center}'
           '.wl-hero-tiles{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}'
           '@container (min-width:720px){.wl-hero{grid-template-columns:320px 1fr}}</style>'
           '<div class="wl-hero-wrap">'
           f'<div class="wl-hero" style="border-radius:18px;padding:20px 24px;color:#fff;background:{background}">'
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


# ---------------------------------------------------------------------------------------------------------------------
# The redesigned right-now card (0.37.62): sky icon, the big temperature, the conditions and today's range, then today's
# temperature line and the sunrise or sunset time over a strip of sky on the right.

def _clouds_svg(night: bool) -> str:
    """Soft clouds for the sky strip, as a background image."""
    fill = "#c9d6ec" if night else "#ffffff"
    shapes = "".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{fill}" fill-opacity="{o}"/>'
                     for x, y, rx, ry, o in ((330, 70, 120, 34, .55), (410, 52, 80, 30, .5), (240, 92, 90, 22, .35),
                                             (470, 120, 110, 26, .45), (380, 150, 140, 22, .3), (180, 40, 70, 16, .25)))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 200" preserveAspectRatio="xMidYMid slice">'
           '<filter id="b"><feGaussianBlur stdDeviation="9"/></filter>'
           f'<g filter="url(#b)">{shapes}</g></svg>')
    enc = svg.replace('"', "%27").replace("#", "%23").replace("<", "%3C").replace(">", "%3E").replace(" ", "%20")
    return "url('data:image/svg+xml;utf8," + enc + "')"


def card_html(d: dict) -> str:
    """d keys: temp (number text, no unit), unit ("°F"), icon (HTML), label, feels, hi_text, lo_text, trend,
    trend_up (True, False or None for steady), series (today's temperatures), spark (HTML of the line), sun_icon (HTML),
    sun_note, kind, plain, alert, alert_tone ('warn'|'bad')."""
    kind = d.get("kind", "clear_day")
    g = GRADS.get(kind, GRADS["clear_day"])
    night = kind in ("night", "dusk")
    sky = g[1] if d.get("plain") else f"{_clouds_svg(night)} center/cover no-repeat, {sky_bg(kind, g)}"
    arrow, colour = {True: ("▲", "#3ddc84"), False: ("▼", "#7cc4ff")}.get(d.get("trend_up"), ("–", "#9db0c4"))
    trend = (f'<div class="wl-hx-line"><span style="color:{colour}">{arrow}</span> {_e(d["trend"])}</div>'
             if d.get("trend") else "")
    range_line = ""
    if d.get("hi_text") and d.get("lo_text"):
        range_line = (f'<div class="wl-hx-line">High <b>{_e(d["hi_text"])}</b> &nbsp;/&nbsp; Low <b>{_e(d["lo_text"])}</b></div>')
    feels = f'<div class="wl-hx-feels">Feels like {_e(d["feels"])}</div>' if d.get("feels") else ""
    alert = ""
    if d.get("alert"):
        bad = d.get("alert_tone") == "bad"
        bg, fg = ("rgba(217,45,32,.25)", "#ff9a8f") if bad else ("rgba(240,140,0,.2)", "#ffc266")
        alert = (f'<div style="display:inline-flex;font-size:13px;font-weight:650;background:{bg};color:{fg};padding:4px 10px;'
                 f'border-radius:99px;margin-top:8px">{_e(d["alert"])}</div>')
    sun = (f'<div class="wl-hx-sun">{d.get("sun_icon", "")}<span>{_e(d["sun_note"])}</span></div>'
           if d.get("sun_note") else "")
    return ('<style>.wl-hx{container-type:inline-size;margin:0 0 14px;overflow:hidden;position:relative}'
            '.wl-hx-in{display:grid;grid-template-columns:auto auto 1fr;align-items:center;gap:0;position:relative;z-index:1}'
            '.wl-hx-ic{padding:24px 28px 24px 34px}'
            '.wl-hx-t{font-size:96px;font-weight:800;letter-spacing:-3px;line-height:1;padding:0 30px;'
            'border-left:1px solid rgba(160,190,220,.25);white-space:nowrap}'
            '.wl-hx-t sup{font-size:44px;font-weight:700;letter-spacing:0;vertical-align:top;position:relative;top:10px;margin-left:4px}'
            '.wl-hx-c{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);align-items:center;gap:18px;padding:18px 26px 18px 6px}'
            '.wl-hx-label{font-size:30px;font-weight:750;letter-spacing:-.4px}'
            '.wl-hx-feels{font-size:18px;opacity:.85;margin-top:2px}'
            '.wl-hx-line{font-size:18px;margin-top:6px}.wl-hx-line b{font-weight:750}'
            '.wl-hx-right{display:flex;flex-direction:column;justify-content:flex-end;gap:10px;min-height:120px}'
            '.wl-hx-sun{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:600}'
            '.wl-hx-sky{position:absolute;inset:0 0 0 52%;-webkit-mask-image:linear-gradient(90deg,transparent,#000 45%);'
            'mask-image:linear-gradient(90deg,transparent,#000 45%);opacity:.9}'
            '@container (max-width:860px){.wl-hx-in{grid-template-columns:auto 1fr}.wl-hx-c{grid-column:1/-1;padding:0 24px 20px}'
            '.wl-hx-t{font-size:72px;border-left:none;padding:0}.wl-hx-sky{inset:0 0 0 30%}}'
            '@container (max-width:520px){.wl-hx-c{grid-template-columns:1fr}}</style>'
            f'<div class="wl-panel wl-hx"><div class="wl-hx-sky" style="background:{sky}"></div><div class="wl-hx-in">'
            f'<div class="wl-hx-ic">{d.get("icon", "")}</div>'
            f'<div class="wl-hx-t">{_e(d["temp"])}<sup>{_e(d.get("unit", ""))}</sup></div>'
            f'<div class="wl-hx-c"><div><div class="wl-hx-label">{_e(d.get("label") or "")}</div>{feels}{range_line}{trend}{alert}</div>'
            f'<div class="wl-hx-right">{d.get("spark", "")}{sun}</div></div></div></div>')


def metric_html(icon: str, label: str, value: str, unit: str, note: str, spark: str) -> str:
    """One reading card under the right-now card: icon and name, the value, a short note and its last 24 hours."""
    unit_html = f"<small>{_e(unit)}</small>" if unit else ""
    return (f'<div class="wl-panel wl-metric"><div class="wl-mh">{icon}{_e(label)}</div>'
            f'<div class="wl-mv">{_e(value)}{unit_html}</div><div class="wl-mn">{_e(note) or "&nbsp;"}</div>{spark}</div>')
