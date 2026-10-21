"""Side-by-side look check for Weather Lab and the dashboard.

Run this on your PC while both apps are running, each on its own port. Start them in their own folders:
  streamlit run app.py --server.port 8501                  (Weather Lab)
  streamlit run dashboard_v2.0.py --server.port 8502      (dashboard)

One-time setup:
  pip install playwright
  playwright install chromium

Then:
  python tools/compare_looks.py --pages Live "Rain calendar"
  (use --dashboard-pages if the dashboard's page names differ, in the same order)

For each page, at a desktop width and a phone width, it saves a screenshot of both apps and measures the styles of key
elements. It writes report/index.html with the screenshots and a table of style differences. The apps hold different
data, so the report compares looks, not numbers. If the dashboard asks you to sign in, its screenshot shows the sign-in
page and its styles are not measured.
"""

import argparse
import html
import json
import pathlib
import re
import sys
import time

from playwright.sync_api import sync_playwright

WIDTHS = {"desktop": (1280, 900), "phone": (390, 844)}
PHONE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")
PROBES = [  # (name, CSS selector, styles to read)
    ("page", ".stApp", ["background-color", "font-family"]),
    ("sidebar", "[data-testid='stSidebar']", ["background-color"]),
    ("body text", ".stApp p", ["color", "font-family", "font-size"]),
    ("button", ".stButton > button", ["background-color", "border-top-color", "border-radius"]),
    ("tab", "[data-testid='stTabs'] button[role='tab']", ["color", "border-radius"]),
    ("heading", ".wx-sec h3", ["font-size", "font-weight"]),  # section headings: the same element in both apps
    ("tile", ".wl-tile", ["background-color", "border-radius"]),
]
READ_STYLES = """([sel, props]) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const cs = getComputedStyle(el);
  return Object.fromEntries(props.map(p => [p, cs.getPropertyValue(p)]));
}"""


def open_page(page, url: str, name: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=90000)
    page.wait_for_selector("[data-testid='stApp']", timeout=60000)
    time.sleep(2)
    if name and name != "Live":
        if not page.locator("[data-testid='stSidebar']").first.is_visible():  # phone: the sidebar starts closed
            page.locator("[data-testid='stExpandSidebarButton'], [data-testid='stSidebarCollapsedControl']").first.click()
            time.sleep(1)
        for more in page.locator("[data-testid='stSidebar'] button", has_text=re.compile(r"View \d+ more")).all():
            more.click()  # long sections start folded; a page such as Setup can sit behind one of these
            time.sleep(1)
        page.locator("[data-testid='stSidebarNavLink']", has_text=name).first.click()
        time.sleep(4)


# The dashboard draws its cards inline, so it needs its own tile selector.
# Both apps draw their hero tiles with the same inline style (weatherlab/hero.py, dashboard live.py).
TILE = "div[style*='rgba(0,0,0,.22)']"
APP_SELECTORS = {"weather_lab": {"tile": TILE}, "dashboard": {"tile": TILE}}

def measure(page, app: str) -> dict:
    over = APP_SELECTORS.get(app, {})
    out = {}
    for name, sel, props in PROBES:
        found = None
        for frame in page.frames:  # some cards are drawn inside components, which live in their own frames
            try:
                found = frame.evaluate(READ_STYLES, [over.get(name, sel), props])
            except Exception:
                found = None
            if found:
                break
        out[name] = found
    return out


def render(results: list) -> str:
    sections = []
    for r in results:
        pics = []
        for app, label in (("weather_lab", "Weather Lab"), ("dashboard", "Dashboard")):
            d = r.get(app, {})
            if "error" in d:
                pics.append(f"<td><b>{label}</b><p>Could not read this page: {html.escape(d['error'])}</p></td>")
            else:
                pics.append(f"<td><b>{label}</b><img src=\"{html.escape(d['shot'])}\" "
                            "style=\"width:100%;border:1px solid #ccc\"></td>")
        wl = r.get("weather_lab", {}).get("styles") or {}
        db = r.get("dashboard", {}).get("styles") or {}
        diff_rows = []
        for probe, _sel, props in PROBES:
            a, b = wl.get(probe) or {}, db.get(probe) or {}
            for prop in props:
                va, vb = a.get(prop, "missing"), b.get(prop, "missing")
                tag = "same" if va == vb else "<b>different</b>"
                diff_rows.append(f"<tr><td>{probe}</td><td>{prop}</td><td>{html.escape(str(va))}</td>"
                                 f"<td>{html.escape(str(vb))}</td><td>{tag}</td></tr>")
        sections.append(
            f"<h2>{html.escape(r['page'])} &middot; {r['width']}</h2>"
            f"<table style='width:100%;border-collapse:collapse'><tr>{''.join(pics)}</tr></table>"
            "<table border='1' cellpadding='4' style='border-collapse:collapse;margin:12px 0 28px;font-size:13px'>"
            "<tr><th>Element</th><th>Style</th><th>Weather Lab</th><th>Dashboard</th><th>Match</th></tr>"
            + "".join(diff_rows) + "</table>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Look check</title>"
            "<style>body{font-family:system-ui,sans-serif;margin:24px;color:#1c2330}"
            "td{vertical-align:top;padding:6px}</style></head><body>"
            "<h1>Weather Lab and dashboard look check</h1>" + "".join(sections) + "</body></html>")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--weather-lab", default="http://localhost:8501")
    ap.add_argument("--dashboard", default="http://localhost:8502")
    ap.add_argument("--pages", nargs="+", default=["Live"], help="page names as they appear in Weather Lab")
    ap.add_argument("--dashboard-pages", nargs="+", help="page names in the dashboard, in the same order")
    ap.add_argument("--out", default="report")
    ap.add_argument("--headed", action="store_true", help="show the browser while it works")
    args = ap.parse_args()
    dash_pages = args.dashboard_pages or args.pages
    if len(dash_pages) != len(args.pages):
        sys.exit("--dashboard-pages needs the same number of names as --pages")
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    results = []
    print("Look check running. Each step is listed below as it finishes.", flush=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        for wl_name, db_name in zip(args.pages, dash_pages):
            for width_name, (w, h) in WIDTHS.items():
                row = {"page": wl_name, "width": width_name}
                for app, url, name in (("weather_lab", args.weather_lab, wl_name),
                                       ("dashboard", args.dashboard, db_name)):
                    opts = {"viewport": {"width": w, "height": h}}
                    if width_name == "phone":  # the apps check the User-Agent to decide they are on a phone
                        opts.update(user_agent=PHONE_UA, is_mobile=True, has_touch=True)
                    context = browser.new_context(**opts)
                    page = context.new_page()
                    print(f"  {wl_name}, {width_name}: loading {app}...", flush=True)
                    try:
                        open_page(page, url, name)
                        shot = out / f"{app}-{wl_name.replace(' ', '_')}-{width_name}.png"
                        page.screenshot(path=str(shot), full_page=True)
                        row[app] = {"shot": shot.name, "styles": measure(page, app)}
                        print("    done", flush=True)
                    except Exception as exc:  # keep going so one app can't stop the other
                        print(f"    failed: {str(exc)[:200]}", flush=True)
                        row[app] = {"error": str(exc)[:300]}
                    finally:
                        context.close()
                results.append(row)
        browser.close()
    (out / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (out / "index.html").write_text(render(results), encoding="utf-8")
    print("Report:", (out / "index.html").resolve())


if __name__ == "__main__":
    main()
