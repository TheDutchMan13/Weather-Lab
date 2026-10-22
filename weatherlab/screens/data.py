"""Pages under Data: import, export and reports."""

import io
import sqlite3
import streamlit as st
from dataclasses import replace
from datetime import date, datetime, timedelta
from weatherlab import auto_reports, backup, ecowitt_import, exports, history, importer, noaa, report, secrets, storage, theme, units
from weatherlab.settings import Settings, load_settings, save_settings
from zoneinfo import ZoneInfo
from weatherlab.screens.common import _tz, empty_card, start_poller


# ---------------------------------------------------------------- Reports
def reports_page() -> None:
    s = load_settings()
    today = datetime.now(_tz(s)).date()
    db = storage.connect()
    st.markdown(theme.title_html("Reports"), unsafe_allow_html=True)
    auto = st.checkbox("Make reports automatically", value=s.auto_reports, key="auto_reports_on",
                       help="Last month's PDF is made each month, and last year's in January. Each file is made once.")
    if auto != s.auto_reports:
        save_settings(replace(s, auto_reports=auto))
    st.caption(f"Saved in {auto_reports.folder()}.")
    error = start_poller().status.report_error
    if error:
        st.warning(error)
    kind = st.radio("Report", ["Monthly", "Yearly"], horizontal=True)
    year = st.number_input("Year", min_value=2000, max_value=today.year, value=today.year, step=1)
    if kind == "Monthly":
        names = [datetime(2000, m, 1).strftime("%B") for m in range(1, 13)]
        month = st.selectbox("Month", range(1, 13), index=today.month - 1, format_func=lambda m: names[m - 1])
        first = date(int(year), month, 1)
        last = date(int(year) + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
        rows = history.daily_between(db, first, last)
        if not rows:
            empty_card("No daily summaries for that month yet")
            return
        st.download_button("Download monthly report", data=report.monthly_pdf(int(year), month, rows, units.is_metric(load_settings().units)),
                           file_name=f"weather_report_{int(year)}_{month:02d}.pdf", mime="application/pdf")
    else:
        rows = history.daily_between(db, date(int(year), 1, 1), date(int(year), 12, 31))
        if not rows:
            empty_card("No daily summaries for that year yet")
            return
        st.download_button("Download yearly report", data=report.yearly_pdf(int(year), rows, units.is_metric(load_settings().units)),
                           file_name=f"weather_report_{int(year)}.pdf", mime="application/pdf")


# ---------------------------------------------------------------- Import
def _import_flow(title: str, file_types: list[str], default_units: str, intro: str) -> None:
    s = load_settings()
    tz = _tz(s)
    st.markdown(theme.title_html(title), unsafe_allow_html=True)
    st.write(intro)
    up = st.file_uploader("File", type=file_types, key=f"{title}-file")
    if up is None:
        return
    try:
        headers, rows = importer.read_file(up.getvalue(), up.name)
    except importer.ImportProblem as exc:
        st.error(str(exc))
        return
    if not headers or not rows:
        st.error("The file has no rows to import.")
        return

    time_guess = importer.guess_time_column(headers)
    time_col = st.selectbox("Time column", headers,
                            index=headers.index(time_guess) if time_guess else 0, key=f"{title}-time")
    units = st.radio("Units in this file", ["Imperial (°F, mph, inHg, in)", "Metric (°C, km/h, hPa, mm)"],
                     index=0 if default_units == "imperial" else 1, horizontal=True, key=f"{title}-units")
    units_key = "metric" if units.startswith("Metric") else "imperial"

    guessed = importer.guess_mapping(headers, time_col)
    st.caption("Match each column to a reading. Choose Ignore to skip a column.")
    options = ["Ignore", *importer.READING_KEYS]
    mapping = {}
    for h in headers:
        if h == time_col:
            continue
        choice = st.selectbox(h, options, index=options.index(guessed.get(h, "Ignore")), key=f"{title}-map-{h}")
        if choice != "Ignore":
            mapping[h] = choice
    if not mapping:
        st.warning("Match at least one column to a reading.")
        return
    if len(set(mapping.values())) != len(mapping):
        st.error("Two columns are matched to the same reading. Change one of them to Ignore.")
        return

    try:
        readings = importer.build_readings(rows, time_col, mapping, tz, units_key)
    except importer.ImportProblem as exc:
        st.error(str(exc))
        return
    first = datetime.fromtimestamp(min(ts for ts, _ in readings), tz)
    last = datetime.fromtimestamp(max(ts for ts, _ in readings), tz)
    st.write(f"Found {len(readings)} readings from {first:%b %d, %Y} to {last:%b %d, %Y}.")
    if st.button("Import readings", key=f"{title}-go"):
        with st.spinner("Importing and rebuilding daily summaries..."):
            result = importer.store(storage.connect(), readings, s.latitude or 0.0, s.longitude or 0.0,
                                    s.elevation_m, tz)
        st.success(f"Imported {result['inserted']} readings across {result['days']} days. "
                   f"{result['skipped']} were already stored.")


def csv_import_page() -> None:
    _import_flow("CSV Import", ["csv"], "imperial",
                 "Upload a CSV file of past readings. Columns are matched to readings automatically. "
                 "Check the matches, then import. Only the file you choose is read.")


def excel_import_page() -> None:
    _import_flow("Excel Import", ["xlsx"], "imperial",
                 "Upload an Excel (.xlsx) file of past readings. The first sheet is used. "
                 "Columns are matched automatically. Check the matches, then import.")


def weather_underground_page() -> None:
    _import_flow("Weather Underground", ["csv"], "imperial",
                 "Upload a history CSV downloaded from Weather Underground. Its column names are matched "
                 "automatically, and its units are imperial by default.")


# ---------------------------------------------------------------- Export
def _backups_section(s: Settings) -> None:
    """Daily database backups: the on/off setting, how many copies are kept, and a button to back up now."""
    folder = backup.folder_for(storage.db_path())
    st.markdown(theme.section_html("Database backups"), unsafe_allow_html=True)
    enabled = st.checkbox("Back up the database once a day", value=s.backup_enabled, key="backup_on")
    keep = int(st.number_input("Backups to keep", min_value=1, max_value=365, value=int(s.backup_keep), step=1,
                               key="backup_keep"))
    if enabled != s.backup_enabled or keep != s.backup_keep:
        save_settings(replace(s, backup_enabled=enabled, backup_keep=keep))
    copy_to = st.text_input("Also copy each backup to this folder (optional)", value=s.backup_copy_folder,
                            key="backup_copy", help="For example a USB drive or a synced cloud folder.")
    if copy_to.strip() != s.backup_copy_folder.strip():
        save_settings(replace(s, backup_copy_folder=copy_to.strip()))
    error = start_poller().status.backup_error
    if error:
        st.warning(error)
    items = backup.backups(folder)
    if items:
        newest = datetime.fromtimestamp(items[-1].stat().st_mtime)
        st.caption(f"{len(items)} kept. Newest: {newest:%b %d, %Y %H:%M}. Saved in {folder}.")
    else:
        st.caption(f"No backups yet. They are saved in {folder}.")
    if st.button("Back up now"):
        path = backup.make_backup(storage.db_path(), folder, datetime.now())
        backup.prune(folder, keep)
        try:
            backup.copy_to_folder(path, copy_to, keep)
        except OSError as exc:
            st.warning(f"Couldn't copy the backup to that folder: {exc}")
        st.success(f"Saved {path.name}.")
    if items:
        pick = st.selectbox("Backup to restore", list(reversed(items)), format_func=lambda p: p.name, key="restore_pick")
        sure = st.checkbox("Replace the current data with this backup", key="restore_sure")
        if st.button("Restore", disabled=not sure):
            try:
                safety = backup.restore(pick, storage.db_path(), folder, datetime.now())
            except (OSError, sqlite3.Error) as exc:
                st.error(f"Couldn't restore: {exc}")
            else:
                st.success(f"Restored {pick.name}. The data from before the restore is saved as {safety.name}. "
                           "Restart Weather Lab so every page shows the restored data.")


def _daily_export(db, today: date) -> None:
    """Download one row per day: the highs, lows, rain, wind and sun for the range you choose."""
    st.markdown(theme.section_html("Daily summaries as a spreadsheet file"), unsafe_allow_html=True)
    st.caption("Values are in US units: degrees Fahrenheit, inches, miles per hour, miles and hours.")
    start = st.date_input("Daily summaries from", value=today - timedelta(days=365), max_value=today, key="daily_csv_from")
    end = st.date_input("Daily summaries to", value=today - timedelta(days=1), max_value=today, key="daily_csv_to")
    if end < start:
        st.error("The end date is before the start date.")
        return
    rows = history.daily_between(db, start, end)
    if not rows:
        empty_card("No daily summaries in that range")
        return
    st.download_button("Download daily summaries (CSV)", data=history.daily_csv(rows),
                       file_name=f"weather_daily_{start.isoformat()}_{end.isoformat()}.csv", mime="text/csv")


MONTH_NAMES = [datetime(2000, m, 1).strftime("%B") for m in range(1, 13)]


@st.cache_data(ttl=600, show_spinner=False)
def _all_history(tz_name: str, today: date) -> dict:
    """Every reading and daily summary as CSV. Kept for ten minutes, because the full history is large."""
    db = storage.connect()
    tz = ZoneInfo(tz_name)
    readings = storage.readings_between(db, 0.0, exports.day_start(today + timedelta(days=1), tz))
    daily = history.daily_between(db, date(2000, 1, 1), today - timedelta(days=1))
    return {"readings": importer.export_csv(readings, tz) if readings else None, "readings_count": len(readings),
            "daily": history.daily_csv(daily) if daily else None, "daily_count": len(daily)}


def _all_history_section(s: Settings, today: date) -> None:
    files = _all_history(_tz(s).key, today)
    st.caption("Everything the station has collected. The files are rebuilt at most every ten minutes.")
    if not files["readings_count"] and not files["daily_count"]:
        empty_card("No readings yet", "Readings appear here once the station has reported.")
        return
    left, right = st.columns(2)
    if files["readings"]:
        left.download_button("Download all readings (CSV)", data=files["readings"],
                             file_name=f"weather_readings_all_{today.isoformat()}.csv", mime="text/csv")
    if files["daily"]:
        right.download_button("Download all daily summaries (CSV)", data=files["daily"],
                              file_name=f"weather_daily_all_{today.isoformat()}.csv", mime="text/csv")


def _size_text(data) -> str:
    """A file size for a download button, such as 6.2 MB."""
    size = len(data.encode("utf-8")) if isinstance(data, str) else len(data)
    return f"{size / 1_000_000:.1f} MB" if size >= 1_000_000 else f"{max(size, 1) / 1000:.0f} KB"


def _monthly_section(db, tz: ZoneInfo, today: date) -> None:
    latest = storage.latest(db)
    # Open on the month of the newest reading, so the usual download is one click away.
    newest = datetime.fromtimestamp(latest[0], tz).date() if latest else today
    years = list(range(today.year, today.year - 10, -1))
    year_col, month_col = st.columns(2)
    year = int(year_col.selectbox("Year", years, index=years.index(newest.year) if newest.year in years else 0,
                                  key="export_year"))
    month = int(month_col.selectbox("Month", range(1, 13), index=newest.month - 1,
                                    format_func=lambda m: MONTH_NAMES[m - 1], key="export_month"))
    first, last = exports.month_bounds(year, month)
    if first > today:
        empty_card("That month hasn't started yet.")
        return
    readings = storage.readings_between(db, *exports.day_range_ts(first, last, tz))
    daily = history.daily_between(db, first, min(last, today - timedelta(days=1)))
    label = f"{MONTH_NAMES[month - 1]} {year}"
    if not readings and not daily:
        empty_card(f"No data for {label}", "Pick another month, or check that the station was reporting then.")
        return
    left, right = st.columns(2)
    if readings:
        csv = importer.export_csv(readings, tz)
        left.download_button(f"Readings for {label} (CSV) · {len(readings):,} rows · {_size_text(csv)}", data=csv,
                             file_name=f"weather_readings_{year}_{month:02d}.csv", mime="text/csv")
    if daily:
        csv = history.daily_csv(daily)
        right.download_button(f"Daily summaries for {label} (CSV) · {len(daily):,} days · {_size_text(csv)}", data=csv,
                              file_name=f"weather_daily_{year}_{month:02d}.csv", mime="text/csv")


def _readings_export(db, tz: ZoneInfo, today: date) -> None:
    """Download readings for a date range, in the same format the CSV Import page reads."""
    st.markdown(theme.section_html("Readings as CSV"), unsafe_allow_html=True)
    st.write("Download readings as a CSV file. It uses the same format as the CSV Import page, so you can "
             "import it on another computer. Times are in the timezone on the Setup page.")
    start = st.date_input("From", value=today - timedelta(days=30), max_value=today)
    end = st.date_input("To", value=today, max_value=today)
    if end < start:
        st.error("The end date is before the start date.")
        return
    rows = storage.readings_between(db, *exports.day_range_ts(start, end, tz))
    if not rows:
        empty_card("No readings in that range", "Try a wider range, or check that the station has been reporting.")
        return
    st.write(f"{len(rows)} readings ready.")
    st.download_button("Download CSV", data=importer.export_csv(rows, tz),
                       file_name=f"weather_readings_{start.isoformat()}_{end.isoformat()}.csv", mime="text/csv")


def export_page() -> None:
    s = load_settings()
    tz = _tz(s)
    db = storage.connect()
    today = datetime.now(tz).date()
    st.markdown(theme.title_html("Export"), unsafe_allow_html=True)
    st.write("Download your readings and daily summaries as CSV files. Values are in US units. "
             "Times use the timezone on the Setup page.")
    with st.expander("Download all history"):
        _all_history_section(s, today)
    with st.expander("Download by month", expanded=True):
        _monthly_section(db, tz, today)
    with st.expander("Download a custom range"):
        _daily_export(db, today)
        st.divider()
        _readings_export(db, tz, today)
    with st.expander("Database backups"):
        _backups_section(s)
    with st.expander("Old readings"):
        _archive_section(s)


def _archive_section(s: Settings) -> None:
    """Move raw readings older than a chosen age into an archive table. Nothing is deleted."""
    st.write("The station sends a reading every few seconds, so the database grows over time. Readings older than the "
             "number of days below move to an archive table in the same database. Nothing is deleted, and charts, "
             "reports and exports still include them.")
    days = int(st.number_input("Move readings older than (days, 0 keeps them all)", min_value=0, max_value=3650,
                               value=int(s.archive_after_days), step=1, key="archive_days",
                               help="At least the last 7 days always stay raw, so recent summaries can be rebuilt."))
    if days != s.archive_after_days:
        save_settings(replace(s, archive_after_days=days))
    error = start_poller().status.archive_error
    if error:
        st.warning(error)
    if days == 0:
        st.caption("Off. Every reading stays in the main table.")


# ---------------------------------------------------------------- Ecowitt export import
def ecowitt_import_page() -> None:
    db = storage.connect()
    st.markdown(theme.title_html("Ecowitt export"), unsafe_allow_html=True)
    st.write("Upload one or more history exports from ecowitt.net (.xlsx): daily, 5-minute or 4-hour. Only days Weather "
             "Lab doesn't have yet are added; days already stored are never changed. The values must be in US units "
             "(°F, mph, inches).")
    up = st.file_uploader("File", type=["xlsx"], key="ecowitt-file", accept_multiple_files=True)
    if not up:
        return
    try:
        days = ecowitt_import.days_from_files([io.BytesIO(f.getvalue()) for f in up])
    except ValueError as exc:
        st.error(str(exc))
        return
    except Exception:
        st.error("Couldn't read that file. Export the daily history from ecowitt.net as an .xlsx file.")
        return
    stored = {day for day, _ in history.all_daily(db)}
    new = sorted(day for day in days if day not in stored)
    st.write(f"The file has {len(days)} days, from {min(days):%b %d, %Y} to {max(days):%b %d, %Y}. "
             f"{len(new)} are new and {len(days) - len(new)} are already stored.")
    estimated = sum(1 for day in new if days[day].get("estimated"))
    if estimated:
        st.caption(f"{estimated} of the new days are estimates from 4-hour readings. A high or a low can fall between "
                   "readings, so those values can be a few degrees off.")
    if new and st.button(f"Import {len(new)} days", key="ecowitt-go"):
        with st.spinner("Importing..."):
            added = ecowitt_import.store_days(db, {day: days[day] for day in new})
        st.success(f"Added {added} days. They show on the Daily and Records pages.")


def noaa_page() -> None:
    """Daily rain and temperatures from NOAA's nearest station, for years before this app collected data."""
    s = load_settings()
    db = storage.connect()
    st.markdown(theme.title_html("NOAA history"), unsafe_allow_html=True)
    st.write("NOAA keeps daily rain and temperatures for many weather stations, going back decades. Weather Lab can fetch "
             "the nearest station's last 10 years. They show on the Explore page, in the year totals, beside your own "
             "readings. NOAA needs a free token from its Climate Data Online website.")
    token = noaa.token()
    with st.form("noaa-token"):
        typed = st.text_input("NOAA token", type="password",
                              placeholder="Saved in Windows Credential Manager" if token else "Paste your token")
        if st.form_submit_button("Save token") and typed.strip():
            secrets.set_key(noaa.TOKEN_KEY, typed.strip())
            st.rerun()
    if not token:
        st.caption("Get a free token from the Climate Data Online website, then paste it here.")
        return
    if s.noaa_station:
        st.caption(f"Nearest station: {s.noaa_station_name} ({s.noaa_station})")
    count, first, last = storage.noaa_summary(db)
    if count:
        st.caption(f"Stored: {count:,} days, from {first} to {last}.")
    if st.button("Find the nearest station"):
        if s.latitude is None or s.longitude is None:
            st.warning("Set your latitude and longitude on the Setup page first.")
        else:
            try:
                found = noaa.find_station(s.latitude, s.longitude, token)
            except noaa.NoaaError as exc:
                st.error(str(exc))
                found = None
            if found is None:
                st.warning("NOAA has no daily station within about 55 km of your location.")
            else:
                save_settings(replace(s, noaa_station=found[0], noaa_station_name=found[1]))
                st.success(f"Nearest station: {found[1]}, about {found[2]:.0f} km away.")
    if s.noaa_station and st.button("Fetch the last 10 years"):
        today = date.today()
        with st.spinner("Fetching from NOAA. This can take a minute."):
            try:
                days = noaa.fetch_daily(s.noaa_station, date(today.year - 10, 1, 1), today - timedelta(days=1), token)
            except noaa.NoaaError as exc:
                st.error(str(exc))
            else:
                storage.store_noaa_days(db, days)
                st.success(f"Stored {len(days):,} days from NOAA.")


def _import_page() -> None:
    pages = {"CSV": csv_import_page, "Excel": excel_import_page,
             "Weather Underground": weather_underground_page,
             "Ecowitt export": ecowitt_import_page, "NOAA history": noaa_page}
    source = st.radio("Import from", list(pages), horizontal=True)
    pages[source]()
