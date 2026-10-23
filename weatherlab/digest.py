"""The morning summary notification: yesterday's high, low, rain and sun, in the units the user chose."""

from weatherlab import units


def weekly_text(label: str, days: list, metric: bool) -> str:
    """One line for the week: highest and lowest temperature, total rain, and how many days had readings.
    days: daily summaries (dicts) for the last seven days. Empty string when none of them has data."""
    highs = [d["tempf_max"] for d in days if d.get("tempf_max") is not None]
    lows = [d["tempf_min"] for d in days if d.get("tempf_min") is not None]
    rain = [d["rain_in"] for d in days if d.get("rain_in") is not None]
    if not highs and not lows and not rain:
        return ""
    parts = []
    if highs and lows:
        parts.append(f"high {units.format_value('tempf', max(highs), metric, 0)}, "
                     f"low {units.format_value('tempf', min(lows), metric, 0)}")
    if rain:
        parts.append(f"rain {units.format_value('dailyrainin', sum(rain), metric, 2)}")
    parts.append(f"{len(highs) or len(lows) or len(rain)} of 7 days recorded")
    return f"Last 7 days ({label}): " + ", ".join(parts) + "."


def text(day_label: str, summary: dict, metric: bool) -> str:
    """One line for the notification, or an empty string when the summary has nothing to show."""
    parts = []
    if summary.get("tempf_max") is not None and summary.get("tempf_min") is not None:
        high = units.format_value("tempf", summary["tempf_max"], metric, 0)
        low = units.format_value("tempf", summary["tempf_min"], metric, 0)
        parts.append(f"high {high}, low {low}")
    if summary.get("rain_in") is not None:
        parts.append(f"rain {units.format_value('dailyrainin', summary['rain_in'], metric, 2)}")
    if summary.get("sun_hours") is not None:
        parts.append(f"sun {summary['sun_hours']:.1f} hours")
    if not parts:
        return ""
    return f"Yesterday ({day_label}): " + ", ".join(parts) + "."
