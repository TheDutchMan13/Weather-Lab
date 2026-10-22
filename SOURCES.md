# Sources copied from the weather dashboard

The dashboard at `C:\Weather Station\ecowitt-dashboard` is never edited by this project.

## Copied

| File in Weather Lab | Copied from | Date | Notes |
|---|---|---|---|
| `weatherlab/parse.py` | `collectors/gw2000_collector.py` lines 48–171 (unit handling, `parse_livedata`, `LIMITS`, `clean`, `plausible`) and lines 195–197 (`fetch`) | 2026-10-19 | `parse_lightning` is in `weatherlab/lightning.py` (see below). |
| `weatherlab/storage.py` | `collectors/gw2000_collector.py` `connect` and `store_reading` (the `readings` and `daily` tables) | 2026-10-19 | Path moved to the user's AppData folder. The dashboard's other tables are not copied. |
| `weatherlab/daily.py` | `collectors/gw2000_collector.py` `_solar_max` (lines 247–261), `summarize_day` (lines 264–294), `rollup_daily` (lines 297–329) | 2026-10-20 | Location, timezone, and elevation come from settings. The solar time uses UTC plus longitude instead of the dashboard's hardcoded Arizona standard meridian. For Phoenix the result is the same. The daily-meta table and the CumulusMX fallback are not copied. |
| `weatherlab/charts.py` layout, colours, grid, legend, hover box and toolbar | `wxdash/common.py` `get_chart_layout` and `get_accent_border`, `utils/chart_cfg.py` `chart_config`, `style_fig` and `CHART_COLORS` | 2026-10-20 | The dashboard's config.py CHART_* values are not used by its charts, so they are not copied. Text colour follows style_fig. Phone sizes, time hover labels and the hover-tips setting are matched (see the latest section). |
| `weatherlab/config.py` colors | `config.py`, the COLOR PALETTE and RISK COLORS sections (`ACCENT_COLOR`, `RISK_COLORS`) | 2026-10-19 | Values copied exactly. |
| `weatherlab/theme.py` palettes | `utils/theme.py` `LIGHT_PALETTE` and `DARK_PALETTE` (page, surface, text, muted, accent) | 2026-10-20 | Values copied exactly. |
| `weatherlab/theme.py` card colors | `utils/live_cards.py` `_k` (card, line, sub, text, muted for light and dark) | 2026-10-20 | Values copied exactly. |
| `weatherlab/theme.py` font | `utils/live_cards.py` `FONT` | 2026-10-20 | Copied exactly. |
| `weatherlab/theme.py` tile and heading style | `utils/page_look.py` `strip_html` and `page_head_html` | 2026-10-20 | Restyled as CSS classes. |
| `weatherlab/theme.py` `is_dark` | `utils/theme.py` `is_dark_mode` (auto mode only) | 2026-10-20 | Light, Dark and Auto are chosen on the Setup page. |

| `weatherlab/comfort.py` | `update_records.py` lines 50–80 (`heat_index_f`, `humidex_c`, `wind_chill_f`) | 2026-10-20 | Formulas copied as they were. |
| `weatherlab/airquality.py` | `import_airnow.py` `fetch_aqi` | 2026-10-20 | Endpoint and pollutant names copied. The ZIP-code lookup is replaced with latitude and longitude from settings. The API key is not copied. |
| `weatherlab/lightning.py` | `collectors/gw2000_collector.py` `parse_lightning` (lines 174–194) | 2026-10-20 | The dashboard's km switch became the `lightning_value_is_km` setting. |
| `weatherlab/fire.py` | `import_fire_weather.py` lines 39–158 (`DEFAULT_CODES`, `DAY_LENGTH`, `DAY_FACTOR`, the FFMC, DMC, DC, and FWI equations) and lines 226–249 (forecast at the hour nearest 1 pm) | 2026-10-20 | Equations unchanged. Location, time zone, and NWS grid point come from settings. Moisture codes are stored in the database, not in `fwi_state.json`. The dashboard's hardcoded grid `PSR/145,58` and `America/Phoenix` are not copied. |
| `weatherlab/nws.py` `forecast_hourly` (humidity, wind, limit) | `import_fire_weather.py` `fetch_forecast_near_1pm` fields | 2026-10-20 | Fields added for the fire index. |
| `weatherlab/wx_icons.py` | `utils/wx_icons.py`, the whole file (copied unchanged) | 2026-10-20 | Forecast icons on the Forecast page. The dashboard's Live 'right now' icon is not used yet. |

## Written for Weather Lab (not copied)

- `weatherlab/cwop.py`: CWOP upload. The dashboard has no CWOP code. The APRS-IS login line and position-weather format were checked against a public APRS-IS guide (hamradio.my, article 7494). The passcode uses the standard APRS-IS algorithm.
- `installer.iss` and `build_installer.py`: Inno Setup installer. Written for Weather Lab.
- `README.md`: written for other users.

