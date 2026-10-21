"""Plotly charts that look like the dashboard's: the same layout, colours, grid, legend, hover box and toolbar.

Sources (listed in SOURCES.md): wxdash/common.py get_chart_layout and get_accent_border, and utils/chart_cfg.py
chart_config, style_fig and CHART_COLORS. The dashboard's charts don't use the CHART_* values in config.py.
"""

from datetime import datetime

import plotly.graph_objects as go
import streamlit as st

from weatherlab.settings import load_settings
from weatherlab.theme import is_phone, page_palette

CHART_COLORS = ["#4a9eff", "#4ac880", "#facc15", "#fb923c", "#f87171", "#dc2626"]
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
    if is_phone() and fig.layout.height and fig.layout.height > 260:
        fig.update_layout(height=260)
    for trace in fig.data:
        xs = getattr(trace, "x", None)
        if xs is not None and len(xs) and isinstance(xs[0], datetime):
            fig.update_xaxes(hoverformat="%b %d, %-I:%M %p")
            break
    config = dict(CONFIG, displayModeBar=True) if load_settings().chart_toolbar else CONFIG
    st.plotly_chart(fig, config=config, **kwargs)
