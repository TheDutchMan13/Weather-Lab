"""The welcome screen (0.37.61, "Daybreak"): the first thing a new user sees, before the setup wizard.

A full-window sky that follows the PC's clock (morning, afternoon, evening, night), a greeting, and one button that
starts the wizard and looks for the station straight away. Shown only while no station address is saved and the
wizard has not been opened, so Settings, Station, Run setup again goes straight to the wizard.
Drawn as one SVG used as a CSS background, so nothing is downloaded and there is no image file to ship.
"""

from datetime import datetime
from urllib.parse import quote

import streamlit as st

from weatherlab.settings import load_settings

PERIODS = ("morning", "afternoon", "evening", "night")

GREETING = {"morning": "Good morning.", "afternoon": "Good afternoon.", "evening": "Good evening.", "night": "Hello there."}

# stops: (offset, colour) top to bottom. hills: back to front. text region ends near offset 0.4; contrast is tested there.
PALETTE = {
    "morning": dict(stops=[(0, "#26346F"), (.4, "#4A5CA3"), (.7, "#E9A087"), (.88, "#F6D199"), (1, "#FBE6B4")],
                    hills=["#6C5B86", "#40386A", "#25214A"], sun=("#FFE08A", 880, 600, 56), stars=0, moon=False, clouds=0),
    "afternoon": dict(stops=[(0, "#103A86"), (.4, "#1F5AB4"), (.8, "#7DB6EC"), (1, "#CBE6F8")],
                      hills=["#3F7D6E", "#2C5F57", "#1A3F3B"], sun=("#FFF1A8", 930, 500, 52), stars=0, moon=False, clouds=1),
    "evening": dict(stops=[(0, "#0F1B45"), (.4, "#3B3F86"), (.68, "#C9627E"), (.86, "#F2A878"), (1, "#F8D9A0")],
                    hills=["#5A3A6B", "#2A1F4A", "#150F2E"], sun=("#FFC857", 800, 640, 64), stars=36, moon=False, clouds=0),
    "night": dict(stops=[(0, "#050816"), (.4, "#101A44"), (.8, "#27306B"), (1, "#3E4A8C")],
                  hills=["#1C2250", "#121737", "#0A0D24"], sun=("#F3F0E0", 920, 490, 46), stars=90, moon=True, clouds=0),
}
INK = "#FFFFFF"      # greeting
SUB = "#EDEAFB"      # line under it
EYEBROW = "#FFE7C2"  # "Weather Lab"
NOTE = "#F4EEE8"     # small print, over the darkest hill


def period(hour: int) -> str:
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 17:
        return "afternoon"
    if 17 <= hour < 21:
        return "evening"
    return "night"


def scene_svg(name: str) -> str:
    """The sky for one time of day, 1600 by 900, hills along the bottom edge."""
    p = PALETTE[name]
    w, h = 1600, 900
    stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in p["stops"])
    stars = "".join(f'<circle cx="{(i * 211) % w}" cy="{(i * 97) % int(h * .42) + 10}" r="{1 + (i % 3) * .6:.1f}" '
                    f'fill="#fff" fill-opacity="{.35 + (i % 4) * .13:.2f}"/>' for i in range(p["stars"]))
    colour, sx, sy, r = p["sun"]
    glow = (f'<circle cx="{sx}" cy="{sy}" r="{r * 2.8:.0f}" fill="{colour}" fill-opacity=".10"/>'
            f'<circle cx="{sx}" cy="{sy}" r="{r * 1.8:.0f}" fill="{colour}" fill-opacity=".18"/>'
            f'<circle cx="{sx}" cy="{sy}" r="{r}" fill="{colour}"/>')
    clouds = ("".join(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="#fff" fill-opacity=".30"/>'
                      for x, y, rx, ry in ((300, 560, 170, 26), (390, 540, 110, 24), (1250, 520, 200, 28), (1330, 500, 120, 24)))
              if p["clouds"] else "")
    a, b, c = p["hills"]
    hills = (f'<path d="M0 {h * .80}C{w * .2} {h * .70} {w * .38} {h * .84} {w * .58} {h * .76}S{w * .88} {h * .68} {w} {h * .78}V{h}H0z" fill="{a}" fill-opacity=".9"/>'
             f'<path d="M0 {h * .88}C{w * .25} {h * .80} {w * .45} {h * .92} {w * .7} {h * .85}S{w * .92} {h * .84} {w} {h * .88}V{h}H0z" fill="{b}"/>'
             f'<path d="M0 {h * .95}C{w * .3} {h * .90} {w * .6} {h * .98} {w} {h * .93}V{h}H0z" fill="{c}"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMax slice">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient></defs>'
            f'<rect width="{w}" height="{h}" fill="url(#g)"/>{stars}{glow}{clouds}{hills}</svg>')


