"""What's New in Weather Lab: newest first. Add an entry each time a feature ships.

The first entry's version must match APP_VERSION in config.py (tests/test_whats_new.py checks it).
"""

ENTRIES = [
    {
        "version": "0.37.53",
        "date": "October 30, 2026",
        "items": [
            "The sidebar has a Jump to page box at the top. Type part of a page's name to go straight there.",
            "Pin the pages you use most: Pin at the bottom of the sidebar puts the open page in a Pinned list at the top, up to 8 pages. Unpin takes it off.",
            "Now, History, Weather, Storms and Station fold shut when you click their name, and stay that way until you open them again. The group of the page you're on always stays open.",
            "Settings has a Find a setting box. Pick a setting, such as quiet hours or the password, and its tab opens.",
            "Settings warns you when Station has unsaved changes, before you switch to App and alerts and lose them.",
            "Notices on Home say how long ago each alert went off, such as 12 min ago.",
        ],
    },
    {
        "version": "0.37.52",
        "date": "October 30, 2026",
        "items": [
            "Setup and Settings are one page now. Settings has a Station and App switch at the top: Station has the station address, location, air quality, uploads and access tabs that were on Setup, and App has appearance, alerts, phone alerts, updates and startup. Old links still open the right tab.",
        ],
    },
    {
        "version": "0.37.51",
        "date": "October 30, 2026",
        "items": [
            "The dew point card and the nearest airport's reading moved into More readings at the bottom of Home, closed until you open it.",
            "The notices strip has an All alerts link to Alert history, for alerts older than the last few hours.",
            "Home layout can show the right-now panel in one plain colour instead of the sky gradient.",
        ],
    },
    {
        "version": "0.37.50",
        "date": "October 30, 2026",
        "items": [
            "History has one Period control at the top: 7 days, 30 days, 90 days, 1 year or All. It sets how far back Records, Rankings, Coverage and Daily's several-days view look, so they always agree. Daily still has its one-day view with a date box. Compare, Month, Year and Rewind keep their own date and year pickers.",
        ],
    },
    {
        "version": "0.37.49",
        "date": "October 30, 2026",
        "items": [
            "A Getting started list on Home shows what is still worth setting up once your station is reporting: your location, phone alerts, a first backup and update checks. Each has a link to the right page, and Turn on starts update checks with the official releases. Items disappear as they are done; Hide this list removes it, and Home layout can show it again.",
        ],
    },
    {
        "version": "0.37.48",
        "date": "October 30, 2026",
        "items": [
            "When a newer Weather Lab is out, Home says so in a thin line at the top, with an Update link to Settings. It needs update checks on (Settings, Updates).",
        ],
    },
    {
        "version": "0.37.47",
        "date": "October 30, 2026",
        "items": [
            "Notices on Home sit in one strip under the reading right now, instead of yellow boxes above it. The strip says how many there are (for example 2 notices) and opens when you tap it. It opens by itself when the background reader has stopped or a weather warning is Severe or Extreme.",
            "The line under the temperature no longer ends with a stray dot when there is no sky description.",
        ],
    },
    {
        "version": "0.37.46",
        "date": "October 30, 2026",
        "items": [
            "The Android app can follow your Home layout. Its Live tab reads whether you show the briefing, the order of your cards and which are wide, from a new read-only address in the app's connection. It needs the Android app 0.7.23 or newer; older versions keep their own layout.",
        ],
    },
    {
        "version": "0.37.45",
        "date": "October 30, 2026",
        "items": [
            "The longer tables can be sorted. A Sort by box above Rankings, the daily table on History, Rain events, Unusual days and the records lists orders the rows by any column of numbers, times, lengths or dates, highest or lowest first. Rows with no value (--) always stay at the bottom.",
        ],
    },
    {
        "version": "0.37.44",
        "date": "October 30, 2026",
        "items": [
            "Each reading shows once on Home. Temperature, humidity and wind have their card in the Last 24 hours row, so they are no longer repeated below it or offered again in the Home layout. UV index is now a card under Air.",
            "The temperature ring, Feels like and Pressure are a group called Gauges, below the cards. On a phone it starts closed, so the readings come first. On the Home layout page you can set it to always open or always closed.",
            "The Compact sections switch is gone, replaced by the Gauges setting. The airport card moved to the bottom of Home.",
        ],
    },
    {
        "version": "0.37.43",
        "date": "October 30, 2026",
        "items": [
            "Humidity is shown once on Home, in the Last 24 hours row, instead of twice. It is no longer offered as a card in the Home layout.",
        ],
    },
    {
        "version": "0.37.42",
        "date": "October 30, 2026",
        "items": [
            "A Home layout page, under Station, replaces the Customize pop-up. Choose the readings on Home, put them in order, and make any card Small or Wide. A wide card has a row to itself. A preview shows how Air and Wind and rain will look.",
            "Customize on Home now opens the Home layout page.",
        ],
    },
    {
        "version": "0.37.41",
        "date": "October 30, 2026",
        "items": [
            "The dials on Home use the newer way Streamlit embeds panels. They look the same, size themselves to fit, and keep working when Streamlit drops the old way.",
        ],
    },
    {
        "version": "0.37.40",
        "date": "October 30, 2026",
        "items": [
            "The sidebar has five areas instead of eight: Now, History, Weather, Storms and Station. Every page is still there, and all of them show without a View more link. Forecast moved to Now, and Rain calendar, Rain events, Unusual days, Replay and Ask moved to History.",
            "Sensors, Status and Health check are now one Station health page. Pick Status, Sensors or Health check at the top; only the one you pick runs.",
        ],
    },
    {
        "version": "0.37.39",
        "date": "October 30, 2026",
        "items": [
            "Home opens with the reading right now at the top, so on a phone the temperature is the first thing you see. Today's briefing follows as one short card: the headline and a single line of numbers.",
            "The separate status line and the grey line of today against yesterday are gone from Home. The right-now panel already shows how fresh the reading is and today's high, low, rain and gust.",
        ],
    },
    {
        "version": "0.37.38",
        "date": "October 29, 2026",
        "items": [
            "The Customize button on Home looks like a normal button again. It had shrunk to a small round ring.",
        ],
    },
    {
        "version": "0.37.37",
        "date": "October 29, 2026",
        "items": [
            "The ? help marks are gone from every Weather Lab page, including the Air quality index, lightning and heat index tiles. The Android app keeps its ? marks.",
            "Live shows the station's status once, under the title, with the time of the last reading. The line at the bottom now shows only when the reader last tried and when it started.",
        ],
    },
    {
        "version": "0.37.36",
        "date": "October 29, 2026",
        "items": [
            "The wording for dew point (dry, muggy...), wind direction and UV level now comes from Weather Lab itself and is sent to the Android app, so both always say the same thing. A new word needs one change instead of two. The Android app needs this version or newer to show those words.",
        ],
    },
    {
        "version": "0.37.35",
        "date": "October 29, 2026",
        "items": [
            "All history is on one page. Rewind (the same date in earlier years) and Coverage (which days have a summary) join Daily, Records, Rankings, Compare, Month and Year as views at the top of History. They are no longer separate entries in the sidebar.",
            "Customize on Home can reorder your reading cards. Under Readings on Home, each card has an up and a down arrow. The order applies inside Air and inside Wind and rain.",
        ],
    },
    {
        "version": "0.37.34",
        "date": "October 29, 2026",
        "items": [
            "Compare stations (Now section): pick two of your stations and see them side by side. A sentence says which is warmer, a table shows temperature, feels like, humidity, wind, gust, pressure, rain and UV with the difference, and a chart draws both temperatures for the last 24 hours. It needs at least two stations, added under Stations.",
        ],
    },
    {
        "version": "0.37.33",
        "date": "October 29, 2026",
        "items": [
            "A more modern look: cards have softer edges and a light shadow, and lift a little when you point at them. Every card, table and panel now uses the same rounded corners.",
            "Numbers on the tiles are larger and bolder, with the label above them in a quieter style.",
            "Home's briefing headline sits on its own tinted card, and a shimmering placeholder shows while the forecast loads.",
            "The sidebar is slimmer: the page you're on is a tinted pill, and section names are small capitals.",
            "Page titles fade in gently. Turn on Reduce motion in Windows and the fade is skipped. High contrast keeps strong lines and no shadows.",
        ],
    },
    {
        "version": "0.37.32",
        "date": "October 29, 2026",
        "items": [
            "History's Daily view has a Compare with last year switch for 7 days and 30 days. It shows the hottest day, days at 100 or more, and rain, each next to last year's figure for the same days.",
        ],
    },
    {
        "version": "0.37.31",
        "date": "October 29, 2026",
        "items": [
            "Home replaces Live and Briefing. Today's briefing leads, then right now, the last 24 hours and your cards. Customize (top right) picks the readings and hides the briefing.",
            "History is one page now. Pick Daily, Records, Rankings, Compare, Month or Year at the top. Rewind and Coverage stay in the History section.",
            "The sidebar is shorter: Rankings, My year and Climate charts moved into History, and Season keeps Rain calendar and Rain events.",
        ],
    },
    {
        "version": "0.37.30",
        "date": "October 28, 2026",
        "items": [
            "The briefing's sunrise and sunset now follow the Time format setting: 5:42 PM in 12-hour, 17:42 in 24-hour.",
        ],
    },
    {
        "version": "0.37.29",
        "date": "October 26, 2026",
        "items": [
            "Times now show in 12-hour form, such as 2:30 PM, on the Live alerts, backups, lightning, rain events, charts and everywhere else. New Time format switch under Settings, Appearance: choose 12-hour or 24-hour, and every page and chart follows it.",
        ],
    },
    {
        "version": "0.37.28",
        "date": "October 26, 2026",
        "items": [
            "New morning briefing notification. Turn it on under Settings, Notifications: each morning at the hour you pick, Weather Lab sends the day's headline, how the expected high compares with yesterday, and any warning in effect, to this PC and your phone. It is off until you turn it on, and it waits during quiet hours.",
        ],
    },
    {
        "version": "0.37.27",
        "date": "October 26, 2026",
        "items": [
            "My year can now save a picture of the year: the hottest day, days at 100°F or more, the longest hot streak, the wettest day, the year's rain and the highest gust, ready to share. Use Save as image under the year's numbers.",
        ],
    },
    {
        "version": "0.37.26",
        "date": "October 26, 2026",
        "items": [
            "New Briefing page under Now: one sentence about today, the expected high against yesterday and the same day last year, last night's low, the heat index peak, UV, rain chance and wind, plus a short list of things worth knowing such as alerts, sunrise and sunset, and hot-day streaks. The Android app can read it too.",
        ],
    },
    {
        "version": "0.37.25",
        "date": "October 26, 2026",
        "items": [
            "New Backup page under Tools. Back up now, see every backup with its date and size, and restore one after a confirmation. A new backup is checked as soon as it is saved, and a backup is checked again before it replaces your data. Backup settings moved here from Export.",
        ],
    },
    {
        "version": "0.37.24",
        "date": "October 25, 2026",
        "items": [
            "The Android Wind page can now show how often the wind was calm (under 1 mph). Weather Lab shares the calm share over the phone connection.",
        ],
    },
    {
        "version": "0.37.23",
        "date": "October 25, 2026",
        "items": [
            "The Android Live page can now draw 24-hour lines for indoor temperature, indoor humidity, UV, rain rate, rain today and dew point. Weather Lab shares them over the phone connection.",
        ],
    },
    {
        "version": "0.37.22",
        "date": "October 25, 2026",
        "items": [
            "The Android Daily page can now show 1 day, 7 days, 30 days or all days, with summary numbers, charts, the wind rose and rain totals. Weather Lab shares the daily series and the rain totals over the phone connection.",
        ],
    },
    {
        "version": "0.37.21",
        "date": "October 25, 2026",
        "items": [
            "The Android Heat safety page can now show hours in each heat level today, hours at Danger or worse, the dangerous heat days, and today's heat index chart. Weather Lab shares them over the phone connection.",
        ],
    },
    {
        "version": "0.37.20",
        "date": "October 25, 2026",
        "items": [
            "The Android app can now show Records and analysis: summary numbers, heat, cold, wind and rain event lists, and the daily-high distribution. Weather Lab shares them over the phone connection.",
        ],
    },
    {
        "version": "0.37.19",
        "date": "October 25, 2026",
        "items": [
            "Every card on the Live page with history is a chart now: outdoor and indoor temperature, humidity, wind, gust and rain today each show their last 24 hours, with low and high.",
        ],
    },
    {
        "version": "0.37.18",
        "date": "October 25, 2026",
        "items": [
            "The cards on the Live page have more room: more padding inside each card, larger numbers, and more space between cards.",
        ],
    },
    {
        "version": "0.37.17",
        "date": "October 25, 2026",
        "items": [
            "The small ? icons beside terms are gone from every page, including the Live page. Hover help is off; the glossary is kept for later.",
        ],
    },
    {
        "version": "0.37.16",
        "date": "October 25, 2026",
        "items": [
            "Dew point is no longer at the top of the Live page. It is a card at the bottom, in the same style as the other Live charts, with a 24-hour trend and its low and high. Tap it for the full history.",
        ],
    },
    {
        "version": "0.37.15",
        "date": "October 25, 2026",
        "items": [
            "The Heat safety page now shows hours at Danger or worse today, dotted level lines on the chart, a ladder of all five heat safety levels with yours marked, hours spent in each level today, and a list of dangerous heat days.",
        ],
    },
    {
        "version": "0.37.14",
        "date": "October 25, 2026",
        "items": [
            "The Records page is now Records and analysis. It has summary tiles at the top and chips to pick a group (Records, Heat, Rain and storms, Climate and comparisons) and a view (Extreme events, Records board, Distribution).",
            "Extreme events lists the hottest, coldest, windiest and wettest days with counts for each. Distribution shows how many days fell in each daily-high range.",
        ],
    },
    {
        "version": "0.37.13",
        "date": "October 25, 2026",
        "items": [
            "The sidebar is regrouped to match the dashboard: Now, History, Air, sun and heat, Forecast and storms, Season, Tools, Health and Settings. Every page is still there; some moved to a new section.",
        ],
    },
    {
        "version": "0.37.12",
        "date": "October 25, 2026",
        "items": [
            "Daily and Daily history are one page now. Pick 1 day for a single day with its date box and charts, or 7 days, 30 days or All for the summary, daily charts, wind rose, rain totals and table for that span.",
            "Daily history is no longer in the sidebar. Its several-day view is under Daily.",
        ],
    },
    {
        "version": "0.37.11",
        "date": "October 25, 2026",
        "items": [
            "The wind rose now splits light wind into 1 mph, 2 mph, 3-4 mph and 5+ mph bands, with calm (under 1 mph) left out of the bands and reported in the caption. The Android wind page picks this up from the PC.",
        ],
    },
    {
        "version": "0.37.11",
        "date": "October 25, 2026",
        "items": [
            "The wind rose now splits light wind into 1 mph, 2 mph, 3-4 mph and 5+ mph bands, with calm (under 1 mph) left out of the bands and reported in the caption. The Android wind page picks this up from the PC.",
        ],
    },
    {
        "version": "0.37.10",
        "date": "October 25, 2026",
        "items": [
            "Daily history now starts with a live strip: the latest temperature, wind, humidity and rain today, and whether any weather warning is active.",
            "The wind rose uses blues from light to dark by wind speed, and says how much of the time the air was calm.",
        ],
    },
    {
        "version": "0.37.9",
        "date": "October 25, 2026",
        "items": [
            "Android app: tapping a Live tile now opens that reading's history for 24 hours, 7 days or 30 days, with its high, low and average. The app gets it from the new /api/v1/measure/<reading>/<days> address.",
        ],
    },
    {
        "version": "0.37.8",
        "date": "October 24, 2026",
        "items": [
            "Android app: the Live tiles can now show 24-hour trend lines, today's peaks, the pressure trend and airport visibility. The app asks Weather Lab for them through new /api/v1/tiles and airport details.",
        ],
    },
    {
        "version": "0.37.7",
        "date": "October 24, 2026",
        "items": [
            "The ? beside weather terms is now a blue ring, easier to see and tap. It fills in when you point at it.",
        ],
    },
    {
        "version": "0.37.6",
        "date": "October 24, 2026",
        "items": [
            "Fixed a crash in the background server that could stop the app with a connection error. Pages may load slightly slower.",
        ],
    },
    {
        "version": "0.37.5",
        "date": "October 24, 2026",
        "items": [
            "Now page: the Air and Wind and rain readings that have a history are now clickable, like the trend cards.",
        ],
    },
    {
        "version": "0.37.4",
        "date": "October 24, 2026",
        "items": [
            "Now page: the Humidity, Wind and UV readings are now trend cards showing the last 24 hours with their low and high. Click any card for its history.",
            "Now page: the other readings are grouped under Air and Wind and rain, and the status line is now a row of small pills.",
        ],
    },
    {
        "version": "0.37.3",
        "date": "October 24, 2026",
        "items": [
            "Fixed the clickable dials and tiles on Now for real: the whole dial or tile is now clickable, not just a strip at the top. The hover tooltip on them is gone.",
        ],
    },
    {
        "version": "0.37.2",
        "date": "October 24, 2026",
        "items": [
            "Fixed the clickable dials and tiles on Now. Clicking the temperature ring, Feels like, Pressure, Humidity, Wind, UV and the Last 24 hours tiles opens their history again.",
        ],
    },
    {
        "version": "0.37.1",
        "date": "October 24, 2026",
        "items": [
            "Weather Lab keeps the PC awake while it runs, so Windows doesn't put the PC to sleep and cut off the network and the phone connection. The screen can still turn off as usual.",
            "server.log now records a heartbeat every minute, with the time, the number of background tasks and the phone API status. If the log stops, Weather Lab stopped at that moment. This helps find any future drop.",
        ],
    },
    {
        "version": "0.37.0",
        "date": "October 23, 2026",
        "items": [
            "The Android app connection can now also read history from your own station: this calendar day in every year, months of the last three years side by side, a monthly card, a year in review, season milestones (first and last freeze and 90 and 100 degree days), unusual readings from the last 24 hours, the last 14 days of alerts, how close the forecast highs were, every daily summary as a CSV, and any past day replayed every 10 minutes. It can also read the nearest airport observation next to your station, tropical storms from the National Hurricane Center, radar picture addresses for your location, AirNow air quality (only if you added an AirNow key) and the phone-alert server and topic. All read-only, with the same token.",
        ],
    },
    {
        "version": "0.36.0",
        "date": "October 23, 2026",
        "items": [
            "The Android app connection can now also read more pages: the top 10 days (warmest, coolest, coldest nights, wettest, windiest, UV, sunniest), a rain calendar with yearly totals, rain events, the wind rose, lightning by day, sun and UV with sunburn times, heat safety, station health and sensors, this What's New list, and the National Weather Service forecast. The 7 and 30 day charts also send temperature readings so the phone can show them in more detail. These are read-only, like the rest, and use the same token.",
        ],
    },
    {
        "version": "0.35.0",
        "date": "October 23, 2026",
        "items": [
            "The Android app connection can now also read daily charts for the last 7 and 30 days, the last 60 days of highs, lows and rain, every figure kept for any one day (including yesterday), and the all-time records with the day each happened. These are read-only, like the rest, and use the same token.",
        ],
    },
    {
        "version": "0.34.0",
        "date": "October 23, 2026",
        "items": [
            "On Now, the dials and tiles open their history when you click them: the big temperature ring, Feels like, Pressure, Humidity, Wind, UV index and the three Last 24 hours tiles. The History buttons below them are gone. The ? help stays in the top corner of the Feels like and Pressure dials.",
        ],
    },
    {
        "version": "0.33.0",
        "date": "October 23, 2026",
        "items": [
            "The Ecowitt export import now accepts an export of any span of time. ecowitt.net only lets you pick whole days, so exports often don't run from 5 PM to 5 PM; before, those were refused. Now their readings are added (except where Weather Lab already has a reading at that time) and the summaries of those days are rebuilt. Exports with readings more than 5 minutes apart can be a few degrees off at the day's high and low.",
        ],
    },
    {
        "version": "0.32.0",
        "date": "October 23, 2026",
        "items": [
            "The Android app connection can now also read the last 24 hours of temperature, the high, low and rain for the last 7 days, and lightning (the last strike, strikes in the last 10 and 30 minutes and today, and whether a storm is approaching or moving away). These are read-only, like the rest, and use the same token.",
            "The rain total in today's summary for the Android app now keeps two decimals, so 0.05 in no longer shows as 0.1 in.",
        ],
    },
    {
        "version": "0.31.0",
        "date": "October 23, 2026",
        "items": [
            "A read-only connection for the Android app, off by default. Turn it on in Settings under Android app, and create a token there. The token is shown once. The app can read the latest reading, today's high, low and rain, and the recent alerts. It only works while Weather Lab is open and phones and devices are allowed.",
        ],
    },
    {
        "version": "0.30.0",
        "date": "October 23, 2026",
        "items": [
            "Settings, under Phones and devices, has a Who can reach Weather Lab note. It says in plain words who can open the app right now, how the password works, and that nothing is opened to the internet.",
        ],
    },
    {
        "version": "0.29.0",
        "date": "October 23, 2026",
        "items": [
            "A small ? now sits beside the labels for the Air quality index, Last strike and Closest today on Lightning, and the heat index tiles on Heat. Hover it on a computer, or tap it on a phone, to see what the term means.",
        ],
    },
    {
        "version": "0.28.0",
        "date": "October 23, 2026",
        "items": [
            "On Live, Dew point, Feels like and Pressure now have a small ? beside their history button instead of a line of text. Hover over it on a computer to see what the term means, or tap it on a phone for the full explanation.",
        ],
    },
    {
        "version": "0.27.0",
        "date": "October 23, 2026",
        "items": [
            "A new Help page in the Configure section explains the terms you see: dew point, feels like, heat index, wind chill, humidity, gusts, pressure, rain, UV, air quality and more. Search it by any word.",
            "Dew point, feels like and pressure each show a one-line explanation under their number on Live.",
        ],
    },
    {
        "version": "0.26.0",
        "date": "October 23, 2026",
        "items": [
            "Health check has a Test the newest backup button. It opens a copy read-only, checks it is intact and says how many readings it holds, so you know a backup would really restore.",
            "A new install shows a short welcome on Live with three steps, and ticks each one as it's done.",
            "The Live dial history charts shade the night between sunset and sunrise, so the dark hours are visible at a glance.",
            "A new option in Settings sends a Monday summary of the last seven days: highest and lowest temperature, total rain, and how many days were recorded.",
        ],
    },
    {
        "version": "0.25.0",
        "date": "October 23, 2026",
        "items": [
            "Health check has a new Recent errors line. When the background collector hits an error, it is now written to a short log that the line reads, so problems are no longer only visible in a console window.",
            "Your phone gets an alert if the drive is nearly full or a daily backup fails. It is sent once per problem, and again only if the problem clears and comes back. You can turn it off in Settings.",
            "A new High contrast colour scheme in Settings uses plain black and white with strong lines. Its text meets the strictest contrast standard (7 to 1).",
            "Charts on a phone show fewer, smaller axis labels so they don't run together.",
            "More behind-the-scenes tests, including a start-up check that runs automatically on GitHub.",
        ],
    },
    {
        "version": "0.24.1",
        "date": "October 22, 2026",
        "items": [
            "Every coloured summary tile now says its level in words: Good, Watch, Alert or Info. Colour is no longer the only sign, so the level reads the same without it.",
            "The UV tiles name the UV level, from low to extreme, next to the number.",
            "The NOAA history subtitle is shorter, so it fits on a phone.",
        ],
    },
    {
        "version": "0.24.0",
        "date": "October 22, 2026",
        "items": [
            "The 24-hour tiles on Live are coloured by what the number means. Temperature and wind above usual are amber, humidity above usual is grey, and anything below usual is blue. Red is kept for real problems.",
            "The Wind tile in the 24-hour section has no History button now. The Wind dial below has one, so there's a single way in.",
            "Until a station has five days of readings, the usual-for-this-hour note shows how many days it has so far, with a count of five.",
            "The subtitles on Forecast, Health check and Stations are shorter, so they fit on a phone.",
        ],
    },
    {
        "version": "0.23.0",
        "date": "October 22, 2026",
        "items": [
            "Every page has a one-line subtitle under its title that says what the page shows.",
            "Tables look the same on every page: a shaded header row, numbers lined up on the right, and the same spacing.",
            "The summary tiles on Forecast, Heat, Sun, Sensors and Daily history have a coloured edge. Green is good, amber needs a look, red is a problem, and blue is information. A tile with nothing to flag stays grey.",
            "The 24-hour tiles on Live have the same coloured edge. Only a tile well above or below its usual level is coloured.",
            "The Wind and UV dials on Live have a History button, and so does the Dew point line. Humidity's History button is in the 24-hour section.",
            "On a phone, the Daily history table shows the date, high, low and rain so it fits. Average, gust, sun hours and humidity show on a wider screen, and the CSV download has every column.",
        ],
    },
    {
        "version": "0.22.9",
        "date": "October 22, 2026",
        "items": [
            "Daily history is laid out like the dashboard's page: a summary strip of hottest day, coldest night, average high, total rain, wettest day and highest gust, then charts grouped by temperature and rain, humidity and pressure, indoors, and wind and sunshine.",
            "The wind rose for the period comes with the prevailing wind for each month. It's worked out from one reading every ten minutes, and refreshes every 30 minutes.",
            "The page opens on the last year. Choose the last 30 days, the last 90 days, or all of the record.",
            "The sidebar entry is now Daily history, so it's not confused with the single-day Daily page.",
        ],
    },
    {
        "version": "0.22.8",
        "date": "October 22, 2026",
        "items": [
            "Sensors is laid out like the dashboard's Sensor health page: a summary strip, a sensor status table, batteries and radio signal, completeness and gaps side by side, data quality alerts, and sensor activity.",
            "See a sensor's history: tap a sensor to open its history over 24 hours, 7 days or 30 days, with its highest, lowest and average.",
            "History windows also cover gust, rain today, solar, indoor temperature and indoor humidity. Humidity history shows a percent sign.",
        ],
    },
    {
        "version": "0.22.7",
        "date": "October 22, 2026",
        "items": [
            "Every page in the sidebar has a colour emoji icon, like the dashboard's menu, instead of a plain line icon.",
        ],
    },
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
