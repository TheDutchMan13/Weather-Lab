"""The morning summary notification: yesterday's high, low, rain and sun, in the units the user chose."""

from weatherlab import units


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
