"""The sidebar sections and the pages in each, in order. The first page of the first section opens by default.

Kept apart from app.py so the layout can be tested without the page's dependencies."""

DEFAULT_PAGE = "Home"

GROUPS = {
    "Now": ["Home", "Alert history"],
    "History": ["History", "Coverage", "Rewind"],
    "Air, sun and heat": ["Air", "Wind", "Wind map", "Sun", "Heat", "Astronomy"],
    "Forecast and storms": ["Forecast", "Lightning", "Fire", "Tropics", "Radar"],
    "Season": ["Rain calendar", "Rain events"],
    "Tools": ["Ask", "Unusual days", "Replay", "Reports", "Import", "Export", "Backup"],
    "Health": ["Sensors", "Status", "Health check"],
    "Settings": ["Settings", "Setup", "Stations", "Help", "What's New"],
}


def all_pages() -> list[str]:
    return [name for names in GROUPS.values() for name in names]
