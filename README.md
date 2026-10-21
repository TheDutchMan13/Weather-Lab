# Weather Lab

A Windows weather dashboard for the Ecowitt GW2000 station. It reads your station on your home network, keeps its own history, and shows live readings, daily and historical charts, records, sensor health, forecasts, alerts, air quality, lightning, comfort indexes, fire weather, and a daily PDF report.

## What you need

- Windows 11
- An Ecowitt GW2000 (or a compatible gateway) on the same network as your PC
- Your station's IP address (shown on the gateway's web page or in your router's device list)
- Your latitude and longitude (optional, for sun hours, forecasts, and air quality)

## Install

1. Download `WeatherLabSetup-0.12.0.exe` and run it.
2. Windows may warn that the app is from an unknown publisher. Click **More info**, then **Run anyway**. The app is not code-signed yet.
3. Weather Lab opens when setup finishes. Use the **Setup** page to finish the steps below.

## First-time setup

On the **Setup** page:

1. Enter the station's IP address.
2. Choose your timezone, and enter your latitude, longitude, and elevation.
3. Choose which readings appear on the **Live** page.
4. Optional: paste a free **AirNow** API key for air quality. It is stored in Windows Credential Manager, not in a file.
5. Optional: turn on **Start Weather Lab when I sign in to Windows**.
6. Optional: turn on **CWOP**. This sends your readings to the public Citizen Weather Observer Program, and your station's location becomes public. It is off by default.
7. Click **Save**.

The Live page starts filling in within a minute. History builds up from the time the app starts collecting data, so charts and records grow over the first few days.

## Pages

- **Live:** current readings with heat index, wind chill, and humidex when they apply
- **Daily:** one day's summary, with a PDF report download
- **History:** rain totals and daily charts
- **Records:** highs and lows since the app started collecting data
- **Forecast:** NWS alerts, a 7-day forecast, and an hourly chart (United States only)
- **Air:** AirNow air quality (needs a key and a location)
- **Lightning:** recent strikes. If distances look too small, turn on the kilometres switch on the Setup page.
- **Fire:** Canadian Fire Weather Index and forecast (United States forecast only)
- **Sensors:** how complete the readings are, and any gaps

## Phone and other devices

On the **Setup** page, turn on "Let phones and other devices on my home network open Weather Lab", then restart Weather Lab. Open the address shown on Setup from a phone on the same Wi-Fi. Other devices must sign in with the password you set on Setup. Only turn this on for a network you trust. If Windows asks about the firewall, allow Private networks.

## Where your data lives

Settings and history are stored in `%APPDATA%\WeatherLab`. Uninstalling Weather Lab removes the program and its start-on-login entry, but keeps this folder. Delete the folder yourself if you want to remove your history.

## Troubleshooting

- **"Can't reach the station":** check the IP address on the Setup page, and make sure the PC and the gateway are on the same network.
- **Nothing on the Live page:** the reader needs a minute after you save the IP address.
- **Lightning distances look too small:** some firmware labels kilometres as miles. Turn on the kilometres switch on the Setup page.
- **Forecast or fire weather says it's unavailable:** the National Weather Service covers the United States only.

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

`build_installer.py` needs Inno Setup 6 (free, from jrsoftware.org).

Project layout: `app.py` (pages), `launcher.py` (desktop window), `weatherlab/` (readers, storage, and calculations), `tests/`. `SOURCES.md` lists every piece copied from the author's dashboard. `PLAN.md` tracks the phases.
