"""What's New in Weather Lab: newest first. Add an entry each time a feature ships.

The first entry's version must match APP_VERSION in config.py (tests/test_whats_new.py checks it).
"""

ENTRIES = [
    {
        "version": "0.22.6",
        "date": "October 22, 2026",
        "items": [
            "Each day now records its heat index, the highest feels-like heat from the day's readings. Records has a Highest heat index record in Temperature.",
            "Highest heat index replaces Highest UV among the six record highlights.",
            "Days from before this update are filled in automatically, 60 days every 5 minutes, from the readings already stored.",
        ],
    },
    {
        "version": "0.22.5",
        "date": "October 22, 2026",
        "items": [
            "Records has a new look: six record highlights on a gradient card, then every record grouped into Temperature, Rain, Wind, and Humidity and pressure.",
            "Each record shows its date, or how long a dry or wet spell lasted and when it ended. Records set in the last 30 days are marked NEW.",
            "Wettest month and the longest dry and wet spells are now records too. The current month is left out of the wettest month until it ends.",
        ],
    },
    {
        "version": "0.22.4",
        "date": "October 22, 2026",
        "items": [
            "Live: each Last 24 hours tile has a History button. It opens a window with the reading's chart over 24 hours, 7 days or 30 days, and its highest, lowest and average.",
            "The Feels like and Pressure dials on Live have History buttons too.",
            "The history window stays open while the Live page refreshes, and closes when you close it.",
        ],
    },
    {
        "version": "0.22.3",
        "date": "October 22, 2026",
        "items": [
            "The app uses the dashboard's colours: one accent blue for buttons, tabs and links, and one colour per measure on every chart.",
            "Temperature is amber, rain is violet, wind, humidity and UV are quiet grey-blue, gusts are green and dashed, pressure is gold, and dew point is teal.",
            "Charts with several series start violet, then green and amber, as on the dashboard.",
        ],
    },
    {
        "version": "0.22.2",
        "date": "October 22, 2026",
        "items": [
            "What's New shows each version as a card, and marks the latest one.",
            "Every page with nothing to show yet uses the same card: what is missing, and why.",
            "Section headings look the same on every page.",
            "Removing an alert rule, the phone topic, the password or a station asks you to confirm first.",
            "Clearing a saved key is marked on the page and only happens when you press Save. Keep the key undoes the mark.",
        ],
    },
    {
        "version": "0.22.1",
        "date": "October 22, 2026",
        "items": [
            "Wind map has a Your station card: the station's wind now, its gusts, and the strongest wind in the area for the time you picked.",
            "Live shows the nearest airport's readings as tiles, after the comparison with yesterday and the dew point.",
            "Alert rules on Setup are in clear sections. A second condition and the time settings sit in their own expanders.",
            "Health check results are grouped: Station, Storage, Alerts and reports, Online services, and This app.",
        ],
    },
    {
        "version": "0.22.0",
        "date": "October 22, 2026",
        "items": [
            "Alert rules can check more than one thing: for example, temperature at or above 105 and humidity at or below 20, both at once, or either one.",
            "Alert rules can run only in the daytime, only at night, or only in the months you pick.",
            "An alert rule can escalate: a Notice at first, a Warning after an hour, and Severe after three hours, repeated every three hours while it lasts.",
            "New alerts for falling pressure (in inches of mercury or millibars per hour) and falling temperature (per hour), over the last hour.",
            "Setup can send National Weather Service warnings and advisories to your phone and PC. Only new ones are sent, and US locations only.",
            "Reports can be made automatically: a monthly PDF on the second day of each month, and a yearly PDF in January.",
            "Export has an Old readings section. Raw readings older than the number of days you choose move to an archive table. Nothing is deleted, and charts and daily totals still see them.",
            "Import has a NOAA history page. Paste a free NOAA token, find the nearest station, and fetch up to ten years of rain and temperatures. Explore's year totals show the NOAA rain too.",
            "Outlook has a Wind map: arrows across the area around your station, coloured by speed, for now, +3, +6 or +12 hours.",
            "Live shows the latest reading from the nearest airport, or the nearest weather station if no airport is close. US locations only.",
            "Health check has new lines for weather warnings, automatic reports and the reading archive when they are turned on.",
        ],
    },
    {
        "version": "0.21.0",
        "date": "October 22, 2026",
        "items": [
            "Health check shows a coloured dot with its word for each result, such as OK or Problem, instead of an emoji.",
            "Every table in Weather Lab has the same look: a tinted header, thin rules and numbers aligned right.",
            "Setup's Station tab has two parts: Where the station is, and Forecast requests.",
            "Setup's tabs have shorter names: Station, Air, Uploads and Access.",
            "Setup has shorter notes, and an About this page section at the bottom says where your changes are saved.",
            "Stations shows Yes in the Showing now column, instead of a tick.",
            "Settings, Alerts: More notices is now Other warnings.",
        ],
    },
    {
        "version": "0.20.0",
        "date": "October 22, 2026",
        "items": [
            "Setup has a save bar at the bottom of the page. It stays in view and shows how many changes are waiting.",
            "Live shows a line under the title: whether the station is reporting, and when its last reading came in.",
            "Health check opens with counts of OK, check, problem and info results.",
            "Section headings look the same on every page.",
            "Phone alerts is now titled Phone notifications with the ntfy app, so the name is explained where it appears.",
        ],
    },
    {
        "version": "0.19.0",
        "date": "October 21, 2026",
        "items": [
            "The last sidebar section is now Configure: Setup, Settings, Stations, Status, Health check and What's New.",
            "Pages use simple line icons instead of emoji, so they line up and follow the theme.",
            "Setup, Uploads: each service is a card whose header shows its status, such as On, last sent 16:12:04. Open a card to change its settings.",
            "Network access is now Phone and device access, on Setup and in Health check.",
            "Export: each monthly download shows its row count and file size, and the month picker opens on the latest month with readings.",
            "Pages with no data yet show the same card, with what is missing and, where it is known, when it fills in.",
        ],
    },
    {
        "version": "0.18.0",
        "date": "October 21, 2026",
        "items": [
            "The sidebar is grouped into seven sections: Now, History, Explore, Outlook, Hazards, Data and System. Each page is in one place.",
            "Setup has four tabs: Station, Air and lightning, Uploads and Network access. CWOP, Weather Underground, PWSweather, Weathercloud and Home Assistant are all under Uploads. Phone access is now Network access.",
            "Database backups moved from Settings to Export, next to the downloads. Settings now has Appearance, Alerts, Phone alerts, Updates and Startup.",
        ],
    },
    {
        "version": "0.17.1",
        "date": "October 21, 2026",
        "items": [
            "The installer shows the Weather Lab logo: the setup icon, the side panel and the corner image.",
        ],
    },
    {
        "version": "0.17.0",
        "date": "October 21, 2026",
        "items": [
            "Export page: downloads are grouped into dropdowns. Download all history gives every reading and daily summary in one file each.",
            "Download by month: pick a year and month to download that month's readings or daily summaries. Custom range is still there, in its own dropdown.",
        ],
    },
    {
        "version": "0.16.0",
        "date": "October 21, 2026",
        "items": [
            "Home Assistant over MQTT: publish each reading to your MQTT broker once a minute, such as the Mosquitto add-on in Home Assistant. Set it up under Setup, Other services.",
            "Home Assistant finds the sensors by itself. Weather Lab sends discovery messages once an hour, and the broker password is kept in Windows Credential Manager.",
        ],
    },
    {
        "version": "0.15.0",
        "date": "October 21, 2026",
        "items": [
            "Other upload services: send your readings to PWSweather or Weathercloud every five minutes, each off by default. Set them up under Setup, Other services.",
            "Like Weather Underground, each key is kept in Windows Credential Manager, and upload problems show on the Setup page and in the health check.",
        ],
    },
    {
        "version": "0.14.0",
        "date": "October 21, 2026",
        "items": [
            "Weather Underground upload: send your readings to Weather Underground every five minutes, as CWOP does. Turn it on under Setup, Weather Underground, with your station ID and key from wunderground.com.",
            "The Weather Underground key is kept in Windows Credential Manager, not in a file. Upload problems show on the Setup page and in the health check.",
        ],
    },
    {
        "version": "0.13.0",
        "date": "October 21, 2026",
        "items": [
            "Forecast page redesigned: an Overview of the next 24 hours, one column every two hours, with the sky, temperature, rain chance, sunrise and sunset, and the moon phase.",
            "Rain falls over the hours with a rain chance of 40% or more. The rain stops moving when your device asks for less motion.",
            "Next 7 days: each day shows its rain chance, its low and high on a temperature bar, and the wind. Wind is in km/h when you use metric.",
        ],
    },
    {
        "version": "0.12.0",
        "date": "October 21, 2026",
        "items": [
            "Stations: add a second weather station under Data and setup, Stations. Each station keeps its own readings, settings, alerts, phone topic and backups.",
            "Pick the station in the sidebar. It appears once you have added a second one. Each new station needs its own Ecowitt address and location under Setup and Settings.",
        ],
    },
    {
        "version": "0.11.0",
        "date": "October 21, 2026",
        "items": [
            "Updates tab under Settings: check for a newer version and download and install it in one step. The installer is checked against a published checksum before it runs.",
            "Phone alerts through the free ntfy app, so alerts reach your phone when you're away from home. Set it up under Settings, Phone alerts.",
            "Away from home over Tailscale: Setup shows your Tailscale address once Tailscale is running. Phone access must be on.",
        ],
    },
    {
        "version": "0.10.0",
        "date": "October 21, 2026",
        "items": [
            "Lightning history on the Lightning page: strikes per day and how close the closest one was, over 30 days or a year.",
            "Health check page under Now: one list showing whether the collector, database, disk space, backups, notifications and settings are working.",
            "Larger text under Settings, Appearance, for bigger text and tiles.",
            "Always show the chart buttons under Settings, Appearance. The camera button saves any chart as a PNG picture.",
        ],
    },
    {
        "version": "0.9.0",
        "date": "October 21, 2026",
        "items": [
            "Metric or US units now apply to every page, chart, alert and PDF report. Choose them under Settings, Appearance.",
            "Alert rules, record alerts and the freeze warning are entered in the chosen units and stored in US units.",
            "Export and import files stay in US units, and the Ask page reads questions in °F.",
        ],
    },
    {
        "version": "0.8.0",
        "date": "October 21, 2026",
        "items": [
            "New Settings page under Data and setup: Appearance, Alerts, Backups and Startup now live there.",
            "Setup keeps the station address, location, AirNow key, CWOP and phone access.",
            "Live readings can be chosen under Appearance on the Settings page.",
        ],
    },
    {
        "version": "0.7.0",
        "date": "October 21, 2026",
        "items": [
            "Ask under History: type a question such as wettest month, warmest day, or rain in March 2026, and get the answer from your stored history.",
            "Unusual days under History: days from the last year whose high or low was 10 °F or more from usual for that date, or that had an inch or more of rain.",
            "Dew point line on Live: how muggy it feels, in plain words.",
        ],
    },
    {
        "version": "0.6.0",
        "date": "October 21, 2026",
        "items": [
            "Alert history under Now: every notification is saved in a list you can search.",
            "UV, air quality and fire danger notices, once a day each. Off by default; turn them on under Alerts on Setup.",
            "Rain started and stopped notices. Off by default.",
            "Live page shows today so far compared with yesterday at the same time: high, rain and gust.",
            "Rain chance check on the Forecast page: how often rain was forecast, and how often it fell.",
            "Copy each backup to a second folder, such as a USB drive or synced folder, on Export.",
            "Version check: give Weather Lab an address and it shows when a newer version is available. Nothing is installed automatically.",
        ],
    },
    {
        "version": "0.5.0",
        "date": "October 21, 2026",
        "items": [
            "Quiet hours under Notifications on Setup: sensor warnings, stuck-sensor warnings and the morning summary wait until quiet hours end. Offline, freeze and lightning notices still sound.",
            "Stuck sensor warning: outdoor temperature or humidity that has not changed for 3 hours.",
            "Lightning notice when a strike is within the distance you choose (off by default).",
            "Find or test the station under Setup: test the connection, or look for the station on your network.",
            "Hot days by year on Records: days at or above 100 °F and 110 °F.",
            "Daily summaries download as a spreadsheet file (CSV) on Export.",
        ],
    },
    {
        "version": "0.4.0",
        "date": "October 21, 2026",
        "items": [
            "Station offline alert: one notification if the station sends no reading for 15 minutes, and one when it is back. Turn it off under Notifications on Setup.",
            "Freeze warning: one notification per night when the forecast low is at or below your threshold (36 °F by default), so you can cover plants.",
            "Rain events page under History: each rain shown as a separate shower, with its start, length, amount and peak rate.",
            "Daily page compares the day with the 7 days around the same date in earlier years, when there are at least two other years of data.",
        ],
    },
    {
        "version": "0.3.0",
        "date": "October 21, 2026",
        "items": [
            "Restore a backup on the Export page. The data from before the restore is saved as a copy first.",
            "Warnings when a wireless sensor's battery is low or its signal is weak. Each warning is sent once a day.",
            "A morning notification with yesterday's high, low, rain and sun. Turn it off or change the hour under Notifications on Setup.",
            "A test notification button on Setup.",
            "Forecast accuracy on the Forecast page: how far off the forecast highs have been.",
            "Skipped readings are listed on Status.",
            "A year-over-year chart of daily highs on Climate charts.",
            "On This Day on Records: the same date in earlier years.",
            "Add Weather Lab to a phone's home screen, with its own icon.",
        ],
    },
    {
        "version": "0.2.0",
        "date": "October 21, 2026",
        "items": [
            "New Coverage page under History: shows which days have exact summaries, which are estimates from 4-hour readings, and which are missing.",
            "Days built from 4-hour Ecowitt readings are marked as estimates on the Daily page, and records from them are tagged on the Records page.",
            "Database backups: Weather Lab copies its database once a day and keeps the newest 14 copies by default. Turn this on or off, change how many are kept, or back up now on the Export page.",
            "Compare two periods: History now has side-by-side totals and averages for two date ranges, with the change between them.",
            "Indoor temperature and humidity trend charts on History, when the station reports indoor readings.",
            "Ecowitt history import accepts exports with readings more often than once a day, not only daily rows.",
            "What's New: this page.",
        ],
    },
]
