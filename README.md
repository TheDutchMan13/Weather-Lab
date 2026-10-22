# Weather Lab

A Windows weather dashboard for the Ecowitt GW2000 station. It reads your station on your home network, keeps its own history, and shows live readings, daily and historical charts, records, sensor health, forecasts, alerts, air quality, lightning, comfort indexes, fire weather, and a daily PDF report.

## What you need

- Windows 11
- An Ecowitt GW2000 (or a compatible gateway) on the same network as your PC
- Your station's IP address (shown on the gateway's web page or in your router's device list)
- Your latitude and longitude (optional, for sun hours, forecasts, and air quality)

## Install

1. Go to the [Releases page](https://github.com/TheDutchMan13/weather-lab/releases) and download the newest `WeatherLabSetup-x.y.z.exe`.
2. Run it. Windows may warn that the app is from an unknown publisher. Click **More info**, then **Run anyway**. The app is not code-signed yet.
3. Weather Lab opens when setup finishes. Use the **Setup** page to finish the steps below.

## First-time setup

On the **Setup** page:

1. Enter the station's IP address.
2. Choose your timezone, and enter your latitude, longitude, and elevation.
3. Choose which readings appear on the **Live** page.
4. Optional, on the **Air** tab: paste a free **AirNow** API key for air quality. It is stored in Windows Credential Manager, not in a file. If lightning distances look too small, turn on the kilometres switch there.
5. Optional: turn on **Start Weather Lab when I sign in to Windows**. It is under **Settings > Startup**.
6. Optional, on the **Uploads** tab: turn on **CWOP**. This sends your readings to the public Citizen Weather Observer Program, and your station's location becomes public. It is off by default.
7. Optional, on the **Uploads** tab: turn on **Weather Underground**, with your station ID and key from wunderground.com. The key is stored in Windows Credential Manager. It is off by default.
8. Optional, on the **Uploads** tab: turn on **PWSweather** or **Weathercloud**, with the station ID and key from each account. Each key is stored in Windows Credential Manager. Both are off by default.
9. Optional, on the **Uploads** tab: for **Home Assistant**, turn on MQTT. Enter the broker address (for example, the Mosquitto add-on's address on your network), and the username and password if the broker needs them. Home Assistant then finds the sensors by itself. The password is stored in Windows Credential Manager. The connection isn't encrypted, so use it on your local network only.
10. Click **Save**. The bar at the bottom of the Setup page shows how many changes are waiting.

The Live page starts filling in within a minute. History builds up from the time the app starts collecting data, so charts and records grow over the first few days.

## Stations

If you run more than one station, open **Configure > Stations** and add each one by name. Each station keeps its own readings, settings, alerts and backups. Pick the station in the sidebar; the picker appears once a second station exists. A new station starts with default settings, so set its IP address and location on its **Setup** page. Removing a station stops its collection but keeps its folder. Adding a station with the same name again brings its readings back.

## Updates

Weather Lab can check for new versions and install them. Open **Settings > Updates**, paste this address, and click **Check for updates**:

    https://github.com/TheDutchMan13/weather-lab/releases/latest/download/latest.json

Each download is checked against a published checksum before the installer runs. The update check needs the repository to be public, because GitHub doesn't allow anonymous downloads of release files from a private repository.

## Pages

The sidebar groups the pages into seven sections: Now, History, Explore, Outlook, Hazards, Data and Configure.

- **Now:** **Live** (current readings with heat index, wind chill, and humidex when they apply), **Sensors** (how complete the readings are, and any gaps), and **Alert history**.
- **History:** **Daily** (one day's summary, with a PDF report download), **History** (rain totals and daily charts), **Records** (highs and lows since the app started collecting data), **Coverage**, **Rankings**, **Rewind**, **Climate charts**, and **My year**.
- **Explore:** **Rain calendar**, **Rain events**, **Ask**, **Unusual days**, and **Replay**.
- **Outlook:** **Forecast** (NWS alerts, an Overview of the next 24 hours with rain streaks when rain is likely, and the next 7 days with rain chance and wind; United States only), **Heat**, **Wind**, **Wind map** (arrows across the area around the station, for now and up to 12 hours ahead), **Sun**, and **Astronomy**.
- **Hazards:** **Air** (AirNow air quality; needs a key and a location), **Fire** (Canadian Fire Weather Index and forecast; United States forecast only), **Lightning** (recent strikes), **Tropics**, and **Radar**.
- **Data:** **Import** (including **NOAA history**, which needs a free NOAA Climate Data Online token), **Export** (downloads of readings and daily summaries, plus the database backups, and an **Old readings** section that moves raw readings to an archive table without deleting them), and **Reports** (monthly and yearly PDF reports, which can be made automatically).
- **Configure:** **Setup**, **Settings**, **Stations**, **Status**, **Health check**, and **What's New**.

## Phone and other devices

On the **Setup** page, open the **Access** tab and turn on "Let phones and other devices on my home network open Weather Lab", then restart Weather Lab. Open the address shown on Setup from a phone on the same Wi-Fi. Other devices must sign in with the password you set on Setup. Only turn this on for a network you trust. If Windows asks about the firewall, allow Private networks.

## Where your data lives

The first station's settings and history are stored in `%APPDATA%\WeatherLab`. Other stations are in `%APPDATA%\WeatherLab\stations\<name>`. Uninstalling Weather Lab removes the program and its start-on-login entry, but keeps these folders. Delete them yourself if you want to remove your history.

## Troubleshooting

- **"Can't reach the station":** check the IP address on the Setup page, and make sure the PC and the gateway are on the same network.
- **Nothing on the Live page:** the reader needs a minute after you save the IP address.
- **Lightning distances look too small:** some firmware labels kilometres as miles. Turn on the kilometres switch on the Setup page, under **Air**.
- **Forecast or fire weather says it's unavailable:** the National Weather Service covers the United States only.
- **NOAA history says the token was refused:** get a new token from NOAA Climate Data Online, and paste it on the Import page's NOAA history tab. The token is saved in Windows Credential Manager, not in the settings file.

## For developers

Run from source (PowerShell, in the project folder):

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    streamlit run app.py

Run the tests:

    python -m unittest discover -s tests -t .

Build the app and installer (activate `.venv` first):

    python build_exe.py
    python build_installer.py

`build_installer.py` needs Inno Setup 6 (free, from jrsoftware.org). It writes `installer\WeatherLabSetup-<version>.exe` and `installer\latest.json`, which the update check reads. `rebuild.bat` runs the tests and both build steps.

### Publishing a release

1. Set `APP_VERSION` in `weatherlab/config.py` and the matching `AppVersion` in `installer.iss`. Add a What's New entry in `weatherlab/whats_new.py`.
2. Commit and push to `main`. GitHub Actions runs the tests, builds the installer and publishes a release tagged with the new version, with `latest.json`. Pushes that don't change the version do nothing.
3. Pushing a tag by hand, such as `git tag v0.18.0` and `git push origin v0.18.0`, publishes that version too. The tag must match `APP_VERSION`, or the build stops.

To build without publishing, run the **Release** workflow by hand from the Actions tab and download the installer from the run.

Project layout: `app.py` (sidebar and start-up), `weatherlab/screens/` (the pages, one module for each sidebar section), `launcher.py` (desktop window), `weatherlab/` (readers, storage, and calculations), `tests/` (including `static_check.py`, which checks names and imports without running Streamlit), `.github/workflows/` (release build). `SOURCES.md` lists every piece copied from the author's dashboard. `PLAN.md` tracks the phases.

## How it was made

Weather Lab was built with help from Claude, an AI assistant made by Anthropic, working in Claude Code. The author chose the features, directed the work, and tested each release on their own station and PC. The code is reviewed through the tests and the release checks in this repository.

## License

MIT. See `LICENSE`.
