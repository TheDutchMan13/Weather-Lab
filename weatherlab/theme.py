"""The dashboard's look, copied so Weather Lab matches it. Each value's source is listed in SOURCES.md.

Two sets of colours, as in the dashboard:
- page colours (background, surface, border, text, accent) from utils/theme.py, used for the page and Streamlit's own
  controls (buttons, inputs, tabs, sidebar);
- card colours (tiles, lines, muted text) from utils/live_cards.py, used for the tiles and gauges.
Colour schemes change both sets, as they do in the dashboard.
"""

import html as _html
import re
import time

import streamlit as st


# Manrope, the Android app's font, bundled in static/ (0.37.60) so both apps look alike. Before, Inter was asked for
# but not shipped, so most PCs fell back to Segoe UI.
FONT = "Manrope, Inter, system-ui, -apple-system, 'Segoe UI', sans-serif"  # tiles and headings
FONT_FACE = ("@font-face{font-family:'Manrope';src:url('app/static/manrope.ttf') format('truetype');"
             "font-weight:200 800;font-display:swap}")

# Shape and depth (0.37.33): one set of corner sizes and shadows used everywhere, so every card looks the same.
RADIUS = {"sm": 10, "md": 14, "lg": 18, "pill": 99}
SHADOW = {True: "0 1px 2px rgba(0,0,0,.35),0 8px 24px rgba(0,0,0,.22)",
          False: "0 1px 2px rgba(16,24,40,.06),0 8px 24px rgba(16,24,40,.07)"}
SHADOW_HOVER = {True: "0 2px 4px rgba(0,0,0,.4),0 14px 32px rgba(0,0,0,.3)",
                False: "0 2px 4px rgba(16,24,40,.08),0 14px 32px rgba(16,24,40,.11)"}

# Card colours (utils/live_cards.py _k).
LIGHT = {"page": "#ffffff", "surface": "#f8f9fa", "text": "#1c2330", "muted": "#5b6472",
         "card": "#ffffff", "line": "#e3e7ee", "sub": "#f4f6f9", "accent": "#4ea1ff"}
# Dark is the navy look from the redesign (0.37.62): deep blue page, blue-grey cards, cyan accent.
DARK = {"page": "#0b1828", "surface": "#101a28", "text": "#eaf2fb", "muted": "#9db0c4",
        "card": "#142536", "line": "#2c4357", "sub": "#1a2c3e", "accent": "#38c6ec"}

# Page colours (utils/theme.py LIGHT_PALETTE and DARK_PALETTE).
PAGE_LIGHT = {"background": "#ffffff", "surface": "#f8f9fa", "border": "#e0e0e0",
              "text": "#1a1a1a", "text_muted": "#666666", "accent": "#4ea1ff"}
PAGE_DARK = {"background": "#0b1828", "surface": "#101a28", "border": "#2c4357",
             "text": "#eaf2fb", "text_muted": "#9db0c4", "accent": "#38c6ec"}

# Selected pill-tab colours (wxdash/live_glue.py inject_style): background, text.
TAB_ON = {True: ("#16485b", "#ffffff"), False: ("#e6eefb", "#17325c")}

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
                  ".stApp li,.stApp span:not([style*='color']),[data-testid='stMarkdownContainer'],[data-testid='stMetricValue'],"
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
        # A gentle fade as a page opens: on the title, its line and the briefing, which are drawn once per page.
        "@keyframes wl-fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}",
        "@keyframes wl-shimmer{from{background-position:200% 0}to{background-position:-200% 0}}",
        "@media (prefers-reduced-motion:no-preference){.wl-title,.wl-sub,.wl-card{animation:wl-fade .35s ease-out both}"
        ".wl-skel{animation:wl-shimmer 1.4s linear infinite}}",
    ]
    rules += _redesign_rules(dark, p, pg, tab_bg, tab_text, shadow)
    if large:
        rules += ["html{font-size:118%}", ".wl-title{font-size:32px !important}", ".wl-label{font-size:15px !important}",
                  ".wl-value{font-size:28px !important}", ".wl-note,.wl-status{font-size:16px !important}",
                  ".wx-sec h3{font-size:22px !important}"]
    extra = ".wl-grid{gap:6px;margin-bottom:6px}" if compact else ""
    # One line, no indentation: Streamlit shows indented lines as code.
    return "<style>" + FONT_FACE + "".join(rules) + MOBILE_CSS + extra + "</style>"


