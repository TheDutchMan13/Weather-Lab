"""Getting started on Home (0.37.49): what is still worth setting up once the station is reporting.

Each item says whether it is done, why it matters, and which page (and tab) sets it up. Home shows the items that
are not done, until they are all done or the list is hidden. No Streamlit here, so the tests run without it."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    key: str
    done: bool
    title: str
    detail: str
    page: str  # the sidebar page that sets it up
    tab: str = ""  # the tab to open on that page, as in ?tab=


def items(s, has_topic: bool, has_backup: bool) -> list[Item]:
    """The getting-started items for these settings. has_topic: a phone alerts topic is saved. has_backup: at least
    one backup copy exists."""
    return [
        Item("location", s.latitude is not None and s.longitude is not None, "Set your location",
             "Forecasts, weather warnings, sun times and the briefing need it.", "Setup"),
        Item("alerts", has_topic, "Get alerts on your phone",
             "Rain, lightning, a station that stops reporting, and app problems.", "Settings", "phone alerts"),
        Item("backup", has_backup, "Back up your readings",
             "With backups on, Weather Lab copies the readings once a day. This ticks off once the first copy exists.",
             "Backup"),
        Item("updates", bool(s.update_url.strip()), "Turn on update checks",
             "Home tells you when a newer Weather Lab is out. Turn on uses the official releases on GitHub.",
             "Settings", "updates"),
    ]


def pending(found: list[Item]) -> list[Item]:
    return [i for i in found if not i.done]
