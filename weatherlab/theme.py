"""The dashboard's look, copied so Weather Lab matches it. Each value's source is listed in SOURCES.md.

Two sets of colours, as in the dashboard:
- page colours (background, surface, border, text, accent) from utils/theme.py, used for the page and Streamlit's own
  controls (buttons, inputs, tabs, sidebar);
- card colours (tiles, lines, muted text) from utils/live_cards.py, used for the tiles and gauges.
Colour schemes change both sets, as they do in the dashboard.
"""

import html as _html
import math
import re
import time

import streamlit as st


FONT = "Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"  # tiles and headings (utils/live_cards.py)

# Shape and depth (0.37.33): one set of corner sizes and shadows used everywhere, so every card looks the same.
RADIUS = {"sm": 10, "md": 14, "lg": 18, "pill": 99}
SHADOW = {True: "0 1px 2px rgba(0,0,0,.35),0 8px 24px rgba(0,0,0,.22)",
          False: "0 1px 2px rgba(16,24,40,.06),0 8px 24px rgba(16,24,40,.07)"}
SHADOW_HOVER = {True: "0 2px 4px rgba(0,0,0,.4),0 14px 32px rgba(0,0,0,.3)",
                False: "0 2px 4px rgba(16,24,40,.08),0 14px 32px rgba(16,24,40,.11)"}

# Card colours (utils/live_cards.py _k).
LIGHT = {"page": "#ffffff", "surface": "#f8f9fa", "text": "#1c2330", "muted": "#5b6472",
         "card": "#ffffff", "line": "#e3e7ee", "sub": "#f4f6f9", "accent": "#4ea1ff"}
DARK = {"page": "#0e1117", "surface": "#161b22", "text": "#e8eaed", "muted": "#9aa3b0",
        "card": "#161b24", "line": "#262d3a", "sub": "#1b2130", "accent": "#4ea1ff"}

# Page colours (utils/theme.py LIGHT_PALETTE and DARK_PALETTE).
PAGE_LIGHT = {"background": "#ffffff", "surface": "#f8f9fa", "border": "#e0e0e0",
              "text": "#1a1a1a", "text_muted": "#666666", "accent": "#4ea1ff"}
PAGE_DARK = {"background": "#0e1117", "surface": "#161b22", "border": "#30363d",
             "text": "#e0e0e0", "text_muted": "#999999", "accent": "#4ea1ff"}

# Selected pill-tab colours (wxdash/live_glue.py inject_style): background, text.
TAB_ON = {True: ("#23324a", "#ffffff"), False: ("#e6eefb", "#17325c")}

DOT_COLORS = {"ok": "#3ddc84", "slow": "#f6d55c", "silent": "#e5633c"}

# Colour schemes (utils/theme.py COLOR_SCHEMES), copied exactly.
SCHEMES = {
    "Default": {},
    # New for this app, not from the dashboard: black or white text on plain backgrounds with strong lines.
    "High contrast": {
        "light": {"background": "#ffffff", "surface": "#f0f0f0", "border": "#000000",
                  "text": "#000000", "text_muted": "#2b2b2b", "accent": "#0030c8",
                  "success": "#006b2e", "warning": "#8a5a00", "error": "#b00020", "info": "#0030c8"},
        "dark": {"background": "#000000", "surface": "#0d0d0d", "border": "#ffffff",
                 "text": "#ffffff", "text_muted": "#dcdcdc", "accent": "#6cb8ff",
                 "success": "#5dff8a", "warning": "#ffd84d", "error": "#ff7b7b", "info": "#6cb8ff"},
    },
    "Ocean": {
        "light": {"background": "#f5fbfd", "surface": "#e5f3f8", "border": "#bcdde8",
                  "accent": "#0b8fb0", "info": "#38a9d8"},
        "dark": {"background": "#0a1620", "surface": "#102230", "border": "#1f3d54",
                 "accent": "#2dd4f0", "info": "#7dd3fc"},
    },
    "Desert": {
        "light": {"background": "#fffaf4", "surface": "#f8ebde", "border": "#e6cdb4",
                  "accent": "#cf5a24", "info": "#d98a3d"},
        "dark": {"background": "#16100c", "surface": "#221812", "border": "#3d2b1f",
                 "accent": "#f28c4e", "info": "#f0b27a"},
    },
    "Forest": {
        "light": {"background": "#f6fbf7", "surface": "#e4f1e8", "border": "#bfdcc8",
                  "accent": "#2a7d52", "info": "#4a9d78"},
        "dark": {"background": "#0b140f", "surface": "#122019", "border": "#21392b",
                 "accent": "#4fd18b", "info": "#86e0b0"},
    },
    "Violet": {
        "light": {"background": "#faf8ff", "surface": "#eee9fa", "border": "#d6cbef",
                  "accent": "#7048d6", "info": "#8f6fe0"},
        "dark": {"background": "#110e1b", "surface": "#1a1530", "border": "#312850",
                 "accent": "#a78bfa", "info": "#c4b5fd"},
    },
}

