"""Sorting the text in a table by the value it shows (0.37.45).

Tables are built from display text such as "12.3 mph", "1 h 5 min", "6:20 AM" or "Mon Oct 29, 2026", which sorts
wrongly as plain text. sort_value() reads the number, time, duration or date behind a cell. A column can be sorted
only when every cell in it can be read, so the control never offers an order it can't get right. No Streamlit
here, so the tests run without it."""
import re
from datetime import datetime

MISSING_TEXT = {"", "--", "-", "—", "n/a"}
_DATE_FORMATS = ("%a %b %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%b %Y")
_TIME = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s*([AP]M)$", re.IGNORECASE)
_DURATION = re.compile(r"^(?:(\d+)\s*h)?\s*(?:(\d+)\s*min)?$")
_NUMBER = re.compile(r"^[-+−]?\d[\d,]*(?:\.\d+)?")


def sort_value(text) -> tuple[bool, float] | None:
    """(is_missing, value) for a cell, or None when the cell can't be put in order."""
    s = str(text).strip()
    if s.lower() in MISSING_TEXT:
        return (True, 0.0)
    m = _TIME.match(s)
    if m:
        hour = int(m.group(1)) % 12 + (12 if m.group(4).upper() == "PM" else 0)
        return (False, hour * 3600 + int(m.group(2)) * 60 + int(m.group(3) or 0))
    m = _DURATION.match(s)
    if m and (m.group(1) or m.group(2)):
        return (False, int(m.group(1) or 0) * 60 + int(m.group(2) or 0))
    for fmt in _DATE_FORMATS:
        try:
            return (False, float(datetime.strptime(s, fmt).toordinal()))
        except ValueError:
            pass
    m = _NUMBER.match(s)
    if m:
        return (False, float(m.group(0).replace(",", "").replace("−", "-")))
    return None


def sortable_columns(rows: list[dict]) -> list[str]:
    """The columns where every cell can be read and at least one cell has a value."""
    if not rows:
        return []
    found = []
    for col in rows[0]:
        values = [sort_value(r.get(col, "")) for r in rows]
        if all(v is not None for v in values) and any(not v[0] for v in values):
            found.append(col)
    return found


def sort_rows(rows: list[dict], column: str, highest_first: bool = True) -> list[dict]:
    """The rows ordered by a column. Cells with no value (--) always go last. Equal values keep their order."""
    keyed = [(sort_value(r.get(column, "")), r) for r in rows]
    present = [(v[1], r) for v, r in keyed if v is not None and not v[0]]
    absent = [r for v, r in keyed if v is None or v[0]]
    present.sort(key=lambda pair: pair[0], reverse=highest_first)
    return [r for _, r in present] + absent