def css(name: str) -> str:
    """The page's own look: hides the sidebar and header, lays the scene over the whole window."""
    p = PALETTE[name]
    bg = "url(\"data:image/svg+xml;utf8," + quote(scene_svg(name), safe="") + "\")"
    font = "'Outfit', Manrope, system-ui, -apple-system, 'Segoe UI', sans-serif"
    return f"""<style>
@font-face{{font-family:'Outfit';src:url('app/static/outfit.ttf') format('truetype');font-weight:100 900;font-display:swap}}
[data-testid='stSidebar'],[data-testid='stSidebarCollapsedControl'],[data-testid='stExpandSidebarButton'],
[data-testid='stHeader'],[data-testid='stToolbar']{{display:none !important}}
.stApp,[data-testid='stAppViewContainer'],[data-testid='stMain']{{background:{p['hills'][2]} !important}}
.block-container{{padding:0 !important;max-width:100% !important}}
.block-container>[data-testid='stVerticalBlock']{{gap:0 !important}}
.st-key-wl-welcome{{min-height:100vh;box-sizing:border-box;display:flex;flex-direction:column;align-items:center;gap:0;
  padding:9vh 24px 5vh;margin-top:-1px !important;border-radius:0 !important;background:{bg} center bottom/cover no-repeat;font-family:{font};text-align:center}}
div[data-testid='stLayoutWrapper']>div.stVerticalBlock.st-key-wl-welcome,div.stVerticalBlock.st-key-wl-welcome,[data-testid='stMain'],[data-testid='stAppViewContainer'],.stApp{{border-radius:0 !important;border:0 !important}}
.block-container>[data-testid='stVerticalBlock']>[data-testid='stElementContainer']:is(:has(style),:has([data-testid='stCaptionContainer'])){{display:none !important}}
.st-key-wl-welcome>div,.st-key-wl-welcome [data-testid='stMarkdown'],.st-key-wl-welcome [data-testid='stMarkdown'] *{{text-align:center}}
.st-key-wl-welcome>div{{width:100%}}
.st-key-wl-welcome .wlw-eyebrow{{font-size:12px !important;letter-spacing:.28em !important;text-transform:uppercase;font-weight:500 !important;color:{EYEBROW} !important;font-family:{font} !important}}
div.st-key-wl-welcome [data-testid='stMarkdownContainer'] h1 *,div.st-key-wl-welcome h1 *{{color:{INK} !important;font-family:{font} !important}}
div.st-key-wl-welcome [data-testid='stMarkdownContainer'] h1,.st-key-wl-welcome h1{{font-family:{font} !important;font-size:clamp(46px,9vw,96px) !important;font-weight:300 !important;letter-spacing:-.035em !important;
  line-height:1 !important;color:{INK} !important;margin:18px 0 14px !important;padding:0 !important}}
.st-key-wl-welcome .wlw-sub{{font-family:{font} !important;font-size:clamp(16px,2.2vw,20px) !important;line-height:1.5 !important;font-weight:300 !important;
  color:{SUB} !important;max-width:520px;margin:0 auto !important}}
.st-key-wl-welcome-go{{margin-top:auto !important;width:100%;max-width:340px}}
.st-key-wl-welcome-go button{{width:100% !important;height:56px !important;border-radius:28px !important;border:0 !important;
  background:#fff !important;color:#17214A !important;box-shadow:none !important;font-family:{font} !important;font-size:17px !important;font-weight:600 !important}}
.st-key-wl-welcome-go button *{{color:#17214A !important;font-family:{font} !important;font-size:17px !important;font-weight:600 !important}}
.st-key-wl-welcome-go button:hover{{background:#F4F1FF !important}}
.st-key-wl-welcome-go button:focus-visible,.st-key-wl-welcome-address button:focus-visible{{outline:3px solid #FFE7C2 !important;outline-offset:3px}}
.st-key-wl-welcome-address{{width:auto !important}}
.st-key-wl-welcome-address button{{min-height:44px !important;background:transparent !important;border:0 !important;box-shadow:none !important;
  color:{NOTE} !important;padding:0 12px !important}}
.st-key-wl-welcome-address button *{{color:{NOTE} !important;font-family:{font} !important;font-size:15px !important;
  text-decoration:underline;text-underline-offset:4px}}
.st-key-wl-welcome-address button:hover,.st-key-wl-welcome-address button:hover *{{background:transparent !important;color:#fff !important}}
.st-key-wl-welcome .wlw-note{{font-family:{font} !important;font-size:13.5px !important;color:{NOTE} !important;margin-top:6px !important}}
</style>"""


def pending() -> bool:
    """True while a brand-new install should see the welcome: no station saved and the wizard not opened yet."""
    return (not st.session_state.get("wiz_active") and not st.session_state.get("wl_welcomed")
            and not load_settings().station_ip.strip())


def _begin(find: bool) -> None:
    st.session_state["wl_welcomed"] = True
    st.session_state["wiz_active"] = True
    st.session_state["wiz_step"] = 0
    if find:
        st.session_state["wiz_autofind"] = True


def show(hour: int | None = None) -> None:
    name = period(datetime.now().hour if hour is None else hour)
    st.markdown(css(name), unsafe_allow_html=True)
    with st.container(key="wl-welcome"):
        st.markdown(f'<div class="wlw-eyebrow">Weather Lab</div><h1>{GREETING[name]}</h1>'
                    '<p class="wlw-sub">Let\'s connect your weather station: the one on your roof, in the garden or by the window.</p>',
                    unsafe_allow_html=True)
        st.button("Find my station", key="wl-welcome-go", on_click=_begin, args=(True,))
        st.button("I know its address", key="wl-welcome-address", type="tertiary", on_click=_begin, args=(False,))
        st.markdown('<div class="wlw-note">About two minutes. Your readings stay on this PC.</div>', unsafe_allow_html=True)
