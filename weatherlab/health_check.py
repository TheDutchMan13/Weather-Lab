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


Row = tuple[str, str, str]  # (name, state, detail)


def evaluate(f: dict, now: float) -> list[dict]:
    """The checks for these facts. Missing keys are treated as "nothing to report". Each group of checks is worked
    out by its own function below, in the order the page shows them."""
    rows: list[Row] = []
    for part in (_station, _storage, _alerts_and_services, _this_app):
        rows.extend(part(f, now))
    return [{"name": name, "state": state, "detail": detail} for name, state, detail in rows]


def _station(f: dict, now: float) -> list[Row]:
    out: list[Row] = []

    def add(name: str, state: str, detail: str) -> None:
        out.append((name, state, detail))

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
    return out


def _storage(f: dict, now: float) -> list[Row]:
    out: list[Row] = []

    def add(name: str, state: str, detail: str) -> None:
        out.append((name, state, detail))

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
        behind = f.get("copy_behind_days") or 0
        if behind >= COPY_BEHIND_DAYS:
            # Three days without an off-site copy is worth a phone alert (0.37.54).
            add("Second backup folder", "fail",
                f"The off-site copy is {behind} days behind. Check the drive is plugged in or the network folder is "
                "reachable; it catches up by itself once it's back.")
        elif f.get("copy_error"):
            add("Second backup folder", "warn", f"{f['copy_error']} It tries again every hour.")
        elif f.get("copy_folder_ok"):
            add("Second backup folder", "ok", "Writable." if not behind else f"{behind} day behind; it catches up hourly.")
        else:
            add("Second backup folder", "warn", "Can't write to the second backup folder. Check the drive is connected.")

    if f.get("settings_writable") is False:
        add("Settings", "fail", "Settings can't be saved. Check the folder permissions.")
    else:
        add("Settings", "ok", "Settings can be saved.")
    return out


def _alerts_and_services(f: dict, now: float) -> list[Row]:
    out: list[Row] = []

    def add(name: str, state: str, detail: str) -> None:
        out.append((name, state, detail))

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

    if f.get("nws_on"):
        if f.get("nws_error"):
            add("Weather warnings", "warn", f"Couldn't check the National Weather Service: {f['nws_error']}")
        else:
            add("Weather warnings", "ok", "Checking the National Weather Service every 15 minutes.")
    if f.get("reports_on"):
        if f.get("report_error"):
            add("Automatic reports", "warn", f"Couldn't make a report: {f['report_error']}")
        else:
            add("Automatic reports", "ok", "Monthly and yearly PDFs are made on their own.")
    if f.get("archive_days"):
        if f.get("archive_error"):
            add("Reading archive", "warn", f"Couldn't move old readings: {f['archive_error']}")
        else:
            add("Reading archive", "ok", f"Readings older than {f['archive_days']} days move to the archive.")
    return out


def _this_app(f: dict, now: float) -> list[Row]:
    out: list[Row] = []

    def add(name: str, state: str, detail: str) -> None:
        out.append((name, state, detail))

    errors = f.get("recent_errors")
    if errors is not None:
        if errors:
            when, where, text = errors[0]
            add("Recent errors", "warn", f"{len(errors)} in the last 24 hours. The latest, {age_text(now - when)}, "
                                         f"was in the {where}: {text}")
        else:
            add("Recent errors", "ok", "None in the last 24 hours.")

    if f.get("allow_network"):
        add("Phone and device access", "info", "Phones and devices on your network can open Weather Lab.")
    if f.get("update_available"):
        add("Updates", "info", f"Version {f['update_available']} is available.")
    return out


GROUPS = [("Station", ["Background collector", "Station readings", "Station connection"]),
          ("Storage", ["Database", "Disk space", "Backups", "Second backup folder", "Reading archive", "Settings"]),
          ("Alerts and reports", ["Windows notifications", "Weather warnings", "Automatic reports"]),
          ("Online services", ["Forecast", "Air quality"]),
          ("This app", ["Phone and device access", "Updates", "Recent errors"])]


COPY_BEHIND_DAYS = 3  # an off-site copy this many days behind sends a phone alert (0.37.54)
ALERT_CHECKS = ("Disk space", "Backups", "Second backup folder")  # problems worth a phone alert, because nothing else will tell you


def alert_messages(checks: list[dict], alerted: set) -> tuple[list[str], set]:
    """(messages, failing). A message for each alert-worthy check that has just started failing, and the names failing
    now. Pass the second back in next time, so a problem is sent once and sent again only if it clears and returns."""
    failing = {c["name"]: c for c in checks if c["state"] == "fail" and c["name"] in ALERT_CHECKS}
    messages = [f"Weather Lab problem: {name}. {c['detail']}" for name, c in failing.items() if name not in alerted]
    return messages, set(failing)


def grouped(checks: list[dict]) -> list[tuple[str, list[dict]]]:
    """The checks in fixed groups, in order. Checks not named in GROUPS go under Other, at the end."""
    out = []
    for title, names in GROUPS:
        rows = [c for c in checks if c["name"] in names]
        if rows:
            out.append((title, rows))
    listed = {name for _, names in GROUPS for name in names}
    other = [c for c in checks if c["name"] not in listed]
    if other:
        out.append(("Other", other))
    return out


def summary(checks: list[dict]) -> str:
    """One line: how many checks need attention."""
    needs = sum(1 for c in checks if c["state"] in ("warn", "fail"))
    return "Everything is working." if not needs else f"{needs} to check."
