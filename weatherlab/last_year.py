"""Last year's figures for the same days, for the History page's "Compare with last year" (0.37.32).

Pure helpers, no streamlit, so the tests can run without the page's dependencies."""

from datetime import date


def year_back(day: date) -> date:
    """The same day one year earlier (Feb 29 becomes Feb 28)."""
    try:
        return day.replace(year=day.year - 1)
    except ValueError:
        return day.replace(year=day.year - 1, day=28)


def figures(rows: list) -> dict:
    """Hottest high, days at 100 or more, and total rain for [(date, summary), ...]. None when there is no data."""
    highs = [s["tempf_max"] for _, s in rows if s.get("tempf_max") is not None]
    rain = [s["rain_in"] for _, s in rows if s.get("rain_in") is not None]
    return {"days": len(rows),
            "hottest": max(highs) if highs else None,
            "hot_days": sum(1 for v in highs if v >= 100) if highs else None,
            "rain": sum(rain) if rain else None}


def compare(this_rows: list, last_rows: list) -> dict:
    """{'this': figures, 'last': figures}; 'last' has no figures at all when last year has no days in the range."""
    return {"this": figures(this_rows), "last": figures(last_rows) if last_rows else None}