TEXT_SELECTORS = (".stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp h5,.stApp h6,.stApp p,.stApp label,"
                  ".stApp li,.stApp span,[data-testid='stMarkdownContainer'],[data-testid='stMetricValue'],"
                  "[data-testid='stMetricLabel'],[data-testid='stWidgetLabel']")
INPUT_SELECTORS = ("[data-baseweb='select']>div,[data-baseweb='input']>div,.stTextInput input,"
                   ".stNumberInput input,.stDateInput input")

# Phone and tablet layout (utils/theme.py apply_mobile_css), then the card-tile sizes for phones.
MOBILE_CSS = (
    "@media (max-width:900px){"
    ".block-container{padding:1.25rem 1rem 3rem 1rem !important}"
    ".stApp h1{font-size:1.7rem !important;line-height:1.25 !important}"
    ".stApp h2{font-size:1.35rem !important}"
    ".stApp h3{font-size:1.15rem !important}"
    ".wx-sec h3{font-size:18px !important}"
    "[data-testid='stTabs'] [data-baseweb='tab-list']{overflow-x:auto;flex-wrap:nowrap;scrollbar-width:none}"
    "[data-testid='stTabs'] button{padding:0.6rem 0.9rem !important;white-space:nowrap}"
    "[data-testid='stDataFrame'],[data-testid='stTable']{overflow-x:auto}"
    "iframe{max-width:100% !important}"
    ".js-plotly-plot,.stPlotlyChart{max-width:100% !important}"
    "}"
    "@media (max-width:640px){"
    ".block-container{padding:1rem 0.75rem 3rem 0.75rem !important}"
    "[data-testid='stHorizontalBlock']{flex-wrap:wrap !important;gap:0.75rem !important}"
    "[data-testid='stColumn'],[data-testid='column']{min-width:100% !important;flex:1 1 100% !important;width:100% !important}"
    ".stButton>button,.stDownloadButton>button,[data-testid='stFormSubmitButton']>button{min-height:48px !important;font-size:1rem !important}"
    "[data-testid='stRadio'] label,[data-testid='stCheckbox'] label{min-height:44px;align-items:center;padding:0.25rem 0 !important}"
    "[data-testid='stRadio'] [role='radiogroup'][aria-orientation='horizontal'],"
    "[data-testid='stRadio']>div[role='radiogroup']{flex-wrap:wrap;gap:0.25rem 1rem}"
    "[data-baseweb='select']>div,.stTextInput input,.stNumberInput input,.stDateInput input{min-height:46px !important;font-size:16px !important}"
    "[data-testid='stMetricValue']{font-size:1.5rem !important}"
    "[data-testid='stColumn']:has([data-testid='stMetric']):not(:has([data-testid='stPlotlyChart'],iframe,[data-testid='stDataFrame'])){"
    "min-width:calc(50% - 0.5rem) !important;flex:1 1 calc(50% - 0.5rem) !important;width:calc(50% - 0.5rem) !important}"
    ".wl-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}"
    ".wl-value{font-size:18px}.wl-title{font-size:22px}.wl-tile{padding:8px 10px}"
    "}"
)


def _rule(selector: str, declarations: str) -> str:
    return f"{selector}{{{declarations}}}"