def _redesign_rules(dark: bool, p: dict, pg: dict, tab_bg: str, tab_text: str, shadow: str) -> list[str]:
    """The redesign (0.37.62): a softly lit page, a branded sidebar with a filled pill for the page you're on, a header
    bar under each title, tabs as one joined bar, and the Home cards. Uses the scheme's colours, so Light and the
    other schemes get the same shapes."""
    glow = "rgba(56,198,236,.07)" if dark else "rgba(78,161,255,.06)"
    soft = f"{p['line']}aa"
    return [
        _rule(".stApp", f"background:radial-gradient(1200px 600px at 20% -10%,{glow},transparent 60%),{pg['background']} !important"),
        _rule("[data-testid='stHeader']", "background:transparent !important"),
        _rule("[data-testid='stMainBlockContainer']", "position:relative;padding-top:1.6rem !important;max-width:1400px"),
        # Sidebar: brand at the top, cyan section names, a filled pill for the page you're on.
        _rule(".wl-brand", "display:flex;align-items:center;gap:10px;padding:2px 6px 10px"),
        _rule(".wl-brand b", f"display:block;font-family:{FONT};font-size:19px;font-weight:800;letter-spacing:-.3px;"
                             f"color:{p['text']};line-height:1.15"),
        _rule(".wl-brand small", f"display:block;font-size:12.5px;color:{p['muted']}"),
        _rule("[data-testid='stSidebar'] [data-testid='stExpander'] summary p,"
              "[data-testid='stSidebar'] [data-testid='stExpander'] summary span",
              f"color:{p['accent']} !important;opacity:1 !important"),
        _rule("[data-testid='stSidebar'] [data-testid='stPageLink'] a", f"border-radius:{RADIUS['sm']}px;padding:.3rem .6rem !important"),
        _rule("[data-testid='stSidebar'] [data-testid='stPageLink'] a:hover", f"background:{p['line']}55"),
        _rule(".st-key-wl-nav-current a",
              f"background:linear-gradient(90deg,{tab_bg},{tab_bg}cc) !important;box-shadow:inset 0 0 0 1px {p['accent']}55"),
        _rule(".st-key-wl-nav-current a *", f"color:{tab_text} !important;font-weight:650"),
        _rule("[data-testid='stSidebar'] [data-testid='stPageLink'] [data-testid='stIconMaterial']", f"color:{p['muted']}"),
        # Streamlit's own boxes (react-aria in 1.65): select boxes, text boxes and folding headers in the scheme's colours.
        _rule("[data-testid='stSelectbox'] [role='group'],[data-testid='stMultiSelect'] [role='group'],"
              "[data-testid='stTextInput'] [data-baseweb='input'],[data-testid='stTextInput'] input,"
              "[data-testid='stNumberInput'] input,[data-testid='stDateInput'] input,[data-testid='stTextArea'] textarea",
              f"background-color:{p['sub']} !important;color:{p['text']} !important;border-color:{soft} !important"),
        _rule("[data-testid='stDateInputField'],[data-testid='stTimeInput'] [role='group']",
              f"background-color:{p['sub']} !important;color:{p['text']} !important;border-color:{soft} !important"),
        _rule("[data-testid='stDateInputField'] *", f"color:{p['text']} !important"),
        _rule("button[data-testid^='stBaseButton-secondary'],button[data-testid^='stBaseButton-tertiary']:hover",
              f"background-color:{p['card']} !important;color:{p['text']} !important;border-color:{soft} !important"),
        _rule("button[data-testid^='stBaseButton-secondary'] p", f"color:{p['text']} !important"),
        _rule("[data-testid='stTextInputRootElement'],[data-testid='stTextInputRootElement']>div",
              f"background-color:{p['sub']} !important;color:{p['muted']} !important;border-color:{soft} !important"),
        _rule("[data-testid='stSelectbox'] input,[data-testid='stMultiSelect'] input", f"color:{p['text']} !important;background:transparent !important"),
        _rule("[data-testid='stSelectbox'] input::placeholder,[data-testid='stTextInput'] input::placeholder", f"color:{p['muted']} !important"),
        _rule("[data-testid='stSelectbox'] [role='group'] button svg", f"fill:{p['muted']}"),
        _rule("[data-testid='stExpander'] summary", f"background:transparent !important;color:{p['text']} !important"),
        _rule("[data-testid='stExpander'] summary:hover", f"background:{p['line']}44 !important"),
        _rule("[data-testid='stMain'] [data-testid='stExpander'] details", f"background:{p['card']}"),
        # Title row and the bar under it: station, place, and whether the readings are live.
        _rule(".wl-head .wl-title", f"font-family:{FONT};font-size:32px !important;font-weight:800 !important;letter-spacing:-.6px;"
                                   f"margin:0 !important;padding:0 !important;color:{p['text']} !important;line-height:1.15 !important"),
        _rule(".wl-head .wl-sub", "margin:4px 0 14px !important"),
        _rule(".wl-ctx", f"display:flex;flex-wrap:wrap;align-items:center;gap:8px 18px;font-family:{FONT};font-size:15px;"
                         f"color:{p['text']};margin:0 0 16px"),
        _rule(".wl-ctx .wl-chip", f"display:inline-flex;align-items:center;gap:8px;padding:7px 14px;border:1px solid {soft};"
                                  f"border-radius:{RADIUS['sm']}px;background:{p['card']}"),
        _rule(".wl-ctx .wl-sep", f"width:1px;height:20px;background:{soft}"),
        _rule(".wl-ctx .wl-live", "display:inline-flex;align-items:center;gap:8px"),
        _rule(".wl-ctx .wl-live b", "font-weight:750;letter-spacing:.02em"),
        _rule(".wl-ctx .wl-dot", "width:9px;height:9px;border-radius:50%"),
        _rule("div[data-testid='stLayoutWrapper']:has(>.st-key-wl-topright)",
              "position:absolute !important;top:1.6rem;right:1rem;width:auto !important;z-index:5"),
        # Style-only blocks and the 1-pixel head script take no room, so the title sits at the top.
        _rule("[data-testid='stElementContainer']:has(>[data-testid='stMarkdown'] [data-testid='stMarkdownContainer']>style:only-child)",
              "display:none !important"),
        _rule("[data-testid='stElementContainer']:has(>iframe[height='1']),[data-testid='stElementContainer']:has(>[data-testid='stIFrame'][height='1'])",
              "position:absolute !important;width:1px;height:1px;overflow:hidden"),
        _rule(".st-key-wl-topright [data-testid='stHorizontalBlock']", "gap:10px !important;align-items:center"),
        _rule(".st-key-wl-topright p", f"color:{p['muted']} !important;font-size:14px !important;white-space:nowrap;margin:0"),
        _rule(".st-key-wl-topright button", f"border-radius:{RADIUS['sm']}px !important;min-height:38px;padding:0 10px !important;"
                                            f"background:{p['card']} !important;border:1px solid {soft} !important"),
        # Tabs: one joined bar with the open tab filled.
        _rule("div[data-testid='stButtonGroup']:has(button[data-variant='segmented_control'])>div[role='radiogroup']",
              f"gap:4px !important;padding:4px;border:1px solid {soft};border-radius:{RADIUS['md']}px;background:{p['card']};"
              "flex-wrap:wrap;width:100%"),
        _rule("div[data-testid='stButtonGroup'] button[data-variant='segmented_control']",
              f"flex:1 1 auto;border:none !important;border-radius:{RADIUS['sm']}px !important;margin:0 !important;padding:8px 16px !important"),
        _rule("div[data-testid='stButtonGroup'] button[data-variant='segmented_control'][aria-checked='true']",
              f"background:{tab_bg} !important;box-shadow:inset 0 0 0 1px {p['accent']}66"),
        # Cards: the same surface for Streamlit's bordered boxes and the tiles.
        _rule("div[data-testid='stVerticalBlockBorderWrapper']:has(>div>div[data-testid='stVerticalBlock']),"
              ".wl-tile,.wl-card", f"background:{p['card']} !important;border-color:{soft} !important"),
        _rule(".stButton>button[kind='primary'],.stFormSubmitButton>button[kind='primaryFormSubmit']",
              f"background:{p['accent']} !important;color:{'#06202c' if dark else '#ffffff'} !important;border:none !important;font-weight:700"),
        _rule(".stButton>button[kind='primary'] p", f"color:{'#06202c' if dark else '#ffffff'} !important"),
        # Home (0.37.62): the right-now card, the reading cards, Today so far, the 24-hour outlook and the health line.
        _rule(".wl-panel", f"font-family:{FONT};background:{p['card']};border:1px solid {soft};border-radius:{RADIUS['lg']}px;"
                           f"box-shadow:{shadow};color:{p['text']}"),
        _rule(".wl-ptitle", f"display:flex;align-items:center;gap:10px;font-size:21px;font-weight:750;margin:0 0 12px"),
        _rule(".wl-ptitle::before", f"content:'';width:4px;height:22px;border-radius:2px;background:{p['accent']}"),
        _rule(".wl-metrics", "display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:0 0 14px"),
        _rule(".wl-metric", "padding:16px 18px 10px;min-width:0"),
        _rule(".wl-metric .wl-mh", f"display:flex;align-items:center;gap:10px;font-size:16px;font-weight:600;color:{p['text']}"),
        _rule(".wl-metric .wl-mv", "font-size:30px;font-weight:750;letter-spacing:-.5px;margin-top:10px;white-space:nowrap;"
                                   "font-variant-numeric:tabular-nums"),
        _rule(".wl-metric .wl-mv small", "font-size:20px;font-weight:650;margin-left:4px"),
        _rule(".wl-metric .wl-mn", f"font-size:14px;color:{p['muted']};margin:2px 0 6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"),
        _rule(".wl-band", "display:grid;grid-template-columns:1.2fr repeat(3,1fr);align-items:center;padding:16px 22px;margin:0 0 14px;gap:12px"),
        _rule(".wl-band>div", f"display:flex;align-items:center;gap:14px;min-width:0"),
        _rule(".wl-band>div+div", f"border-left:1px solid {soft};padding-left:22px"),
        _rule(".wl-band .wl-bt", "font-size:21px;font-weight:750"),
        _rule(".wl-band .wl-bs", f"font-size:14px;color:{p['muted']}"),
        _rule(".wl-band .wl-bv", "font-size:18px;font-weight:650;white-space:nowrap"),
        _rule(".wl-band .wl-bv b", f"color:{p['accent'] if not dark else '#f6c445'}"),
        _rule(".wl-outlook", "padding:16px 22px 18px;margin:0 0 14px"),
        _rule(".wl-hours", "display:grid;grid-template-columns:repeat(12,minmax(0,1fr))"),
        _rule(".wl-hours>div", f"text-align:center;padding:6px 2px;font-size:15px;color:{p['muted']}"),
        _rule(".wl-hours>div+div", f"border-left:1px solid {p['line']}77"),
        _rule(".wl-hours b", f"display:block;font-size:20px;font-weight:700;color:{p['text']};margin-top:4px"),
        _rule(".wl-hours .wl-pop", f"display:block;font-size:13px;color:{p['accent']};margin-top:2px"),
        _rule(".wl-health", "display:flex;align-items:center;gap:12px;padding:12px 20px;margin:0 0 14px;font-size:16px"),
        _rule(".wl-health .wl-hr", f"margin-left:auto;padding-left:18px;border-left:1px solid {soft};color:{p['muted']};white-space:nowrap"),
        # Batch 2 (0.37.63): summary strips, list rows with level badges, day rows and stat rows.
        _rule(".wl-stats", "display:flex;flex-wrap:wrap;align-items:center;padding:14px 22px;margin:0 0 14px;gap:10px 0"),
        _rule(".wl-stats>div", "display:flex;align-items:center;gap:12px;padding:0 26px;min-width:0"),
        _rule(".wl-stats>div:first-child", "padding-left:0"),
        _rule(".wl-stats>div+div", f"border-left:1px solid {soft}"),
        _rule(".wl-stats b", "display:block;font-size:24px;font-weight:750;line-height:1.1"),
        _rule(".wl-stats span", f"font-size:14px;color:{p['muted']}"),
        _rule(".wl-dayhead", f"font-family:{FONT};font-size:19px;font-weight:750;margin:14px 0 8px;color:{p['text']}"),
        _rule(".wl-dayhead span", f"font-size:14px;font-weight:500;color:{p['muted']};margin-left:8px"),
        _rule(".wl-rows", "overflow:hidden;margin:0 0 6px"),
        _rule(".wl-row", f"display:grid;grid-template-columns:96px 40px minmax(0,1fr) 110px auto;align-items:center;gap:12px;"
                         f"padding:11px 18px;font-size:15px"),
        _rule(".wl-row+.wl-row", f"border-top:1px solid {p['line']}88"),
        _rule(".wl-row .wl-rt", f"color:{p['muted']};white-space:nowrap;border-right:1px solid {soft};padding-right:12px"),
        _rule(".wl-row .wl-rtitle", "font-weight:700"),
        _rule(".wl-row .wl-rsub", f"font-size:13.5px;color:{p['muted']};white-space:nowrap;overflow:hidden;text-overflow:ellipsis"),
        _rule(".wl-row .wl-rwhere", f"color:{p['muted']};white-space:nowrap;font-size:14px;padding-left:12px;border-left:1px solid {soft}"),
        _rule(".wl-badge", "display:inline-block;text-align:center;font-size:13px;font-weight:700;padding:3px 12px;border-radius:99px;"
                           "border:1px solid currentColor"),
        _rule(".wl-badge-critical", "color:#ff7a6b;background:rgba(239,91,76,.16)"),
        _rule(".wl-badge-warning", "color:#f6c445;background:rgba(246,196,69,.13)"),
        _rule(".wl-badge-info", f"color:{p['accent']};background:{p['accent']}1f"),
        _rule(".wl-daysrows>div", f"display:grid;grid-template-columns:96px 44px minmax(0,1fr) 70px 70px 64px;align-items:center;"
                                  f"gap:10px;padding:9px 4px;font-size:16px"),
        _rule(".wl-daysrows>div+div", f"border-top:1px solid {p['line']}88"),
        _rule(".wl-daysrows small", f"display:block;font-size:13px;color:{p['muted']}"),
        _rule(".wl-daysrows .wl-up", "color:#f6c445;font-weight:700"),
        _rule(".wl-daysrows .wl-dn", "color:#7cc4ff;font-weight:700"),
        _rule(".wl-daysrows .wl-pp", f"color:{p['muted']};border-left:1px solid {soft};padding-left:12px"),
        _rule(".wl-statrows", f"border:1px solid {soft};border-radius:{RADIUS['md']}px;background:{p['sub']};margin:12px 0"),
        _rule(".wl-statrows>div", "display:flex;align-items:center;gap:14px;padding:14px 18px"),
        _rule(".wl-statrows>div+div", f"border-top:1px solid {soft}"),
        _rule(".wl-statrows b", "display:block;font-size:17px;font-weight:700"),
        _rule(".wl-statrows span", f"font-size:14px;color:{p['muted']}"),
        _rule(".wl-statrows .wl-big", f"margin-left:auto;font-size:30px;font-weight:750;color:{p['text']};white-space:nowrap"),
        _rule(".wl-note-line", f"display:flex;gap:12px;align-items:flex-start;font-size:15px;color:{p['muted']};"
                               f"border-top:1px solid {soft};padding-top:12px;margin-top:4px"),
        _rule(".wl-answer", "display:flex;align-items:center;gap:22px;padding:22px 26px;margin:0 0 14px;position:relative;overflow:hidden"),
        _rule(".wl-answer .wl-at", "font-size:28px;font-weight:800;letter-spacing:-.4px;line-height:1.2"),
        _rule(".wl-answer .wl-as", f"font-size:15px;color:{p['muted']};margin-top:4px"),
        _rule(".wl-answer>svg", f"padding-right:22px;border-right:1px solid {soft}"),
        _rule(".wl-cmphead", "display:flex;align-items:center;gap:18px;padding:18px 22px;position:relative;overflow:hidden;margin:0 0 12px"),
        _rule(".wl-cmphead .wl-cn", "display:flex;align-items:center;gap:10px;font-size:18px;font-weight:700"),
        _rule(".wl-cmphead .wl-ct", "font-size:64px;font-weight:800;letter-spacing:-2px;line-height:1"),
        _rule(".wl-cmphead .wl-ct sup", "font-size:28px;vertical-align:top;position:relative;top:6px;margin-left:2px"),
        _rule(".wl-cmprows>div", f"display:grid;grid-template-columns:minmax(150px,1.2fr) 1fr 1fr 120px 1fr 1fr;align-items:center;gap:12px;"
                                 f"padding:8px 18px;font-size:15px"),
        _rule(".wl-cmprows>div+div", f"border-top:1px solid {p['line']}88"),
        _rule(".wl-cmprows .wl-cv", "font-size:22px;font-weight:700;white-space:nowrap"),
        _rule(".wl-cmprows small", f"display:block;font-size:12.5px;color:{p['muted']}"),
        _rule(".wl-delta", "display:inline-block;text-align:center;min-width:92px;font-size:14px;font-weight:700;padding:4px 10px;"
                           f"border-radius:{RADIUS['sm']}px;border:1px solid {soft};background:{p['sub']}"),
        # Batch 3 (0.37.64): choice lists shown as a joined bar, key-value panels, the daily high/low strip, big-number cards.
        _rule(".st-key-history_view,.st-key-daily_range", "width:100% !important"),
        _rule(".st-key-history_view [role='radiogroup'],.st-key-daily_range [role='radiogroup']",
              f"display:flex !important;flex-wrap:wrap;gap:4px !important;padding:4px;border:1px solid {soft};"
              f"border-radius:{RADIUS['md']}px;background:{p['card']};width:100%"),
        _rule(".st-key-history_view [role='radiogroup']>div,.st-key-daily_range [role='radiogroup']>div", "flex:1 1 auto;margin:0 !important"),
        _rule(".st-key-history_view [data-testid='stRadioOption'],.st-key-daily_range [data-testid='stRadioOption']",
              f"justify-content:center;width:100%;padding:8px 14px !important;border-radius:{RADIUS['sm']}px;margin:0 !important;cursor:pointer"),
        _rule(".st-key-history_view [data-testid='stRadioOption']>div>div:first-child,"
              ".st-key-daily_range [data-testid='stRadioOption']>div>div:first-child", "display:none !important"),
        _rule(".st-key-history_view [data-testid='stRadioOption'][data-selected='true'],"
              ".st-key-daily_range [data-testid='stRadioOption'][data-selected='true']",
              f"background:{tab_bg};box-shadow:inset 0 0 0 1px {p['accent']}66"),
        _rule(".st-key-history_view [data-testid='stRadioOption'][data-selected='true'] p,"
              ".st-key-daily_range [data-testid='stRadioOption'][data-selected='true'] p", f"color:{tab_text} !important;font-weight:650"),
        _rule(".wl-kvp", "padding:16px 20px;min-width:0;height:100%"),
        _rule(".wl-kvp .wl-ptitle", "font-size:17px;margin-bottom:8px"),
        _rule(".wl-kvp .wl-ptitle::before", "display:none"),
        _rule(".wl-kv>div", f"display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:6px 0;font-size:14.5px"),
        _rule(".wl-kv>div+div", f"border-top:1px solid {p['line']}66"),
        _rule(".wl-kv b", "font-size:16px;font-weight:700;white-space:nowrap;text-align:right"),
        _rule(".wl-kv small", f"display:block;font-size:12px;color:{p['muted']};font-weight:500"),
        _rule(".wl-kv .wl-good", "color:#3ddc84"), _rule(".wl-kv .wl-warm", "color:#ff8a6b"), _rule(".wl-kv .wl-cool", "color:#7cc4ff"),
        _rule(".wl-kvgrid", "display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:14px;margin:0 0 14px"),
        _rule(".wl-hl", "display:grid;grid-template-columns:repeat(15,minmax(0,1fr))"),
        _rule(".wl-hl>div", f"text-align:center;padding:4px 2px;font-size:13px;color:{p['muted']}"),
        _rule(".wl-hl>div+div", f"border-left:1px solid {p['line']}77"),
        _rule(".wl-hl b", f"display:block;font-size:14px;font-weight:700;color:{p['text']};margin-top:2px;white-space:nowrap"),
        _rule(".wl-bignum", "display:flex;align-items:center;gap:24px;padding:20px 26px;margin:0 0 14px;position:relative;overflow:hidden"),
        _rule(".wl-bignum .wl-bn", "font-size:64px;font-weight:800;letter-spacing:-2px;line-height:1"),
        _rule(".wl-bignum .wl-bn small", "font-size:30px;font-weight:700;letter-spacing:0;margin-left:6px"),
        _rule(".wl-bignum .wl-bw", "font-size:34px;font-weight:800;letter-spacing:-.5px"),
        _rule(".wl-bignum .wl-bd", f"font-size:16px;color:{p['muted']};max-width:520px;margin-top:4px"),
        _rule(".wl-bignum .wl-div", f"align-self:stretch;width:1px;background:{soft}"),
        _rule(".wl-aqibox", "display:flex;flex-direction:column;align-items:center;justify-content:center;width:118px;height:118px;"
                            f"border-radius:{RADIUS['lg']}px;color:#1b1406;font-weight:800;flex:0 0 auto"),
        _rule(".wl-aqibox span,.wl-aqibox b", "color:#1b1406 !important"),
        _rule(".wl-aqibox span", "font-size:20px"), _rule(".wl-aqibox b", "font-size:52px;line-height:1"),
        # Coloured text set by class wins over the page's text colour (0.37.65).
        _rule(".stApp span.wl-pop", f"color:{p['accent']} !important"),
        _rule(".stApp span.wl-badge-critical", "color:#ff7a6b !important"),
        _rule(".stApp span.wl-badge-warning", "color:#f6c445 !important"),
        _rule(".stApp span.wl-badge-info", f"color:{p['accent']} !important"),
        _rule(".stApp span.wl-note,.stApp span.wl-rt,.stApp span.wl-rwhere,.stApp span.wl-pp,.stApp .wl-stats span,"
              ".stApp .wl-statrows span:not(.wl-big),.stApp .wl-hours>div,.stApp .wl-hl>div", f"color:{p['muted']} !important"),
        _rule(".stApp span.wl-up", "color:#f6c445 !important"), _rule(".stApp span.wl-dn", "color:#7cc4ff !important"),
        _rule("[data-testid='stLinkButton'] a", f"background:{p['card']} !important;color:{p['text']} !important;"
                                                f"border:1px solid {soft} !important;border-radius:{RADIUS['sm']}px !important"),
        _rule("[data-testid='stLinkButton'] a *", f"color:{p['text']} !important"),
        "@media (max-width:900px){.wl-hl{grid-template-columns:repeat(8,minmax(0,1fr))}.wl-hl>div:nth-child(n+9){display:none}"
        ".wl-bignum{flex-wrap:wrap}.wl-bignum .wl-div{display:none}}",
        "@media (max-width:900px){.wl-row{grid-template-columns:70px 32px minmax(0,1fr) auto}.wl-row .wl-rwhere{display:none}"
        ".wl-cmprows>div{grid-template-columns:1fr 1fr 1fr}.wl-cmprows .wl-sp{display:none}"
        ".wl-stats>div{padding:0 12px}}",
        "@media (max-width:900px){.wl-band{grid-template-columns:1fr 1fr}.wl-band>div+div{border-left:none;padding-left:0}"
        ".wl-hours{grid-template-columns:repeat(6,minmax(0,1fr))}.wl-hours>div:nth-child(n+7){display:none}"
        "div[data-testid='stLayoutWrapper']:has(>.st-key-wl-topright){position:static !important}}",
    ]


