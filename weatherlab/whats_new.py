"""What's New in Weather Lab: newest first. Add an entry each time a feature ships.

The first entry's version must match APP_VERSION in config.py (tests/test_whats_new.py checks it).
"""

ENTRIES = [
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
