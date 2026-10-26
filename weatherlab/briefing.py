"""The daily briefing: today in a few plain lines. Pure helpers; api_pages.briefing gathers the facts."""

from datetime import date, timedelta

HOT_F = 100.0   # a hot day for the streak


def hot_streak(highs: dict, today: date, today_high=None, threshold: float = HOT_F) -> int:
    """Days in a row at or above the threshold, counting back from today (if it is already there) or yesterday.

    highs: {date: daily high in °F}. today_high: the highest reading so far today, in °F."""
    if today_high is not None and today_high >= threshold:
        count, day = 1, today - timedelta(days=1)
    else:
        count, day = 0, today - timedelta(days=1)
    while highs.get(day) is not None and highs[day] >= threshold:
        count += 1
        day -= timedelta(days=1)
    return count


def difference(now, other, unit: str, other_name: str):
    """"4° warmer than yesterday", "the same as yesterday", or None when either is missing."""
    if now is None or other is None:
        return None
    gap = round(now - other)
    if gap == 0:
        return f"the same as {other_name}"
    return f"{abs(gap)}{unit} {'warmer' if gap > 0 else 'cooler'} than {other_name}"


def headline(high, unit: str, short: str | None, rain_chance, alerts: int, level: str | None) -> str:
    """One sentence for the top of the page."""
    parts = []
    if high is not None:
        parts.append(f"A high near {round(high)}{unit}")
    if short:
        parts.append(short.lower() if parts else short)
    text = ", ".join(parts) if parts else "No forecast yet today"
    text += "."
    extras = []
    if rain_chance:
        extras.append(f"{rain_chance}% chance of rain")
    if level and level not in ("Comfortable", "No data"):
        extras.append(f"heat safety: {level.lower()}")
    if alerts:
        extras.append(f"{alerts} weather alert{'s' if alerts != 1 else ''} in effect")
    if extras:
        text += " " + extras[0][0].upper() + extras[0][1:] + "".join("; " + e for e in extras[1:]) + "."
    return text


def worth_knowing(alerts: list, sunrise, sunset, dew_text, dew_point, streak: int, pressure_word,
                  danger_hours=0.0) -> list:
    """Short lines for the "Worth knowing" list, most important first."""
    lines = [f"{a}" for a in alerts]
    if streak >= 2:
        lines.append(f"{streak} days in a row at {round(HOT_F)}°F or more.")
    if danger_hours and danger_hours >= 0.5:
        lines.append(f"{danger_hours:g} hours so far today at heat safety Danger or worse.")
    if sunrise and sunset:
        lines.append(f"Sunrise {sunrise}, sunset {sunset}.")
    if dew_text and dew_point is not None:
        lines.append(f"Dew point {round(dew_point)}°: {dew_text}.")
    if pressure_word:
        lines.append(f"Pressure is {pressure_word}.")
    return lines


def notification(data: dict) -> str:
    """The morning notification: the headline, then how today's high compares with yesterday and the first alert."""
    parts = [data.get("headline", "").strip()]
    tiles = data.get("tiles") or []
    high = next((t for t in tiles if t.get("label") == "Expected high"), None)
    if high and high.get("note"):
        parts.append(high["note"][0].upper() + high["note"][1:] + ".")
    if data.get("notes"):
        first = data["notes"][0]
        if "Warning" in first or "Advisory" in first or "Watch" in first:
            parts.append(first if first.endswith(".") else first + ".")
    return " ".join(p for p in parts if p)


def due(hour_now: int, send_hour: int, last_day, today, quiet: bool) -> bool:
    """True once a day, after the chosen hour, outside quiet hours."""
    return not quiet and hour_now >= send_hour and last_day != today
