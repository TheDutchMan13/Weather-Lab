"""Health check: one list of the things that keep Weather Lab working. Each check is ok, check, problem or info.

evaluate() takes the facts the app gathers (see health_check_page in app.py) and returns the checks.
It doesn't use Streamlit, so it can be tested on its own.
"""

MB = 1024 ** 2
GB = 1024 ** 3
LABELS = {"ok": "OK", "warn": "Check", "fail": "Problem", "info": "Info"}


def age_text(seconds: float) -> str:
    """How long ago, in words: "just now", "12 min ago", "3 h ago", "2 days ago"."""
    s = max(0, int(seconds))
    if s < 120:
        return "just now"
    if s < 3600:
        return f"{s // 60} min ago"
    if s < 2 * 86400:
        return f"{s // 3600} h ago"
    return f"{s // 86400} days ago"


def evaluate(f: dict, now: float) -> list[dict]:
    """The checks for these facts. Missing keys are treated as "nothing to report"."""
    out: list[dict] = []

    def add(name: str, state: str, detail: str) -> None:
        out.append({"name": name, "state": state, "detail": detail})

    if f.get("poller_alive") is False:
        add("Background collector", "fail", "It has stopped. Restart Weather Lab.")
    else:
        add("Background collector", "ok", "Running.")

    last = f.get("latest_reading_ts")
    if last is None:
        add("Station readings", "warn", "No readings stored yet.")
    else:
        age = now - last
        if age <= 600:
            add("Station readings", "ok", f"Last reading {age_text(age)}.")
        elif age <= 1800:
            add("Station readings", "warn", f"Last reading {age_text(age)}. The station may be slow or offline.")
        else:
            add("Station readings", "fail", f"Last reading {age_text(age)}. Check the station's power and network.")
    if f.get("last_poll_error"):
        add("Station connection", "warn", f"The last try failed: {f['last_poll_error']}")
    elif f.get("last_poll_ok"):
        add("Station connection", "ok", "Connected.")

    if f.get("db_exists") is False:
        add("Database", "warn", "The database file isn't there yet.")
    else:
        add("Database", "ok", f"{f.get('db_bytes', 0) / MB:.1f} MB.")
    free = f.get("disk_free_bytes")
    if free is not None:
        if free < 200 * MB:
            add("Disk space", "fail", f"Only {free / MB:.0f} MB free on the drive. Free up space.")
        elif free < GB:
            add("Disk space", "warn", f"{free / GB:.1f} GB free on the drive.")
        else:
            add("Disk space", "ok", f"{free / GB:.1f} GB free on the drive.")

    if not f.get("backup_enabled"):
        add("Backups", "warn", "Daily backups are turned off.")
    elif f.get("backup_error"):
        add("Backups", "fail", f"The last backup failed: {f['backup_error']}")
    else:
        newest = f.get("backup_newest_ts")
        if newest is None:
            add("Backups", "warn", "No backup yet. The next hourly check will make one.")
        elif now - newest > 2 * 86400:
            add("Backups", "warn", f"The last backup was {age_text(now - newest)}. Backups should be daily.")
        else:
            add("Backups", "ok", f"Last backup {age_text(now - newest)}.")
    if f.get("copy_folder") is not None:
        if f.get("copy_folder_ok"):
            add("Second backup folder", "ok", "Writable.")
        else:
            add("Second backup folder", "warn", "Can't write to the second backup folder. Check the drive is connected.")

    if f.get("settings_writable") is False:
        add("Settings", "fail", "Settings can't be saved. Check the folder permissions.")
    else:
        add("Settings", "ok", "Settings can be saved.")
    if f.get("notifications_ok") is False:
        add("Windows notifications", "warn", "Notifications aren't available here.")
    else:
        add("Windows notifications", "ok", "Available.")

    if f.get("forecast_error"):
        add("Forecast", "warn", f"Couldn't save the forecast: {f['forecast_error']}")
    else:
        add("Forecast", "ok", "No problems saving forecasts.")
    if f.get("aqi_error"):
        add("Air quality", "warn", f"Couldn't get air quality: {f['aqi_error']}")
    elif f.get("airnow_key"):
        add("Air quality", "ok", "AirNow key saved.")
    else:
        add("Air quality", "info", "No AirNow key saved. It's optional.")

    if f.get("allow_network"):
        add("Phone and device access", "info", "Phones and devices on your network can open Weather Lab.")
    if f.get("update_available"):
        add("Updates", "info", f"Version {f['update_available']} is available.")
    return out


def summary(checks: list[dict]) -> str:
    """One line: how many checks need attention."""
    needs = sum(1 for c in checks if c["state"] in ("warn", "fail"))
    return "Everything is working." if not needs else f"{needs} to check."