- `weatherlab/history.py`: the Daily, History, and Records queries. Records and rain totals are new. Rain totals come from each day's rain value in the daily summaries, not from the dashboard's rain tracker.
- `weatherlab/secrets.py` (Windows Credential Manager via keyring).
- Lightning, Air, Fire, and comfort pages and tiles in `app.py`.
- `weatherlab/report.py`: daily PDF with reportlab. The sections follow the dashboard's `pdf_generator.py` (current conditions, daily statistics). The monthly and yearly reports (`monthly_pdf`, `yearly_pdf`) follow the monthly sections of `pdf_generator.py` (summary and extreme events: 110°F and above, 32°F and below, 20+ mph gusts, rain days). The dashboard's `period_report.py` was not read or copied, so its layouts may differ.
- Daily, History, and Records pages in `app.py`. The dashboard's page layouts were not copied.

## Referenced only

| Weather Lab location | Dashboard source | Date | Notes |
|---|---|---|---|
| Rain IDs `0x0E` and `0x10` (`parse.py`) | `collectors/gw2000_collector.py` lines 130–136 | 2026-10-19 | The yearly ID `0x13` is mapped in the dashboard but not in Weather Lab yet. |
| Poll interval of 30 seconds (`poller.py`) | `collectors/gw2000_collector.py` `POLL` | 2026-10-19 | Same value. |

## Deliberately not copied

These were hardcoded or personal in the dashboard and are settings or left out:

- Goodyear, AZ coordinates (`LATITUDE`, `LONGITUDE`, `ELEV_M`) and the NWS grid point (`PSR/148,59`)
- `C:\Weather Station\...`, CumulusMX paths, and `dbpath.py`
- NOAA station ID and `noaa_token.txt`
- `airnow_key.txt` and any other key files
- `gw2000_ip.txt`, `station_scan.txt`, and `cumulus_dir.txt`
- Phoenix-specific alert presets
- `set_dashboard_password.py`, `reports/`, backups, and the database
- Lightning distance quirk (`LIGHTNING_REPORTED_IN_KM`). Now the `lightning_value_is_km` setting on the Setup page.
- AirNow key. Now stored in Windows Credential Manager through `weatherlab/secrets.py`, which was written for Weather Lab.

## Placeholder values to replace

None.

## Added for the new pages
- heat_safety.py, wind_rose.py, sun_uv.py: written for Weather Lab (heat index categories from the National Weather Service; sunburn minimal erythema doses from the WHO).
- tropics.py: adapted from the dashboard utils/tropics.py (NHC CurrentStorms.json feed).
- Radar pictures: radar.weather.gov ridge loops, the same ones the dashboard uses (dash_pages/radar.py).
- Notifications: plyer.

- theme.py colour schemes (SCHEMES): copied from the dashboard utils/theme.py COLOR_SCHEMES.
- units.py: the dashboard's Settings > Display US/Metric choice (utils/units.py, display only).

## Added for the Add-it-all features
- gateway_sensors.py: battery and signal rules adapted from the dashboard utils/sensor_battery.py (the GW2000 /get_sensors_info pages).
- ecowitt_import.py: the export reader and the 5 PM daily rule adapted from the dashboard import_ecowitt_export.py. Not yet checked against a real daily export: confirm on the first import.
- astro.py: sunrise and sunset from the NOAA sunrise equation, and moon phases from the mean synodic month, written for Weather Lab. The dashboard's astronomy uses skyfield, which is not included.
- record_alerts.py, station_status.py, rain_calendar.py, replay.py: written for Weather Lab.

## Added for the Live and history pages
- weatherlab/dials.py: feels-like and pressure trend dials. Heat zones and pressure bands are the dashboard's values, from utils/visuals.py (ZONES, feels_like_html) and utils/visuals3.py (PRESSURE_BANDS, pressure_dial_html).
- weatherlab/sparks.py: 24-hour sparklines and usual-for-this-hour notes, from utils/visuals.py (_spark, usual_delta, compare_text). Usual needs five earlier days of readings.
- weatherlab/alert_map.py: shades warnings on NWS zone outlines. Outlines come from api.weather.gov at run time for the configured location. The dashboard's Arizona outline and zone files were not copied.
- weatherlab/yearly.py: rankings, same date in past years, monthly climate and year summary, computed from Weather Lab's own daily summaries.