def page_palette(dark: bool, scheme: str = "Default") -> dict:
    """Page colours for the chosen mode and scheme, as the dashboard's get_palette() gives them."""
    base = dict(PAGE_DARK if dark else PAGE_LIGHT)
    base.update(SCHEMES.get(scheme, {}).get("dark" if dark else "light", {}))
    return base


def palette(dark: bool, scheme: str = "Default") -> dict:
    """Card colours for the chosen mode and scheme (tiles, lines, muted text)."""
    base = dict(DARK if dark else LIGHT)
    over = SCHEMES.get(scheme, {}).get("dark" if dark else "light", {})
    for src, dst in (("background", "page"), ("surface", "surface"), ("border", "line"),
                     ("text", "text"), ("text_muted", "muted"), ("accent", "accent")):
        if src in over:
            base[dst] = over[src]
    return base


def is_dark(mode: str | None = None) -> bool:
    """mode is "light", "dark", or "auto". With no mode, the saved Settings choice is used.
    Auto follows Streamlit's theme, the same way the dashboard does."""
    if mode is None:
        from weatherlab.settings import load_settings
        mode = load_settings().theme_mode
    if mode == "dark":
        return True
    if mode == "light":
        return False
    try:
        return st.context.theme.type == "dark"
    except Exception:
        pass
    try:
        return st.get_option("theme.base") == "dark"
    except Exception:
        return False


