"""Plotly charts that look like the dashboard's: the same layout, colours, grid, legend, hover box and toolbar.

Sources (listed in SOURCES.md): wxdash/common.py get_chart_layout and get_accent_border, and utils/chart_cfg.py
chart_config, style_fig and CHART_COLORS. The dashboard's charts don't use the CHART_* values in config.py.
"""

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from weatherlab.settings import load_settings
from weatherlab.theme import is_phone, page_palette

# The dashboard's palette (utils/chart_cfg.py PAL and MEASURE, copied 22 Oct 2026). Each measure has one colour on
# every chart. Charts with several series start with CHART_COLORS.
PAL = {"blue": "#4ea1ff", "amber": "#e8a53c", "red": "#e5483c", "green": "#3ddc84", "gold": "#c9a66b",
       "teal": "#2bb39a", "orange": "#f07a3c", "violet": "#8a5cf0", "quiet": "#6e78ae"}
MEASURE = {"temp": PAL["amber"], "dew": PAL["teal"], "rain": PAL["violet"], "wind": PAL["quiet"],
           "humidity": PAL["quiet"], "gust": "#2e9e63", "pressure": PAL["gold"], "uv": PAL["quiet"],
           "lightning": PAL["quiet"]}
CHART_COLORS = ["#8a5cf0", "#2e9e63", "#e8a53c", "#fb923c", "#f87171", "#dc2626"]
CHART_FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
GRID = "rgba(128,128,128,0.16)"  # the dashboard's y-axis grid colour
TEXT = {True: "#e5e7eb", False: "#374151"}  # chart text on dark and light (utils/chart_cfg.py style_fig)
TOOLBAR_REMOVE = ["zoom2d", "pan2d", "select2d", "lasso2d", "zoomIn2d", "zoomOut2d", "autoScale2d",
                  "hoverClosestCartesian", "hoverCompareCartesian", "toggleSpikelines", "zoom3d", "pan3d",
                  "orbitRotation", "tableRotation", "resetCameraDefault3d", "resetCameraLastSave3d", "hoverClosest3d",
                  "zoomInGeo", "zoomOutGeo", "resetGeo", "hoverClosestGeo", "hoverClosestGl2d", "hoverClosestPie",
                  "toggleHover", "resetViews", "sendDataToCloud", "resetViewMapbox", "toggleSpikelines"]
# Pass as config= to st.plotly_chart: a quiet toolbar that shows on hover, with save-as-picture.
CONFIG = {"displayModeBar": "hover", "displaylogo": False, "modeBarButtonsToRemove": TOOLBAR_REMOVE,
          "toImageButtonOptions": {"format": "png", "scale": 2, "filename": "weather-lab"}}


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def figure(dark: bool, height: int = 340, scheme: str | None = None) -> go.Figure:
    """An empty chart with the dashboard's layout. scheme defaults to the saved colour scheme."""
    saved = load_settings()
    pg = page_palette(dark, scheme or saved.color_scheme)
    phone = is_phone()
    if phone:
        height = max(220, int(height * 0.68))  # get_chart_layout on phones
    fig = go.Figure()
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CHART_FONT, color=TEXT[bool(dark)], size=12),
        hovermode="x unified" if saved.tooltips else False,
        hoverlabel=dict(bgcolor=pg["surface"], bordercolor=pg["accent"], font=dict(color=pg["text"])),
        margin=dict(l=36, r=10, t=36, b=24) if phone else dict(l=40, r=20, t=40, b=30),
        legend=dict(orientation="h", y=-0.3 if phone else -0.22, bgcolor="rgba(0,0,0,0)",
                    bordercolor=_rgba(pg["accent"], 0.2), borderwidth=1),
        xaxis=dict(showgrid=False, zeroline=False, showline=False),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor=GRID, zeroline=False),
    )
    return fig


def show(fig: go.Figure, **kwargs) -> None:
    """Draw a chart the way the dashboard's style_fig does: shorter on phones, time-of-day hover labels on
    time axes, and the hover-only toolbar."""
    if is_phone():
        if fig.layout.height and fig.layout.height > 260:
            fig.update_layout(height=260)
        # fewer, smaller axis labels so they do not run together on a narrow screen
        fig.update_xaxes(nticks=5, tickfont=dict(size=11))
        fig.update_yaxes(nticks=6, tickfont=dict(size=11))
    for trace in fig.data:
        xs = getattr(trace, "x", None)
        if xs is not None and len(xs) and isinstance(xs[0], datetime):
            from weatherlab import timefmt
            fig.update_xaxes(hoverformat=timefmt.hover_format())
            if not timefmt.use_24h():  # plotly shows 24-hour ticks unless told otherwise
                fig.update_xaxes(tickformatstops=[dict(dtickrange=[None, 1800000], value="%-I:%M %p"),
                                                  dict(dtickrange=[1800000, 86400000], value="%-I %p")])
            break
    config = dict(CONFIG, displayModeBar=True) if load_settings().chart_toolbar else CONFIG
    st.plotly_chart(fig, config=config, **kwargs)


def night_bands(fig: go.Figure, lat, lon, tz, start_ts: float, end_ts: float, dark: bool) -> None:
    """Shade the hours between sunset and sunrise behind a time chart, so night shows at a glance. Does nothing
    when the station's location is not set, or when the sun does not set on a day."""
    if lat is None or lon is None:
        return
    from datetime import datetime, timedelta, timezone
    from weatherlab import astro
    shade = "rgba(255,255,255,0.06)" if dark else "rgba(15,23,42,0.06)"
    first = datetime.fromtimestamp(start_ts, tz).date() - timedelta(days=1)
    last = datetime.fromtimestamp(end_ts, tz).date() + timedelta(days=1)
    day = first
    while day <= last:
        _rise, sset = astro.sun_times(lat, lon, day)
        next_rise, _ = astro.sun_times(lat, lon, day + timedelta(days=1))
        if sset is not None and next_rise is not None:
            x0 = sset.replace(tzinfo=timezone.utc).astimezone(tz)
            x1 = next_rise.replace(tzinfo=timezone.utc).astimezone(tz)
            if x1 > x0:
                fig.add_vrect(x0=x0, x1=x1, fillcolor=shade, line_width=0, layer="below")
        day += timedelta(days=1)
