"""Sorts the saved alerts for the Alert history page (0.37.63): what each is about and how serious it is.

The alert log keeps only the text Weather Lab sent, so this reads the words. Pure functions, no streamlit."""

import re

# (words, kind, level, icon). The first match wins, so the most serious come first.
RULES = [
    (("yesterday (",), "Weather", "Info", "calendar"),  # the daily summary
    (("tornado", "extreme", "severe thunderstorm warning", "flash flood warning", "hurricane"), "Weather", "Critical", "alert"),
    (("lightning",), "Weather", "Critical", "bolt"),
    (("warning",), "Weather", "Warning", "alert"),
    (("not reporting", "stopped reporting", "hasn't received", "no reading", "no data", "offline", "can't reach", "couldn't reach", "stuck"), "Station", "Warning", "station"),
    (("battery",), "Station", "Warning", "battery"),
    (("back online", "reporting again", "is back"), "Station", "Info", "station"),
    (("gust", "wind"), "Weather", "Warning", "wind"),
    (("rain rate", "heavy rain", "flood"), "Weather", "Warning", "rain"),
    (("heat", "temperature reached", "hot", "freeze", "frost", "cold"), "Weather", "Warning", "thermo"),
    (("watch", "advisory"), "Weather", "Warning", "alert"),
    (("rain has started", "rain has stopped", "rain"), "Weather", "Info", "rain"),
    (("record",), "Weather", "Info", "thermo"),
    (("available", "update", "backup", "report", "weather lab"), "App", "Info", "info"),
]
LEVELS = ("Critical", "Warning", "Info")
KINDS = ("Weather", "Station", "App")


def classify(text: str) -> dict:
    """{"kind": Weather | Station | App, "level": Critical | Warning | Info, "icon": name, "title", "detail"}."""
    low = text.lower()
    kind, level, icon = "Weather", "Info", "info"
    for words, k, lv, ic in RULES:
        if any(w in low for w in words):
            kind, level, icon = k, lv, ic
            break
    title, detail = split(text)
    return {"kind": kind, "level": level, "icon": icon, "title": title, "detail": detail}


def split(text: str) -> tuple[str, str]:
    """The first sentence as a title and the rest as detail. A colon also splits ("High wind gust: 28 mph")."""
    text = " ".join(text.split())
    m = re.match(r"(.{4,80}?[.!?:])\s+(.+)", text)
    if m:
        return m.group(1).rstrip(".:"), m.group(2)
    return text.rstrip("."), ""


def counts(items: list[dict]) -> dict:
    """How many of each level, and the total."""
    out = {lv: 0 for lv in LEVELS}
    for it in items:
        out[it["level"]] += 1
    out["total"] = len(items)
    return out
