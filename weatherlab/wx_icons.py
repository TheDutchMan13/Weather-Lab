"""Animated weather icons for the dashboard: the Live 'right now' card and the forecast pages.
One inline SVG per sky kind. The motion is CSS only and stops when the viewer asks for reduced motion.
Drawn here, not copied from anyone else's artwork."""
import math

_CSS = (
    ".wx .rays{transform-box:view-box;transform-origin:50px 50px;animation:wxSpin 16s linear infinite}"
    ".wx .sun{transform-box:view-box;transform-origin:50px 50px;animation:wxPulse 4s ease-in-out infinite}"
    ".wx .cloud{animation:wxDrift 5s ease-in-out infinite}"
    ".wx .drop{animation:wxFall 1.1s linear infinite}"
    ".wx .d2{animation-delay:.37s}.wx .d3{animation-delay:.74s}"
    ".wx .flake{animation:wxFlake 3s linear infinite}"
    ".wx .flake.d2{animation-delay:1s}.wx .flake.d3{animation-delay:2s}"
    ".wx .fog{animation:wxSlide 4s ease-in-out infinite}"
    ".wx .fog.d2{animation-delay:.6s}.wx .fog.d3{animation-delay:1.2s}"
    ".wx .gust{animation:wxGust 1.8s ease-in infinite}"
    ".wx .gust.d2{animation-delay:.6s}.wx .gust.d3{animation-delay:1.2s}"
    ".wx .bolt{animation:wxFlash 2.4s linear infinite}"
    ".wx .setting{animation:wxSink 4s ease-in-out infinite}"
    ".wx .star{animation:wxTwinkle 3s ease-in-out infinite}"
    ".wx .star.s2{animation-delay:1.2s}"
    "@keyframes wxSpin{to{transform:rotate(360deg)}}"
    "@keyframes wxPulse{0%,100%{transform:scale(1)}50%{transform:scale(1.06)}}"
    "@keyframes wxDrift{0%,100%{transform:translateX(-3px)}50%{transform:translateX(3px)}}"
    "@keyframes wxFall{0%{transform:translateY(-4px);opacity:0}25%{opacity:1}100%{transform:translateY(20px);opacity:0}}"
    "@keyframes wxFlake{0%{transform:translateY(-4px) translateX(0);opacity:0}25%{opacity:1}50%{transform:translateY(8px) translateX(2px)}"
    "100%{transform:translateY(20px) translateX(-2px);opacity:0}}"
    "@keyframes wxSlide{0%,100%{transform:translateX(-4px)}50%{transform:translateX(4px)}}"
    "@keyframes wxGust{0%{transform:translateX(-10px);opacity:0}30%{opacity:1}100%{transform:translateX(10px);opacity:0}}"
    "@keyframes wxFlash{0%,56%,64%,100%{opacity:0}58%,62%{opacity:1}}"
    "@keyframes wxSink{0%,100%{transform:translateY(0)}50%{transform:translateY(3px)}}"
    "@keyframes wxTwinkle{0%,100%{opacity:.9}50%{opacity:.2}}"
    "@media (prefers-reduced-motion: reduce){.wx *{animation:none!important}}"
)

# forecast wording -> sky kind (checked in order; rain outranks wind so 'windy with showers' shows rain)
_FORECAST_KINDS = (
    (("thunder",), "storm"),
    (("snow", "sleet", "flurr"), "snow"),
    (("shower", "rain", "drizzle"), "rain"),
    (("fog", "haze", "smoke", "dust"), "fog"),
    (("wind", "breezy", "gusty"), "wind"),
)


def _sun(x, y, r):
    rays = []
    for i in range(12):
        a = math.radians(i * 30)
        rays.append(f'<line x1="{x + (r + 4) * math.cos(a):.1f}" y1="{y + (r + 4) * math.sin(a):.1f}" '
                    f'x2="{x + (r + 11) * math.cos(a):.1f}" y2="{y + (r + 11) * math.sin(a):.1f}" '
                    'stroke="#fde047" stroke-width="3.2" stroke-linecap="round"/>')
    return (f'<g class="rays">{"".join(rays)}</g>'
            f'<circle class="sun" cx="{x}" cy="{y}" r="{r}" fill="#fde047"/>')


def _cloud(x, y, s=1.0, col="#f1f5f9"):
    return (f'<g transform="translate({x},{y}) scale({s})"><g class="cloud" fill="{col}">'
            '<ellipse cx="0" cy="0" rx="34" ry="16"/><ellipse cx="-16" cy="-10" rx="17" ry="15"/>'
            '<ellipse cx="12" cy="-14" rx="20" ry="18"/></g></g>')