def css(dark: bool, scheme: str = "Default", compact: bool = False, large: bool = False) -> str:
    pg = page_palette(dark, scheme)
    p = palette(dark, scheme)
    tab_bg, tab_text = TAB_ON[bool(dark)]
    shadow, shadow_hover = SHADOW[bool(dark)], SHADOW_HOVER[bool(dark)]
    if scheme == "High contrast":  # strong lines matter more than depth here
        shadow = shadow_hover = "none"
    rules = [
        # Page and sidebar (utils/theme.py apply_theme_css)
        _rule(".stApp", f"background:{pg['background']}"),
        _rule("[data-testid='stHeader']", f"background:{pg['background']}"),
        _rule("[data-testid='stSidebar'],[data-testid='stSidebar']>div", f"background:{pg['surface']}"),
        _rule(TEXT_SELECTORS, f"color:{pg['text']} !important"),
        _rule("[data-testid='stTabs'] button", f"color:{pg['text_muted']} !important"),
        _rule("[data-testid='stTabs'] button[aria-selected='true']", f"color:{pg['accent']} !important"),
        _rule(".stApp hr", f"border-color:{pg['border']} !important"),
        _rule(INPUT_SELECTORS, f"background-color:{pg['surface']} !important;color:{pg['text']} !important;"
                               f"border-color:{pg['border']} !important"),
        _rule(".stButton>button", f"background-color:{pg['surface']} !important;color:{pg['text']} !important;"
                                  f"border:1px solid {pg['border']} !important"),
        # Pill tabs, button groups, card containers, alerts and metrics (wxdash/live_glue.py inject_style)
        _rule("div[data-baseweb='tab-list'],div[data-testid='stTabs'] [role='tablist']",
              "gap:6px;border-bottom:none !important;box-shadow:none !important"),
        _rule("div[data-baseweb='tab-list'] button[role='tab'],div[data-testid='stTab']",
              f"border:1px solid {p['line']} !important;border-radius:99px !important;padding:6px 16px !important;"
              "margin-bottom:8px"),
        _rule("div[data-baseweb='tab-list'] button[role='tab'][aria-selected='true'],"
              "div[data-testid='stTab'][aria-selected='true']",
              f"background:{tab_bg};border-color:transparent !important"),
        _rule("div[data-baseweb='tab-list'] button[role='tab'][aria-selected='true'] p,"
              "div[data-testid='stTab'][aria-selected='true'] p", f"color:{tab_text} !important"),
        _rule("div[data-testid='stTab']::after,div[data-testid='stTab']::before", "display:none !important"),
        _rule("div[data-baseweb='tab-highlight'],div[data-baseweb='tab-border']", "display:none !important"),
        _rule("div[data-testid='stTabs'] .react-aria-SelectionIndicator", "display:none !important"),
        _rule("div[data-testid='stButtonGroup']>div", "gap:6px !important;flex-wrap:wrap"),
        _rule("div[data-testid='stButtonGroup'] button",
              f"border:1px solid {p['line']} !important;border-radius:99px !important;padding:6px 16px !important;"
              "margin:0 0 8px 0 !important;background:transparent !important"),
        _rule("div[data-testid='stButtonGroup'] button[aria-checked='true']",
              f"background:{tab_bg} !important;border-color:transparent !important"),
        _rule("div[data-testid='stButtonGroup'] button[aria-checked='true'] p", f"color:{tab_text} !important"),
        _rule("div[data-testid='stVerticalBlockBorderWrapper']:has(>div>div[data-testid='stVerticalBlock'])",
              f"border-radius:{RADIUS['lg']}px !important;border-color:{p['line']}99 !important;background:{p['card']};"
              f"box-shadow:{shadow}"),
        _rule("div[data-testid='stLayoutWrapper']>div[data-testid='stVerticalBlock']",
              f"border-radius:{RADIUS['lg']}px !important;border-color:{p['line']}99 !important"),
        _rule("div[data-testid='stAlert']", f"padding:2px 4px !important;border-radius:{RADIUS['md']}px !important"),
        _rule(".stButton>button,.stDownloadButton>button", f"border-radius:{RADIUS['sm']}px !important;"
                                                           "transition:background .15s,border-color .15s"),
        _rule("[data-testid='stExpander'] details", f"border-radius:{RADIUS['md']}px !important;"
                                                    f"border-color:{p['line']}99 !important"),
        # Sidebar (0.37.33): slimmer, with a tinted pill for the page you're on and small section names.
        _rule("[data-testid='stSidebar']", f"min-width:232px !important;max-width:260px !important;"
                                           f"border-right:1px solid {p['line']}66"),
        _rule("[data-testid='stSidebarNavLink']", f"border-radius:{RADIUS['sm']}px;padding:6px 10px !important;"
                                                  "margin:1px 0;transition:background .15s"),
        _rule("[data-testid='stSidebarNavLink'][aria-current='page']", f"background:{p['accent']}26 !important"),
        _rule("[data-testid='stSidebarNavLink'][aria-current='page'] span", f"color:{p['accent']} !important;"
                                                                            "font-weight:650"),
        _rule("[data-testid='stNavSectionHeader']", f"font-size:11px !important;font-weight:650 !important;"
                                                    f"letter-spacing:.08em;text-transform:uppercase;"
                                                    f"color:{p['muted']} !important;margin-top:10px"),
        _rule("div[data-testid='stAlert'] p", "font-size:14px !important"),
        _rule("div[data-testid='stMetricValue']", "font-size:1.6rem !important;font-weight:650 !important"),
        _rule("div[data-testid='stMetricLabel'] p", f"color:{p['muted']} !important;font-size:13px !important"),
        # Card tiles and headings (utils/page_look.py, utils/live_cards.py)
        _rule(".wl-title", f"font-family:{FONT};font-size:26px;font-weight:700;letter-spacing:-.4px;"
                           f"color:{p['text']};margin:4px 0 14px"),
        _rule(".wl-sub", f"font-family:{FONT};font-size:15px;color:{p['muted']};margin:-6px 0 18px"),
        _rule(".wl-grid", "display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:12px"),
        _rule(".wl-tile", f"font-family:{FONT};background:{p['card']};border:1px solid {p['line']}99;"
                          f"border-radius:{RADIUS['md']}px;padding:14px 16px;min-width:0;box-shadow:{shadow};"
                          "transition:box-shadow .2s,transform .2s"),
        _rule(".wl-tile:hover", f"box-shadow:{shadow_hover};transform:translateY(-1px)"),
        _rule(".wl-label", f"font-size:12px;font-weight:500;letter-spacing:.02em;color:{p['muted']}"),
        _rule(".wl-value", f"font-size:26px;font-weight:700;letter-spacing:-.4px;color:{p['text']};margin-top:4px;"
                           "font-variant-numeric:tabular-nums;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"),
        # The briefing headline on Home: a soft accent wash so it reads as the page's lead.
        _rule(".wl-card", f"font-family:{FONT};background:linear-gradient(135deg,{p['accent']}22,{p['card']} 70%);"
                          f"border:1px solid {p['line']}99;border-radius:{RADIUS['lg']}px;padding:18px 20px;"
                          f"margin-bottom:12px;box-shadow:{shadow};color:{p['text']};line-height:1.35"),
        # Loading placeholders: grey shapes that shimmer while a slow part of the page loads.
        _rule(".wl-skel", f"border-radius:{RADIUS['md']}px;background:linear-gradient(90deg,{p['line']}66 0%,"
                          f"{p['line']}cc 50%,{p['line']}66 100%);background-size:200% 100%;margin-bottom:10px"),
        _rule(".wl-status", f"font-size:12px;color:{p['muted']};margin-top:6px"),
        _rule(".wl-note", f"font-size:14px;color:{p['muted']}"),
        _rule(".wx-sec", "display:flex;flex-wrap:wrap;align-items:baseline;gap:2px 10px;margin:6px 0 6px"),
        _rule(".wx-sec h3", "white-space:nowrap;margin:0 !important;padding:0 !important;"
                             "font-size:18px !important;font-weight:650 !important"),
        _rule(".wx-sec span", f"font-size:13px;color:{p['muted']}"),
        _rule("[data-testid='stDataFrame'],[data-testid='stTable']",
              f"border:1px solid {p['line']}99;border-radius:{RADIUS['md']}px;overflow:hidden"),
        _rule(".wl-table-wrap", f"overflow-x:auto;border:1px solid {p['line']}99;border-radius:{RADIUS['md']}px;"
                                f"margin-bottom:12px;box-shadow:{shadow}"),
        _rule(".wl-table", f"width:100%;border-collapse:collapse;font-size:15px;color:{p['text']}"),
        _rule(".wl-table th", f"text-align:left;font-size:13px;font-weight:600;color:{p['muted']};"
                              f"background:{p['sub']};padding:9px 12px;white-space:nowrap"),
        _rule(".wl-table td", f"padding:9px 12px;border-top:1px solid {p['line']};vertical-align:middle"),
        _rule(".wl-table .wl-num", "text-align:right;font-variant-numeric:tabular-nums"),
        _rule("[data-testid='stImage'] img", f"width:100%;height:auto;border-radius:{RADIUS['md']}px"),
        # A dial that opens its history when clicked: the real button is drawn invisibly over the whole dial.
        _rule("[class*='st-key-wcard-']", "position:relative;border-radius:14px;transition:background .15s"),
        _rule("[class*='st-key-wcard-']:hover", f"background:{p['line']}33"),
        # The real button is stretched over the whole dial. Streamlit's boxes around a button are skipped
        # (display:contents) so the button is positioned against the dial itself and the boxes leave no gap.
        _rule("[class*='st-key-wcard-'] .stElementContainer:has([data-testid='stButton']),"
              "[class*='st-key-wcard-'] [data-testid='stButton']", "display:contents !important"),
        _rule("[class*='st-key-wcard-'] [data-testid='stButton'] button",
              "position:absolute;inset:0;width:100%;height:100%;opacity:0;cursor:pointer;min-height:0;z-index:1"),
        "@keyframes wl-sweep{from{stroke-dasharray:0.001,var(--c)}to{stroke-dasharray:var(--v),var(--c)}}",
        "@media (prefers-reduced-motion:no-preference){.wl-sweep{animation:wl-sweep .9s ease-out}}",
        # A gentle fade as a page opens: on the title, its line and the briefing, which are drawn once per page.
        "@keyframes wl-fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}",
        "@keyframes wl-shimmer{from{background-position:200% 0}to{background-position:-200% 0}}",
        "@media (prefers-reduced-motion:no-preference){.wl-title,.wl-sub,.wl-card{animation:wl-fade .35s ease-out both}"
        ".wl-skel{animation:wl-shimmer 1.4s linear infinite}}",
    ]
    if large:
        rules += ["html{font-size:118%}", ".wl-title{font-size:32px !important}", ".wl-label{font-size:15px !important}",
                  ".wl-value{font-size:28px !important}", ".wl-note,.wl-status{font-size:16px !important}",
                  ".wx-sec h3{font-size:22px !important}"]
    extra = ".wl-grid{gap:6px;margin-bottom:6px}" if compact else ""
    # One line, no indentation: Streamlit shows indented lines as code.
    return "<style>" + "".join(rules) + MOBILE_CSS + extra + "</style>"