# The bar under the title (station, place, live) shows on the pages about the weather; settings-like pages skip it.
BAR_PAGES = {"Home", "Forecast", "Alert history", "History", "Ask", "Air and heat", "Sun and sky", "Lightning",
             "Fire", "Tropics"}

import contextvars as _cv
_CONTEXT: _cv.ContextVar = _cv.ContextVar("wl_head_context", default=None)
_SLOT: _cv.ContextVar = _cv.ContextVar("wl_head_slot", default=None)


def set_context(page: str, station: str = "", place: str = "", live: tuple | None = None) -> None:
    """What the header bar says on this run: the page, the station's name, the place and (state, age text)."""
    _CONTEXT.set({"page": page, "station": station, "place": place, "live": live})


def head_slot(slot) -> None:
    """A tabbed page puts its title above the tabs: the tab's page_head() then fills this slot (an st.empty)."""
    _SLOT.set(slot)


def take_slot():
    """The slot if no page_head() used it, so the tabbed page can still show its name."""
    slot = _SLOT.get()
    _SLOT.set(None)
    return slot


LIVE_WORDS = {"ok": ("LIVE", "#3ddc84"), "slow": ("LATE", "#f6c445"), "silent": ("OFFLINE", "#ef5b4c"),
              "none": ("WAITING", "#9aa3b0")}