def _drops(xs, col="#7dd3fc"):
    out = []
    for i, x in enumerate(xs):
        cls = "drop" if i == 0 else f"drop d{i + 1}"
        out.append(f'<line class="{cls}" x1="{x}" y1="70" x2="{x - 3}" y2="80" stroke="{col}" stroke-width="3" '
                   'stroke-linecap="round"/>')
    return "".join(out)


def _flakes(xs):
    out = []
    for i, x in enumerate(xs):
        cls = "flake" if i == 0 else f"flake d{i + 1}"
        out.append(f'<circle class="{cls}" cx="{x}" cy="72" r="2.8" fill="#e0f2fe"/>')
    return "".join(out)


def _moon(cx=48, cy=50, r=24, hole_x=62, hole_y=40, hole_r=19):
    return (f'<mask id="wxmoon"><rect width="100" height="100" fill="#fff"/>'
            f'<circle cx="{hole_x}" cy="{hole_y}" r="{hole_r}" fill="#000"/></mask>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fde68a" mask="url(#wxmoon)"/>')


def _body(kind):
    if kind == "clear_day":
        return _sun(50, 50, 18)
    if kind == "cloudy_day":
        return _sun(40, 40, 13) + _cloud(60, 62, 0.8, "#e2e8f0")
    if kind == "cloud":
        return _cloud(50, 50, 1.05, "#e2e8f0")
    if kind == "rain":
        return _cloud(50, 40, 0.95, "#cbd5e1") + _drops([34, 50, 66])
    if kind == "storm":
        return (_cloud(50, 38, 0.95, "#64748b") +
                '<polygon class="bolt" points="54,56 44,72 52,72 46,88 62,68 53,68 58,56" fill="#fde047"/>' +
                _drops([32, 68], "#93c5fd"))
    if kind == "snow":
        return _cloud(50, 40, 0.95, "#e2e8f0") + _flakes([34, 50, 66])
    if kind == "fog":
        lines = []
        for i, y in enumerate((44, 58, 72)):
            cls = "fog" if i == 0 else f"fog d{i + 1}"
            lines.append(f'<line class="{cls}" x1="18" y1="{y}" x2="82" y2="{y}" stroke="#cbd5e1" '
                         'stroke-width="4" stroke-linecap="round"/>')
        return "".join(lines)
    if kind == "wind":
        lines = []
        for i, y in enumerate((38, 52, 66)):
            cls = "gust" if i == 0 else f"gust d{i + 1}"
            lines.append(f'<line class="{cls}" x1="18" y1="{y}" x2="78" y2="{y}" stroke="#cbd5e1" '
                         'stroke-width="4" stroke-linecap="round"/>')
        return "".join(lines)
    if kind == "night":
        return (_moon() +
                '<circle class="star" cx="18" cy="22" r="1.6" fill="#fff"/>'
                '<circle class="star s2" cx="84" cy="26" r="1.3" fill="#fff"/>'
                '<circle class="star" cx="80" cy="84" r="1.2" fill="#fff"/>')
    if kind == "partly_night":
        return _moon(38, 38, 16, 48, 30, 13) + _cloud(60, 64, 0.8, "#e2e8f0")
    if kind in ("dawn", "dusk"):
        return ('<clipPath id="wxhz"><rect x="0" y="0" width="100" height="66"/></clipPath>'
                '<g class="setting"><g clip-path="url(#wxhz)">'
                '<circle cx="50" cy="66" r="24" fill="#fdba74"/></g></g>'
                '<line x1="14" y1="66" x2="86" y2="66" stroke="#fb923c" stroke-width="3" stroke-linecap="round"/>'
                '<line x1="24" y1="78" x2="76" y2="78" stroke="#fb923c" stroke-width="2.5" stroke-linecap="round" opacity=".6"/>')
    return _sun(50, 50, 18)


def now_icon(kind, size=84, inline=False):
    """Inline HTML for a sky icon. Unknown kinds fall back to a clear-day sun. inline=True sits on a line of text."""
    style = "vertical-align:middle;flex:0 0 auto;overflow:visible" if inline else "flex:0 0 auto;overflow:visible"
    return (f'<svg class="wx" viewBox="0 0 100 100" width="{size}" height="{size}" role="img" '
            f'aria-label="{kind.replace("_", " ")}" style="{style}">'
            f'<style>{_CSS}</style>{_body(kind)}</svg>')


def forecast_icon(text, night=False, size=30):
    """Sky icon for a forecast period, from the NWS short forecast wording."""
    low = str(text or "").lower().split(" then ")[0]
    kind = None
    for keys, k in _FORECAST_KINDS:
        if any(x in low for x in keys):
            kind = k
            break
    if kind is None:
        if "partly" in low or "mostly sunny" in low:
            kind = "partly_night" if night else "cloudy_day"
        elif "cloud" in low or "overcast" in low:
            kind = "cloud"
        else:
            kind = "night" if night else "clear_day"
    return now_icon(kind, size, inline=True)