## Theme copy (page look)
- weatherlab/theme.py PAGE_LIGHT and PAGE_DARK: utils/theme.py LIGHT_PALETTE and DARK_PALETTE (background, surface, border, text, text_muted, accent). Copied exactly.
- weatherlab/theme.py SCHEMES: utils/theme.py COLOR_SCHEMES, copied exactly. page_palette() and palette() apply them the way get_palette() does.
- weatherlab/theme.py page rules (sidebar, text, tabs, inputs, buttons): utils/theme.py apply_theme_css.
- weatherlab/theme.py pill tabs, button groups, card containers, alerts and metrics: wxdash/live_glue.py inject_style. The selected-tab colours are in TAB_ON.
- weatherlab/theme.py MOBILE_CSS: utils/theme.py apply_mobile_css (900 px and 640 px breakpoints), then the card tile sizes for phones.
- Body text uses Streamlit's default font, as the dashboard does. Tiles and headings use FONT.
- Light, Dark and Auto are chosen on the Setup page. The dashboard's toggle isn't copied.
- Streamlit's top-right menu is shown, as on the dashboard.

## Matched in the latest pass
- weatherlab/autofit.py: wxdash/live_glue.py `_FIT_JS` and `install_autofit`, copied exactly. Embedded panels fit their content.
- weatherlab/theme.py `section_html`, `freshness_html` and the `.wx-sec` rules: wxdash/live_glue.py `section`, `freshness_chip` and `inject_style`. Used for the 24-hour cards and the climate chart headings.
- weatherlab/theme.py `is_phone`: wxdash/common.py `is_phone` (User-Agent check).
- weatherlab/charts.py `show` and phone sizes: wxdash/common.py `get_chart_layout` (phone margins, legend and height) and utils/chart_cfg.py `style_fig` (260 px cap, time hover labels).
- weatherlab/settings.py `tooltips` and the Setup checkbox: wxdash/settings_view.py "Show helpful tooltips" and wxdash/common.py `tooltips_on`. Off removes the hover box.
- tools/compare_looks.py: new for Weather Lab, not copied. It screenshots both apps and compares their styles.
- weatherlab/motion.py GAUGE_ANIM: wxdash/live.py GAUGE_ANIM and animated, copied exactly. Runs in the temperature ring and the feels-like and pressure dials. Card gauges use a CSS sweep (wl-sweep) instead, because they sit in markdown, where scripts don't run.
- weatherlab/settings.py animate and the Setup checkbox: wxdash/settings_view.py "Animate gauges" (pref_animations, on by default).
- weatherlab/dials.py needles: polygons turned with a rotate transform, so the animation script can sweep them.
- Ecowitt import: five column names (outdoor temperature and humidity high and low, wind gust) match the dashboard's import_ecowitt_export.py. The full column list still needs a real export to check.

- weatherlab/readings_daily.py: new, built for this app (not in the dashboard). Days from 5-minute and 4-hour Ecowitt exports, 5 PM to 5 PM like the daily export. 4-hour days are marked estimated. Checked against a 5-minute day (October 20): 4-hour high 92.3 vs 5-minute 95.0, low 71.6 vs 69.6.

## Colours matched to the dashboard (22 Oct 2026)
- weatherlab/charts.py: PAL (the nine named colours), MEASURE (one colour per measure) and CHART_COLORS (the multi-series list), copied from the dashboard's utils/chart_cfg.py and config.py CHART_COLORS.
- Accent blue #4ea1ff in weatherlab/config.py, weatherlab/theme.py (both modes) and the health dot, from the dashboard's PAL "blue".
- Charts use the measure colours: temperature amber, rain violet, wind and humidity and UV and lightning quiet grey-blue, gust green dashed, pressure gold, dew point teal. Series on the same chart use CHART_COLORS in order.
- Not copied: the white newest-point marker, and the dashboard's storm and dust colour scales.

## Click for history (22 Oct 2026)
- The idea of clicking a Live reading for its history window (24 hours, 7 days, 30 days, with highest, lowest and average) is from the dashboard's wxdash/detail_view.py. The code is new: weatherlab/screens/live_history.py and weatherlab/history_series.py.

## Records page look (22 Oct 2026)
- The layout of the Records page (a gradient highlights card, then record cards grouped by type with a coloured top border, highest and lowest dots, and NEW badges) is copied from the dashboard's records page look. The code is new: weatherlab/record_board.py and screens/history.py records_page.
- Records that need readings the daily summaries don't keep (most rain in an hour, most rain in 24 hours, dew point, feels-like, wind chill, humidex) are not shown.

## Sidebar page icons (22 Oct 2026)
- The emoji icons for the sidebar pages follow the dashboard's sidebar in dash_pages (app_router.py), where a page matches. The icon choices are the dashboard's; the code that uses them (PAGE_ICONS in app.py) is new.

## Sensors page look (22 Oct 2026)
- The layout of the Sensors page (summary strip, Sensor status table, "See a sensor's history" chips, batteries and radio signal, completeness and gaps side by side, data quality alerts, sensor activity) follows the dashboard's Sensor health page (wxdash/sensor_health.py). The code is new: weatherlab/screens/now.py sensors_page, and the sensor list in weatherlab/health.py.
- The sensor order and names follow the dashboard's Sensor health table.
