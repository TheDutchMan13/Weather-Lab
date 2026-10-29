"""Shapes for the Home page's alert map: each active alert shaded on its zones, the most severe drawn on top.
Zone outlines come from the National Weather Service at run time, so no geography is bundled with the app.
This module only computes the shapes; app.py draws them with Plotly."""

import math

from weatherlab import nws

ORDER = ["Unknown", "Minor", "Moderate", "Severe", "Extreme"]


def _rank(alert: dict) -> int:
    sev = alert.get("severity")
    return ORDER.index(sev) if sev in ORDER else 0


def traces(alerts: list, highlight: int | None = None) -> list:
    """alerts: dicts with event, severity, ugc (zone codes) and zones (a list of (zone, rings)). highlight: the index
    of the alert to emphasise, or None. Returns one dict per ring (xs, ys, color, opacity, name), least severe first.
    When an alert is highlighted, its zones stay bright and the other zones fade."""
    hl = set(alerts[highlight].get("ugc", [])) if highlight is not None else None
    out = []
    for i in sorted(range(len(alerts)), key=lambda k: _rank(alerts[k])):
        a = alerts[i]
        color = nws.SEVERITY_COLORS.get(a.get("severity"), nws.SEVERITY_COLORS["Unknown"])
        for zone, rings in a.get("zones", []):
            opacity = 0.75 if hl is None else (0.95 if zone in hl else 0.2)
            for ring in rings:
                out.append({"xs": [p[0] for p in ring], "ys": [p[1] for p in ring], "color": color,
                            "opacity": opacity, "name": a.get("event", "Alert")})
    return out


def view_box(lat: float, lon: float, span: float = 0.8) -> tuple[float, float, float, float]:
    """(x0, x1, y0, y1) around a location. Longitude is stretched so the map looks square."""
    dlon = span / max(0.2, math.cos(math.radians(lat)))
    return lon - dlon, lon + dlon, lat - span, lat + span
