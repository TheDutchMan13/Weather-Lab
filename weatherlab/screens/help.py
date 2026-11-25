"""Help and glossary: plain-words explanations of the terms shown next to the numbers."""
import html

import streamlit as st

from weatherlab import glossary, hero, line_icons, theme

# One line icon for each term (0.37.66).
TERM_ICONS = {"dew_point": "drop", "feels_like": "thermo", "heat_index": "thermo", "wind_chill": "wind",
              "humidity": "drop", "gust": "wind", "pressure": "gauge", "rain_rate": "rain", "daily_rain": "rain",
              "uv_index": "sun", "aqi": "wind", "usual": "calendar", "lightning": "bolt", "frost": "thermo",
              "stuck": "alert"}


def _rows(found: list[dict]) -> str:
    """The terms in A-to-Z order, a letter above each group, each as a row with its icon, name and meaning."""
    out, letter = [], ""
    for t in sorted(found, key=lambda t: t["name"].lower()):
        first = t["name"][:1].upper()
        if first != letter:
            letter = first
            out.append(f'<div class="wl-letter">{html.escape(letter)}</div>')
        out.append(f'<div class="wl-panel wl-term"><span class="wl-ti">{line_icons.icon(TERM_ICONS.get(t["key"], "info"), 30, "#38c6ec")}</span>'
                   f'<b>{html.escape(t["name"])}</b><span class="wl-tx">{html.escape(t["long"])}</span></div>')
    return "".join(out)


def _link(label: str, page: str, tab: str | None, icon: str) -> None:
    target = st.session_state.get("wl_pages", {}).get(page)
    if target is not None:
        st.page_link(target, label=label, icon=icon, query_params={"tab": tab} if tab else None)


def help_page() -> None:
    st.markdown(theme.page_head("Help and glossary", "What the terms next to the numbers mean."), unsafe_allow_html=True)
    book = line_icons.icon("info", 60, "#e6edf7", 1.5)
    st.markdown(hero.banner_html(book, "Help and glossary", "What the terms next to the numbers mean."), unsafe_allow_html=True)
    typed = st.text_input("Search", placeholder="Search weather terms: try dew, pressure or UV", key="glossary_search",
                          label_visibility="collapsed", icon=":material/search:")
    found = glossary.search(typed)
    if not found:
        st.caption("No term matches. Try a shorter word.")
        return
    st.markdown(_rows(found), unsafe_allow_html=True)
    st.caption("Explanations are general. Your station's numbers come from its own sensors.")
    st.markdown('<div class="wl-panel wl-kvp" style="margin-top:14px"><div class="wl-ph">Getting started: quick links to set up '
                'and get the most from Weather Lab</div></div>', unsafe_allow_html=True)
    a, b, c = st.columns(3)
    with a:
        _link("Station setup: connect your Ecowitt station", "Settings", "station", ":material/sensors:")
    with b:
        _link("Alerts: get notified about important weather", "Settings", "alerts", ":material/notifications:")
    with c:
        _link("Backups: keep a copy of your data and settings", "Data", None, ":material/backup:")
