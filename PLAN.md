# Weather Lab plan

A public, generic weather dashboard for the Ecowitt GW2000, built on Streamlit, with a Windows exe.

## Decisions

- **Dashboard:** Streamlit, the same stack as the AZ Weather Lab dashboard. Users can also open it from a phone or other browser on their network.
- **Windows exe:** PyInstaller starts the Streamlit server in the background and shows it in a pywebview window.
- **Installer:** Inno Setup, with start-on-login as an option.
- **Pollen:** dropped for now.
- **Sharing:** public. No personal files, keys, IPs, or paths in the code or the installer.
- **Prototype:** the PySide6 version is archived in `archive/pyside6-prototype/` and is not part of the project.

## Rules for copying from the dashboard

- The dashboard is never edited. Copy only, and log every copied file or section in `SOURCES.md`.
- Never copy personal files: `airnow_key.txt`, `noaa_token.txt`, `gw2000_ip.txt`, `cumulus_dir.txt`, `data_dir.txt`, `backup_extra_dir.txt`, `station_scan.txt`, `set_dashboard_password.py`, `reports/`, `app_guide/snapshot.txt`, the database, and backups.
- Replace every hardcoded location, path, station ID, and NWS grid point with a setting.
- Keys go in Windows Credential Manager, not in files.

## Phases

### Phase 1: Foundation (in progress)
- [x] Parser, unit conversion, and plausibility checks copied from the collector, with tests
- [x] Local SQLite storage in %APPDATA%
- [x] Background poller every 30 seconds
- [x] Setup page: station IP, timezone, and choice of Live readings
- [x] Live page with metric cards
- [ ] Check the Live page against a running station (needs the user)
- [ ] Start-on-login option
- [ ] Exe window with pywebview

### Phase 2: History (done)
- Daily and history charts
- Rain totals
- Records (highs and lows)

### Phase 3: Sensors and forecasts (done)
- Sensor health and gap detection
- NWS alerts and forecast (latitude and longitude only, no key)

### Phase 4: Extras (written; needs a run on the PC)
- [x] AirNow air quality (user's own key, stored in Credential Manager)
- [x] Fire weather index with NWS forecast (US only)
- [x] Lightning page with km switch
- [x] Comfort index tiles on Live
- [x] Daily PDF report download on the Daily page (monthly and yearly reports not yet)

### Phase 5: Sharing (in progress)
- [x] Optional CWOP upload (off by default, user's callsign, APRS-IS position weather report)
- [x] Installer built and tested on the PC (Inno Setup 7; per-user install, start-on-login entry removed on uninstall)
- [x] README for other users
- [x] Code signing: skipped for now. The app is unsigned, and the README explains the Windows warning.

## Status

- Phase 1: the core is written; the live station and exe have been checked by the user. Start-on-login still needs a sign-in test.
- Phase 2 and 3: checked by the user.
- Phase 4: done and checked on the PC (exe opens).
- Phase 5: CWOP, installer (built and tested), and README are done. Code signing skipped for now.
