"""The sidebar (0.37.53): a Jump to page box, pinned pages, and groups that fold shut.

Pure functions, so the rules can be tested without Streamlit. app.py draws the sidebar from these."""
from weatherlab.nav_groups import GROUPS

MAX_PINS = 8


def group_of(page: str) -> str | None:
    """The sidebar group a page sits in."""
    return next((g for g, names in GROUPS.items() if page in names), None)


def clean_pins(pins: list[str]) -> list[str]:
    """Pinned pages that still exist, in the order pinned, without repeats, at most MAX_PINS."""
    known = {n for names in GROUPS.values() for n in names}
    out: list[str] = []
    for p in pins:
        if p in known and p not in out:
            out.append(p)
    return out[:MAX_PINS]


def toggle_pin(pins: list[str], page: str) -> list[str]:
    """Pins the page at the end of the list, or unpins it if it is already pinned."""
    pins = clean_pins(pins)
    if page in pins:
        return [p for p in pins if p != page]
    return clean_pins(pins + [page])


def is_open(group: str, closed: list[str], current_page: str | None) -> bool:
    """A group is open unless it was folded shut. The group holding the open page is always open, so you can see
    where you are."""
    return group not in closed or group_of(current_page or "") == group


def set_open(closed: list[str], group: str, open_: bool) -> list[str]:
    """The folded-shut groups after opening or closing one."""
    rest = [g for g in closed if g != group and g in GROUPS]
    return rest if open_ else rest + [group]
