"""Sparklines and "usual for this hour" notes for the Home page's at-a-glance cards. Ported from the dashboard's
utils/visuals.py (_spark, usual_delta, compare_text). Values given to these functions are in the stored (US) units,
unless the caller converts them first."""

import html as _h
from datetime import datetime


def spark_svg(values: list, color: str, w: int = 160, h: int = 38) -> str:
    if len(values) < 2:
        return ""
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    pts = [(i * w / (len(values) - 1), h - 3 - (v - lo) / rng * (h - 8)) for i, v in enumerate(values)]
    line = " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" width="100%" height="{h}" style="display:block">'
            f'<path d="M {line} L {w} {h} L 0 {h} Z" fill="{color}" opacity=".13"/>'
            f'<path d="M {line}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" '
            f'vector-effect="non-scaling-stroke"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="3" fill="{color}"/></svg>')


USUAL_DAYS = 5  # earlier days of readings needed before "usual for this hour" is shown


def _hour_matches(rows: list, key: str, tz, now_ts: float, hours_back: int = 24):
    """(current, base, days): the latest value, this hour's values on earlier days, and the set of those days."""
    now_hour = datetime.fromtimestamp(now_ts, tz).hour
    cutoff = now_ts - hours_back * 3600
    current, base, days = None, [], set()
    for ts, reading in rows:
        value = reading.get(key)
        if value is None:
            continue
        current = value
        if ts < cutoff:
            local = datetime.fromtimestamp(ts, tz)
            if local.hour == now_hour:
                base.append(value)
                days.add(local.date())
    return current, base, days


def hourly_usual(rows: list, key: str, tz, now_ts: float, hours_back: int = 24, min_days: int = USUAL_DAYS):
    """rows: (ts, reading) pairs over the past weeks, in time order. Returns (current, usual, days): the latest value,
    the average of this hour of the day on earlier days (before the last hours_back hours), and how many days that
    average uses. None when there are fewer than min_days earlier days."""
    current, base, days = _hour_matches(rows, key, tz, now_ts, hours_back)
    if current is None or len(days) < min_days or not base:
        return None
    return current, sum(base) / len(base), len(days)


def usual_days(rows: list, key: str, tz, now_ts: float, hours_back: int = 24) -> int:
    """How many earlier days have a reading for this hour, counted toward USUAL_DAYS for the progress note."""
    return len(_hour_matches(rows, key, tz, now_ts, hours_back)[2])


def compare_text(cur: float, usual: float, unit: str, neutral: float, decimals: int = 0):
    """(note, direction) comparing the current value with usual. direction is "up", "down" or None."""
    d = cur - usual
    if abs(d) < neutral:
        return "● about usual for this hour", None
    arrow = "▲" if d > 0 else "▼"
    word = "above" if d > 0 else "below"
    gap = " " if unit[:1].isalpha() else ""
    return f"{arrow} {abs(d):.{decimals}f}{gap}{unit} {word} usual for this hour", ("up" if d > 0 else "down")


def tile_html(t: dict) -> str:
    """One at-a-glance card. t keys: label, value, unit, series (display units), color, compare, direction,
    up_color, down_color."""
    colour = {"up": t.get("up_color", "#dc2626"), "down": t.get("down_color", "#2563eb")}.get(t.get("direction"), "inherit")
    note = _h.escape(t["compare"]) if t.get("compare") else "&nbsp;"
    edge = f' style="border-left:4px solid {t["edge"]}"' if t.get("edge") else ""
    return (f'<div class="wl-tile"{edge}>'
            f'<div class="wl-label">{_h.escape(t["label"])}</div>'
            f'<div class="wl-value">{_h.escape(str(t["value"]))}'
            f'<span style="font-size:13px;font-weight:400;opacity:.7"> {_h.escape(t.get("unit", ""))}</span></div>'
            f'{spark_svg(t.get("series") or [], t["color"])}'
            f'<div class="wl-label" style="color:{colour};margin-top:4px">{note}</div></div>')