def skeleton_html(heights: tuple = (72, 96)) -> str:
    """Grey shimmering shapes to stand in for a part of the page that is still loading."""
    return "".join(f'<div class="wl-skel" style="height:{h}px" aria-hidden="true"></div>' for h in heights)


def title_html(text: str) -> str:
    return f'<div class="wl-title">{text}</div>'


def page_head(title: str, subtitle: str = "") -> str:
    """A page's title, with one line under it saying what the page shows."""
    sub = f'<div class="wl-sub">{_html.escape(subtitle)}</div>' if subtitle else ""
    return f'<div class="wl-title">{title}</div>{sub}'


def tile_html(label: str, value: str) -> str:
    return (f'<div class="wl-tile"><div class="wl-label">{label}</div>'
            f'<div class="wl-value">{value}</div></div>')


STRIP_NEUTRAL = "#9aa3b0"


# The word that goes with each tone, so the level is readable without the colour.
TONE_WORD = {"ok": "Good", "warn": "Watch", "bad": "Alert", "info": "Info"}


def strip_tile_html(label: str, value: str, note: str = "", tone: str | None = None, word: str | None = None) -> str:
    """A summary tile with a coloured left edge: ok, warn, bad (red), info, or grey with no tone. The tone's word
    (Good, Watch, Alert, Info) follows the note; pass word="" when the value or note already names the level."""
    key = "fail" if tone == "bad" else tone
    colour = HEALTH_DOT.get(key, STRIP_NEUTRAL) if key else STRIP_NEUTRAL
    if word is None:
        word = TONE_WORD.get(tone, "") if tone else ""
    text = " · ".join(part for part in (note, word) if part)
    label_html = _html.escape(label)
    body = tile_html(label_html, _html.escape(value)).replace(
        'class="wl-tile"', f'class="wl-tile" style="border-left:4px solid {colour}"', 1)
    if text:
        body = body.replace("</div></div>", f'</div><div class="wl-label">{_html.escape(text)}</div></div>')
    return body


