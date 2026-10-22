"""The records board: every record the daily summaries can show, grouped by type, plus six highlights.

Records come from the daily summaries only. Records that need readings the summaries don't keep (such as the most
rain in an hour, or the highest heat index) are not shown. Pure Python, so it can be tested without Streamlit.
"""

from datetime import date, timedelta

DRY_BELOW_IN = 0.01  # a day with less rain than this counts as dry
NEW_DAYS = 30  # a record set in the last 30 days is marked NEW

GROUPS = ["Temperature", "Rain", "Wind", "Humidity and pressure"]
HIGHLIGHTS = [  # (label, icon, record name)
    ("Hottest day", "🔥", "hi_temp"),
    ("Coldest night", "❄️", "lo_temp"),
    ("Highest heat index", "🥵", "heat_hi"),
    ("Wettest day", "💧", "wet_day"),
    ("Highest gust", "💨", "gust_hi"),
    ("Longest dry spell", "🏜️", "dry_spell"),
]


def _best(days, key, high):
    """(value, day) for the highest or lowest value of a daily key, or None."""
    found = [(d[key], day) for day, d in days if d.get(key) is not None]
    if not found:
        return None
    return max(found) if high else min(found)


def _runs(days):
    """Runs of consecutive days that are all wet or all dry. A day with no rain figure ends a run."""
    out, cur, prev = [], None, None
    for day, d in days:
        rain = d.get("rain_in")
        if rain is None:
            if cur:
                out.append(cur)
            cur, prev = None, None
            continue
        wet = rain >= DRY_BELOW_IN
        if cur and cur["wet"] == wet and (day - prev).days == 1:
            cur["end"], cur["length"] = day, cur["length"] + 1
        else:
            if cur:
                out.append(cur)
            cur = {"wet": wet, "start": day, "end": day, "length": 1}
        prev = day
    if cur:
        out.append(cur)
    return out


def _spell(days, wet: bool):
    """The longest wet or dry run: (length, last day, ended on, or None while it is still going)."""
    runs = [r for r in _runs(days) if r["wet"] == wet]
    if not runs:
        return None
    best = max(runs, key=lambda r: (r["length"], r["end"]))
    after = best["end"] + timedelta(days=1)
    have = {day for day, _ in days}
    return best["length"], best["end"], (after if after in have else None)


def _wettest_month(days, today: date):
    """(total inches, first day of the month) for the wettest complete month. The current month is left out."""
    totals: dict = {}
    for day, d in days:
        if d.get("rain_in") is None or (day.year, day.month) == (today.year, today.month):
            continue
        totals[(day.year, day.month)] = totals.get((day.year, day.month), 0.0) + d["rain_in"]
    if not totals:
        return None
    year, month = max(totals, key=lambda k: (totals[k], k))
    return totals[(year, month)], date(year, month, 1)


def board(days, today: date) -> dict:
    """days: [(date, daily summary)] in date order. Returns {"records": [...], "highlights": [...]}.
    Each record: name, label, group (None for highlights only), value, date, unit_key, plain, dec, when, note, new."""
    records = []

    def add(name, label, group, found, high, unit_key=None, plain="", dec=0, when=None):
        if found is None:
            return
        value, day = found[0], found[1]
        ended = found[2] if len(found) > 2 else None
        note = ""
        if len(found) > 2:
            note = f"ended {ended:%b %d, %Y}" if ended else "still going"
        records.append({"name": name, "label": label, "group": group, "value": value, "date": day,
                        "unit_key": unit_key, "plain": plain, "dec": dec, "high": high,
                        "when": when or (f"{day:%b %d, %Y}".replace(" 0", " ") if not note else note),
                        "note": note, "new": day >= today - timedelta(days=NEW_DAYS)})

    temp, rain, wind, hum = "Temperature", "Rain", "Wind", "Humidity and pressure"
    add("hi_temp", "Highest temperature", temp, _best(days, "tempf_max", True), True, "tempf", dec=1)
    add("lo_temp", "Lowest temperature", temp, _best(days, "tempf_min", False), False, "tempf", dec=1)
    add("heat_hi", "Highest heat index", temp, _best(days, "heat_index_max", True), True, "heat_index", dec=1)
    add("warm_night", "Warmest night (highest low)", temp, _best(days, "tempf_min", True), True, "tempf", dec=1)
    add("cool_aft", "Coolest afternoon (lowest high)", temp, _best(days, "tempf_max", False), False, "tempf", dec=1)
    swings = [(d["tempf_max"] - d["tempf_min"], day) for day, d in days
              if d.get("tempf_max") is not None and d.get("tempf_min") is not None]
    if swings:
        add("swing_big", "Biggest daily swing", temp, max(swings), True, "tempf", dec=1)
        add("swing_small", "Smallest daily swing", temp, min(swings), False, "tempf", dec=1)

    add("rate_hi", "Highest rain rate", rain, _best(days, "rainrate_max", True), True, "rainratein", dec=2)
    add("wet_day", "Wettest day", rain, _best(days, "rain_in", True), True, "dailyrainin", dec=2)
    month = _wettest_month(days, today)
    if month:
        add("wet_month", "Wettest month", rain, (month[0], month[1]), True, "dailyrainin", dec=2,
            when=f"{month[1]:%b %Y}")
    dry = _spell(days, wet=False)
    if dry:
        add("dry_spell", "Longest dry spell", rain, (dry[0], dry[1], dry[2]), True, plain=" days", dec=0)
    wet = _spell(days, wet=True)
    if wet:
        add("wet_spell", "Longest wet spell", rain, (wet[0], wet[1], wet[2]), True, plain=" days", dec=0)

    add("gust_hi", "Highest gust", wind, _best(days, "gust_max", True), True, "windgustmph")
    add("wind_hi", "Highest wind speed", wind, _best(days, "wind_max", True), True, "windspeedmph")
    add("wind_run", "Most wind in a day (wind run)", wind, _best(days, "wind_run_mi", True), True, "miles", dec=1)

    add("hum_hi", "Highest humidity", hum, _best(days, "humidity_max", True), True, plain="%", dec=0)
    add("hum_lo", "Lowest humidity", hum, _best(days, "humidity_min", False), False, plain="%", dec=0)
    add("baro_hi", "Highest pressure", hum, _best(days, "baro_max", True), True, "baromrelin", dec=2)
    add("baro_lo", "Lowest pressure", hum, _best(days, "baro_min", False), False, "baromrelin", dec=2)


    by_name = {r["name"]: r for r in records}
    highlights = [dict(by_name[name], icon=icon, title=title)
                  for title, icon, name in HIGHLIGHTS if name in by_name]
    grouped = [(g, [r for r in records if r["group"] == g]) for g in GROUPS]
    return {"records": [r for r in records if r["group"]], "highlights": highlights,
            "groups": [(g, rows) for g, rows in grouped if rows]}
