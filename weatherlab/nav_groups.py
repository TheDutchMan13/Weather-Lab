"""The sidebar sections and the pages in each, in order. The first page of the first section opens by default.

Kept apart from app.py so the layout can be tested without the page's dependencies."""

DEFAULT_PAGE = "Home"

# Five areas (0.37.40). Sensors, Status and Health check are views of one Station health page.
# From 0.37.56 related pages are tabs of one page (TABS below), so the sidebar has 19 pages instead of 28.
GROUPS = {
    "Now": ["Home", "Forecast", "Alert history", "Compare stations"],
    "History": ["History", "Ask"],
    "Weather": ["Air and heat", "Wind", "Sun and sky"],
    "Storms": ["Lightning", "Fire", "Tropics", "Radar"],
    "Station": ["Station health", "Stations", "Settings", "Home layout", "Data", "Help"],
}

# Pages made of tabs (0.37.56). Each tab is a page from before 0.37.56; the first tab opens by default.
TABS = {
    "History": ["History", "Rain calendar", "Rain events", "Unusual days", "Replay"],
    "Air and heat": ["Air", "Heat"],
    "Wind": ["Wind", "Wind map"],
    "Sun and sky": ["Sun", "Astronomy"],
    "Data": ["Backup", "Reports", "Export", "Import"],
    "Help": ["Help", "What's New"],
}


def all_pages() -> list[str]:
    return [name for names in GROUPS.values() for name in names]


def moved() -> dict[str, str]:
    """Old page names that are now a tab of another page: old name -> the page it lives on. The old names keep
    working in links, pins and Jump to page."""
    pages = set(all_pages())
    return {tab: page for page, tabs in TABS.items() for tab in tabs if tab not in pages}


def where(name: str) -> tuple[str, str | None]:
    """The sidebar page and tab that show a page name, old or new. A page without tabs has no tab."""
    page = moved().get(name, name)
    tabs = TABS.get(page)
    if not tabs:
        return page, None
    return page, name if name in tabs else tabs[0]


def view_key(page: str) -> str:
    """The session key that remembers which tab of a page is showing."""
    return "view_" + "".join(c if c.isalnum() else "_" for c in page.lower())
