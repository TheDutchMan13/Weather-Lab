"""The sidebar sections and the pages in each, in order. The first page of the first section opens by default.

Kept apart from app.py so the layout can be tested without the page's dependencies."""

DEFAULT_PAGE = "Home"

# Five areas (0.37.40). Sensors, Status and Health check are views of one Station health page.
GROUPS = {
    "Now": ["Home", "Forecast", "Alert history", "Compare stations"],
    "History": ["History", "Rain calendar", "Rain events", "Unusual days", "Replay", "Ask"],
    "Weather": ["Air", "Wind", "Wind map", "Sun", "Heat", "Astronomy"],
    "Storms": ["Lightning", "Fire", "Tropics", "Radar"],
    "Station": ["Station health", "Stations", "Settings", "Home layout", "Reports", "Import", "Export", "Backup",
                "Help", "What's New"],
}


def all_pages() -> list[str]:
    return [name for names in GROUPS.values() for name in names]