def grid_html(tiles: list[str]) -> str:
    return f'<div class="wl-grid">{"".join(tiles)}</div>'


def gauge_html(value, lo: float, hi: float, label: str, fmt: str, dark: bool, animate: bool = False) -> str:
    """A round gauge in a tile. The arc fills from lo to hi and is clamped at both ends."""
    p = DARK if dark else LIGHT
    frac = 0.0 if value is None else max(0.0, min(1.0, (value - lo) / (hi - lo)))
    r = 44
    circ = 2 * math.pi * r
    text = "--" if value is None else fmt.format(value)
    sweep = f' class="wl-sweep" style="--v:{circ * frac:.1f};--c:{circ:.1f}"' if animate else ""
    return ('<div class="wl-tile" style="text-align:center">'
            '<svg viewBox="0 0 120 120" width="100%" style="max-width:120px;display:block;margin:0 auto">'
            f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="{p["line"]}" stroke-width="10"/>'
            f'<circle cx="60" cy="60" r="{r}" fill="none" stroke="{p["accent"]}" stroke-width="10" '
            f'stroke-linecap="round" stroke-dasharray="{circ * frac:.1f},{circ:.1f}" transform="rotate(-90 60 60)"'
            f'{sweep}/>'
            f'<text x="60" y="68" text-anchor="middle" font-family="{FONT}" font-size="22" '
            f'font-weight="650" fill="{p["text"]}">{text}</text></svg>'
            f'<div class="wl-label" style="margin-top:4px">{label}</div></div>')


def status_dot(state: str) -> str:
    """A small colored dot: ok (green), slow (yellow), silent (red), anything else grey."""
    color = DOT_COLORS.get(state, "#9aa3b0")
    return (f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
            f'background:{color};margin-right:6px;vertical-align:middle"></span>')


