"""The sidebar sections and the pages in each, in order. The first page of the first section opens by default.

Kept apart from app.py so the layout can be tested without the page's dependencies."""

DEFAULT_PAGE = "Live"

GROUPS = {
    "Now": ["Live", "Alert history"],
    "History": ["Daily", "Records", "Rankings", "Coverage"],
    "Air, sun and heat": ["Air", "Wind", "Wind map", "Sun", "Heat", "Astronomy"],
    "Forecast and storms": ["Forecast", "Lightning", "Fire", "Tropics", "Radar"],
    "Season": ["Rain calendar", "Rain events", "My year", "Rewind", "Climate charts"],
    "Tools": ["Ask", "Unusual days", "Replay", "Reports", "Import", "Export"],
    "Health": ["Sensors", "Status", "Health check"],
    "Settings": ["Settings", "Setup", "Stations", "Help", "What's New"],
}


def all_pages() -> list[str]:
    return [name for names in GROUPS.values() for name in names]