def context_bar_html(ctx: dict) -> str:
    """Station name, place and live state, as one line of chips."""
    from weatherlab import line_icons
    parts = []
    if ctx.get("station"):
        parts.append(f'<span class="wl-chip">{line_icons.icon("station", 20)}{_html.escape(ctx["station"])}</span>')
    if ctx.get("place"):
        parts.append(f'<span>{line_icons.icon("pin", 19)} {_html.escape(ctx["place"])}</span>')
    live = ctx.get("live")
    if live:
        word, colour = LIVE_WORDS.get(live[0], LIVE_WORDS["none"])
        tail = f" · updated {_html.escape(live[1])}" if live[0] != "none" else ""
        parts.append(f'<span class="wl-live"><i class="wl-dot" style="background:{colour};box-shadow:0 0 0 3px {colour}33">'
                     f'</i><b style="color:{colour}">{word}</b>{tail}</span>')
    if not parts:
        return ""
    return '<div class="wl-ctx">' + '<i class="wl-sep"></i>'.join(parts) + "</div>"


def skeleton_html(heights: tuple = (72, 96)) -> str:
    """Grey shimmering shapes to stand in for a part of the page that is still loading."""
    return "".join(f'<div class="wl-skel" style="height:{h}px" aria-hidden="true"></div>' for h in heights)


def page_head(title: str, subtitle: str = "") -> str:
    """A page's title, with one line under it saying what the page shows, then the header bar on the weather pages
    (0.37.62). On a tabbed page the head goes above the tabs, under the page's own name, and this returns ""."""
    ctx = _CONTEXT.get() or {}
    slot = _SLOT.get()
    if slot is not None:
        _SLOT.set(None)
        title = ctx.get("page") or title
    sub = f'<div class="wl-sub">{_html.escape(subtitle)}</div>' if subtitle else ""
    bar = context_bar_html(ctx) if ctx.get("page") in BAR_PAGES else ""
    out = f'<div class="wl-head"><div class="wl-title">{title}</div>{sub}{bar}</div>'
    if slot is not None:
        slot.markdown(out, unsafe_allow_html=True)
        return ""
    return out


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
