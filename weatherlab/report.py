"""PDF reports, built with reportlab. The layouts are new. The sections follow the dashboard's
pdf_generator.py (current conditions, daily statistics, extreme events, monthly breakdown),
and the figures come from the daily summaries. Figures follow the US or metric choice."""

import html
from collections import defaultdict
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from weatherlab import units as U
from weatherlab.config import ACCENT_COLOR

RAINY_IN = 0.1  # a rainy day, as the dashboard's monthly report counts it


def _value(x, unit: str, spec: str) -> str:
    """For readings without a US/metric choice (humidity, sun hours)."""
    return "--" if x is None else f"{format(x, spec)}{unit}"


def _shown(key: str, x, metric: bool, spec: str) -> str:
    """A US reading in the chosen units, with its unit."""
    if x is None:
        return "--"
    spec = ".1f" if metric and key == "dailyrainin" else spec
    return f"{format(U.convert(key, x, metric), spec)}{U.suffix(key, metric)}"


def _table(rows: list[list[str]], widths=(2.6, 2.2)) -> Table:
    t = Table(rows, colWidths=[w * inch for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(ACCENT_COLOR)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9ca3af")),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
    ]))
    return t


def _doc(buf: BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(buf, pagesize=letter, leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                             topMargin=0.75 * inch, bottomMargin=0.75 * inch, title=title)


def _stats(rows) -> dict:
    """Totals for a list of (date, daily summary) pairs. Missing values are skipped."""
    summaries = [r for _, r in rows]

    def vals(key):
        return [r[key] for r in summaries if r.get(key) is not None]

    tmax, tmin, tavg = vals("tempf_max"), vals("tempf_min"), vals("tempf_avg")
    rain, gust, sun = vals("rain_in"), vals("gust_max"), vals("sun_hours")
    return {
        "days": len(summaries),
        "high": max(tmax) if tmax else None,
        "low": min(tmin) if tmin else None,
        "avg": sum(tavg) / len(tavg) if tavg else None,
        "rain": sum(rain) if rain else None,
        "rainy": sum(1 for x in rain if x >= RAINY_IN),
        "gust": max(gust) if gust else None,
        "sun": sum(sun) if sun else None,
        "hot": sum(1 for x in tmax if x >= 110),
        "cold": sum(1 for x in tmin if x <= 32),
        "windy": sum(1 for x in gust if x >= 20),
    }


def _summary_rows(st: dict, metric: bool) -> list[list[str]]:
    return [
        ["Days with data", str(st["days"])],
        ["High", _shown("tempf", st["high"], metric, ".0f")],
        ["Low", _shown("tempf", st["low"], metric, ".0f")],
        ["Average", _shown("tempf", st["avg"], metric, ".1f")],
        ["Total rain", _shown("dailyrainin", st["rain"], metric, ".2f")],
        ["Highest gust", _shown("windgustmph", st["gust"], metric, ".0f")],
        ["Total sun hours", _value(st["sun"], " h", ".1f")],
    ]


def _extreme_rows(st: dict, metric: bool) -> list[list[str]]:
    return [
        ["Event", "Days"],
        [f"High at or above {_shown('tempf', 110, metric, '.0f')}", str(st["hot"])],
        [f"Low at or below {_shown('tempf', 32, metric, '.0f')}", str(st["cold"])],
        [f"Rain of {_shown('dailyrainin', RAINY_IN, metric, '.1f')} or more", str(st["rainy"])],
        [f"Gusts of {_shown('windgustmph', 20, metric, '.0f')} or more", str(st["windy"])],
    ]


def daily_pdf(day_label: str, summary: dict, current: dict | None = None, metric: bool = False) -> bytes:
    """A PDF for one day. `summary` is the daily summary; `current` is the latest reading, or None."""
    buf = BytesIO()
    doc = _doc(buf, f"Weather report {day_label}")
    styles = getSampleStyleSheet()
    story = [Paragraph("Daily Weather Report", styles["Title"]),
             Paragraph(f"Date: {html.escape(day_label)}", styles["Normal"]),
             Spacer(1, 0.25 * inch)]

    if current:
        story += [Paragraph("Current conditions", styles["Heading2"]), _table([
            ["Metric", "Value"],
            ["Temperature", _shown("tempf", current.get("tempf"), metric, ".1f")],
            ["Humidity", _value(current.get("humidity"), "%", ".0f")],
            ["Wind", _shown("windspeedmph", current.get("windspeedmph"), metric, ".1f")],
            ["Gust", _shown("windgustmph", current.get("windgustmph"), metric, ".1f")],
            ["Rain today", _shown("dailyrainin", current.get("dailyrainin"), metric, ".2f")],
        ]), Spacer(1, 0.25 * inch)]

    humidity = f"{_value(summary.get('humidity_min'), '%', '.0f')} to {_value(summary.get('humidity_max'), '%', '.0f')}"
    story += [Paragraph("Daily statistics", styles["Heading2"]), _table([
        ["Statistic", "Value"],
        ["High", _shown("tempf", summary.get("tempf_max"), metric, ".0f")],
        ["Low", _shown("tempf", summary.get("tempf_min"), metric, ".0f")],
        ["Average", _shown("tempf", summary.get("tempf_avg"), metric, ".0f")],
        ["Rain", _shown("dailyrainin", summary.get("rain_in"), metric, ".2f")],
        ["Wind run", _shown("miles", summary.get("wind_run_mi"), metric, ".1f")],
        ["Gust max", _shown("windgustmph", summary.get("gust_max"), metric, ".0f")],
        ["Sun hours", _value(summary.get("sun_hours"), " h", ".1f")],
        ["Humidity", humidity],
    ]), Spacer(1, 0.3 * inch),
        Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", styles["Italic"])]

    doc.build(story)
    return buf.getvalue()


def monthly_pdf(year: int, month: int, rows, metric: bool = False) -> bytes:
    """A PDF for one month. `rows` is (date, daily summary) pairs for that month."""
    label = datetime(year, month, 1).strftime("%B %Y")
    st = _stats(rows)
    buf = BytesIO()
    doc = _doc(buf, f"Monthly weather report {label}")
    styles = getSampleStyleSheet()
    story = [Paragraph("Monthly Weather Report", styles["Title"]),
             Paragraph(html.escape(label), styles["Heading3"]), Spacer(1, 0.2 * inch),
             Paragraph("Summary", styles["Heading2"]), _table([["Metric", "Value"], *_summary_rows(st, metric)]),
             Spacer(1, 0.25 * inch),
             Paragraph("Extreme days", styles["Heading2"]), _table(_extreme_rows(st, metric)),
             Spacer(1, 0.3 * inch),
             Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", styles["Italic"])]
    doc.build(story)
    return buf.getvalue()


def yearly_pdf(year: int, rows, metric: bool = False) -> bytes:
    """A PDF for one year, with a month-by-month breakdown. `rows` is (date, daily summary) pairs."""
    st = _stats(rows)
    by_month = defaultdict(list)
    for day, summary in rows:
        by_month[day.month].append((day, summary))

    breakdown = [["Month", "Average", "High", "Low", "Rain", "Rainy days"]]
    for m in range(1, 13):
        if by_month[m]:
            ms = _stats(by_month[m])
            breakdown.append([datetime(year, m, 1).strftime("%B"), _shown("tempf", ms["avg"], metric, ".0f"),
                              _shown("tempf", ms["high"], metric, ".0f"), _shown("tempf", ms["low"], metric, ".0f"),
                              _shown("dailyrainin", ms["rain"], metric, ".2f"), str(ms["rainy"])])

    buf = BytesIO()
    doc = _doc(buf, f"Yearly weather report {year}")
    styles = getSampleStyleSheet()
    story = [Paragraph("Yearly Weather Report", styles["Title"]),
             Paragraph(str(year), styles["Heading3"]), Spacer(1, 0.2 * inch),
             Paragraph("Summary", styles["Heading2"]), _table([["Metric", "Value"], *_summary_rows(st, metric)]),
             Spacer(1, 0.25 * inch),
             Paragraph("Extreme days", styles["Heading2"]), _table(_extreme_rows(st, metric)),
             Spacer(1, 0.25 * inch)]
    if len(breakdown) > 1:
        story += [Paragraph("Monthly breakdown", styles["Heading2"]),
                  _table(breakdown, widths=(1.4, 1.0, 0.9, 0.9, 1.0, 1.2)), Spacer(1, 0.3 * inch)]
    story.append(Paragraph(f"Generated {datetime.now():%Y-%m-%d %H:%M}", styles["Italic"]))
    doc.build(story)
    return buf.getvalue()