HEALTH_DOT = {"ok": "#2fbf71", "warn": "#e0a526", "fail": "#e5533d", "info": "#4ea1ff"}

# Numbers, times and "--" placeholders: a column of only these is right-aligned.
_NUMERIC = re.compile(r"[-+]?[\d.,:]+\s*(?:%|°[FC]?|in|mm|mph|km/h|h|m|W/m²)?|--")


def state_html(state: str, label: str) -> str:
    """A coloured dot with its word beside it, so a status never relies on colour alone."""
    color = HEALTH_DOT.get(state, "#9aa3b0")
    return (f'<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:{color};'
            f'margin-right:7px;vertical-align:middle"></span><span style="vertical-align:middle">'
            f'{_html.escape(label)}</span>')


SORT_MIN_ROWS = 6  # a table shorter than this isn't worth a sort control


def table(rows: list[dict], html_cols: tuple[str, ...] = (), sort_key: str | None = None) -> None:
    """The one table style every page uses. Text is escaped; a column in html_cols already holds markup, such as
    state_html. A column whose cells are all numbers or times is right-aligned. With a sort_key (unique on the
    page) and enough rows, a Sort by control orders the rows by the value in each readable column (0.37.45)."""
    if not rows:
        return
    if sort_key and len(rows) >= SORT_MIN_ROWS:
        from weatherlab import table_sort
        choices = [c for c in table_sort.sortable_columns(rows) if c not in html_cols]
        if choices:
            left, right = st.columns([3, 2], vertical_alignment="bottom")
            by = left.selectbox("Sort by", ["Original order", *choices], key=f"sort_by_{sort_key}")
            high = right.toggle("Highest first", value=True, key=f"sort_high_{sort_key}")
            if by != "Original order":
                rows = table_sort.sort_rows(rows, by, high)
    cols = list(rows[0].keys())
    numeric = {c for c in cols if c not in html_cols and all(_NUMERIC.fullmatch(str(r[c])) for r in rows)}
    head = "".join(f'<th class="{"wl-num" if c in numeric else ""}">{_html.escape(str(c))}</th>' for c in cols)
    body = ""
    for r in rows:
        cells = ""
        for c in cols:
            value = str(r[c]) if c in html_cols else _html.escape(str(r[c]))
            cells += f'<td class="{"wl-num" if c in numeric else ""}">{value}</td>'
        body += f"<tr>{cells}</tr>"
    # One line, no indentation: Streamlit shows indented lines as code.
    st.markdown(f'<div class="wl-table-wrap"><table class="wl-table"><thead><tr>{head}</tr></thead>'
                f'<tbody>{body}</tbody></table></div>', unsafe_allow_html=True)


def is_phone() -> bool:
    """True when the page is open on a phone, judged from the browser's User-Agent (wxdash/common.py is_phone)."""
    try:
        ua = (st.context.headers.get("User-Agent") or "").lower()
    except Exception:
        return False
    return any(k in ua for k in ("iphone", "ipod", "android", "mobile"))


def freshness_html(updated: float | None) -> str:
    """'updated 3 min ago' chip: green under 15 minutes, amber under an hour, red after (wxdash/live_glue.py)."""
    if updated is None:
        return ""
    mins = max(0.0, (time.time() - updated) / 60)
    if mins < 60:
        txt = f"updated {int(mins)} min ago" if mins >= 1 else "updated just now"
    else:
        txt = f"updated {mins / 60:.1f} h ago"
    color, bg = (("#15803d", "#dcfce7") if mins < 15
                 else (("#b45309", "#fef3c7") if mins < 60 else ("#b91c1c", "#fee2e2")))
    return (f'<span style="font-size:12px;font-weight:600;padding:2px 9px;border-radius:99px;'
            f'color:{color};background:{bg};margin-left:6px">{_html.escape(txt)}</span>')


def section_html(title: str, note: str = "", updated: float | None = None) -> str:
    """A calm section heading with an optional note and freshness chip (wxdash/live_glue.py section)."""
    return (f'<div class="wx-sec"><h3>{_html.escape(title)}</h3><span>{_html.escape(note)}</span>'
            f'{freshness_html(updated)}</div>')
