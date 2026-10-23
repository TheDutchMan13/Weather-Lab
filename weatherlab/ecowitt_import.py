"""Ecowitt daily history exports (.xlsx from ecowitt.net, Device > History > Export).

Ported from the dashboard's import_ecowitt_export.py (see SOURCES.md). Each daily row is labelled 5:00 PM and covers
5 PM to 5 PM, so it is stored under the day that ends at that time: the row labelled Oct 8 5:00 PM is stored as Oct 9.
Days Weather Lab already has are never replaced. Values must be in US units (°F, mph, inches).
"""

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta

from . import readings_daily

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
RNS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DAILY_HOUR = 17
MAP = {  # export column (see slug) -> daily summary key
    "outdoor_temperature_high": "tempf_max", "outdoor_temperature_low": "tempf_min",
    "outdoor_temperature": "tempf_avg", "outdoor_humidity_high": "humidity_max",
    "outdoor_humidity_low": "humidity_min", "rainfall_piezo_daily": "rain_in",
    "rainfall_piezo_rain_rate": "rainrate_max", "wind_wind_gust": "gust_max",
}


def _col(ref):
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def read_xlsx(source):
    """Rows of the sheet named result_list (or the first sheet). source: a path or a file-like object."""
    with zipfile.ZipFile(source) as z:
        names = set(z.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        rels = {r.get("Id"): r.get("Target")
                for r in ET.fromstring(z.read("xl/_rels/workbook.xml.rels")).findall(PKG + "Relationship")}
        sheets = [(s.get("name"), rels.get(s.get(RNS + "id")))
                  for s in wb.find(NS + "sheets").findall(NS + "sheet")]
        pick = next((t for n, t in sheets if n == "result_list"), sheets[0][1])
        target = pick.lstrip("/")
        target = target if target.startswith("xl/") else "xl/" + target
        rows = []
        for row in ET.fromstring(z.read(target)).iter(NS + "row"):
            cells = {}
            for c in row.findall(NS + "c"):
                t, v = c.get("t"), c.find(NS + "v")
                if t == "inlineStr":
                    val = "".join(x.text or "" for x in c.iter(NS + "t"))
                elif v is None or v.text is None:
                    continue
                elif t == "s":
                    val = shared[int(v.text)]
                elif t in ("str", "e"):
                    val = v.text
                else:
                    try:
                        val = float(v.text)
                    except ValueError:
                        val = v.text
                cells[_col(c.get("r"))] = val
            if cells:
                rows.append([cells.get(i) for i in range(max(cells) + 1)])
        return rows


def slug(group, name):
    s = f"{group or ''} {name or ''}"
    s = re.sub(r"\([^)]*\)", "", s).lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def parse_daily_rows(rows):
    """{date: summary} from the rows of a daily export. Raises ValueError when the rows aren't a daily export."""
    if len(rows) < 3:
        raise ValueError("That file has no data rows.")
    width = max(len(r) for r in rows[:3])
    top = (rows[0] + [None] * width)[:width]
    sub = (rows[1] + [None] * width)[:width]
    group, names = None, []
    for i in range(width):
        if top[i]:
            group = top[i]
        names.append("time" if i == 0 else slug(group, sub[i]))
    out = {}
    for r in rows[2:]:
        if not r or not isinstance(r[0], str):
            continue
        try:
            t = datetime.strptime(r[0].strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if t.hour != DAILY_HOUR or t.minute != 0:
            raise ValueError("These rows aren't daily totals at 5:00 PM. Export the daily history from ecowitt.net, "
                             "not a finer interval.")
        vals = {}
        for i in range(1, width):
            v = r[i] if i < len(r) else None
            if isinstance(v, float):
                vals[names[i]] = v
        out[(t + timedelta(days=1)).date()] = {MAP[k]: vals[k] for k in MAP if k in vals}
    if not out:
        raise ValueError("No daily rows were found. Export the daily history from ecowitt.net as an .xlsx file.")
    return out


def days_from_file(source):
    return parse_daily_rows(read_xlsx(source))


def days_from_files(sources):
    """{date: summary} from one or more exports. Daily exports are used as they are. Exports with readings finer than
    daily (every minute, 5-minute or 4-hour) are summarized into days; days from the 4-hour readings are marked estimated."""
    days, readings = {}, []
    for source in sources:
        rows = read_xlsx(source)
        try:
            days.update(parse_daily_rows(rows))
        except ValueError:
            readings.append(rows)
    for day, summary in readings_daily.days_from_readings(readings).items():
        days.setdefault(day, summary)
    return days


def readings_from_files(sources, tz):
    """[(timestamp, reading)] for every row of the exports that aren't daily, whatever time span they cover,
    and the most minutes between two readings. Raises ValueError when no file has readings or daily rows."""
    out, widest, daily_files = {}, 0, 0
    for source in sources:
        rows = read_xlsx(source)
        try:
            parse_daily_rows(rows)
            daily_files += 1
            continue
        except ValueError:
            pass
        found, minutes = readings_daily.readings_from_rows(rows)
        for stamp, reading in found:
            ts = int(stamp.replace(tzinfo=tz).timestamp())
            out.setdefault(ts, (reading, minutes or 0))
        widest = max(widest, minutes or 0)
    return out, widest


def store_readings(db, found, widest, tz, lat=0.0, lon=0.0, elev_m=0.0):
    """Saves readings from an export. A reading is skipped when Weather Lab already has one within the export's own
    interval, so readings it collected itself aren't mixed with coarser ones. Then rebuilds the summaries of the days
    covered (days from a daily export are left alone). Returns (added, skipped, days)."""
    from bisect import bisect_left
    from . import daily
    if not found:
        return 0, 0, 0
    lo, hi = min(found), max(found)
    pad = int(widest * 60) + 1
    held = sorted(r[0] for r in db.execute(
        "SELECT ts FROM readings WHERE ts BETWEEN ?1 AND ?2 UNION SELECT ts FROM readings_archive WHERE ts BETWEEN ?1 AND ?2",
        (lo - pad, hi + pad)))
    rows = []
    for ts, (reading, minutes) in sorted(found.items()):
        near = int(minutes * 30)  # half an interval
        i = bisect_left(held, ts - near)
        if i < len(held) and held[i] <= ts + near:
            continue
        rows.append((ts, json.dumps(reading), "ecowitt"))
    with db:
        db.executemany("INSERT OR IGNORE INTO readings (ts, data, source) VALUES (?, ?, ?)", rows)
    days = sorted({datetime.fromtimestamp(ts, tz).date() for ts in found})
    daily.rollup_days(db, days, lat, lon, elev_m, tz, datetime.now(tz).date())
    return len(rows), len(found) - len(rows), len(days)


def store_days(db, days):
    """Adds the days Weather Lab doesn't have yet. Returns how many were added."""
    added = 0
    with db:
        for day, data in days.items():
            cur = db.execute("INSERT OR IGNORE INTO daily (date, data) VALUES (?, ?)",
                             (day.isoformat(), json.dumps({**data, "source": "ecowitt"})))
            added += cur.rowcount
    return added
