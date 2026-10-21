"""Which days have a summary: exact, estimated (from 4-hour readings), or missing."""

from datetime import date, timedelta

EXACT = "exact"
ESTIMATED = "estimated"
MISSING = "missing"
LABELS = {EXACT: "Exact", ESTIMATED: "Estimated", MISSING: "Missing"}


def status(data: dict | None) -> str:
    """The status of one day, given its stored summary (None when there is none)."""
    if data is None:
        return MISSING
    return ESTIMATED if data.get("estimated") else EXACT


def days_between(start: date, end: date) -> list[date]:
    """Every day from start to end, both included. Empty when end is before start."""
    out, day = [], start
    while day <= end:
        out.append(day)
        day += timedelta(days=1)
    return out


def coverage(days: dict[date, dict], start: date, end: date) -> list[tuple[date, str]]:
    """The status of every day in the range, oldest first."""
    return [(day, status(days.get(day))) for day in days_between(start, end)]


def counts(rows: list[tuple[date, str]]) -> dict[str, int]:
    out = {EXACT: 0, ESTIMATED: 0, MISSING: 0}
    for _, state in rows:
        out[state] += 1
    return out


def percent(counted: dict[str, int], total: int) -> float:
    """Share of days that have any summary (exact or estimated)."""
    if total <= 0:
        return 0.0
    return 100.0 * (counted[EXACT] + counted[ESTIMATED]) / total
