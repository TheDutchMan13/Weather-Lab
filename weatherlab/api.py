"""A small read-only JSON API for companion apps, such as the Android app. Off by default.

It runs only while Weather Lab is open, and only when "Let phones and devices" is on. Every request needs the token
from Settings, sent as "Authorization: Bearer <token>". The token is stored as a SHA-256 hash in Windows Credential
Manager, so the app keeps no copy of it in plain text. Too many wrong tokens lock the API for ten minutes.

Endpoints (all GET, all JSON, version 1):
  /api/v1/status    app and station status
  /api/v1/current   the latest reading, in the units chosen in Settings
  /api/v1/today     today's high, low and rain so far
  /api/v1/alerts    the 20 most recent alerts
"""

import hashlib
import hmac
import json
import secrets as pysecrets
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from zoneinfo import ZoneInfo

from weatherlab import secrets as keystore
from weatherlab import stations, storage, units
from weatherlab.config import APP_VERSION

VERSION = 1
KEY = "api-token"
PORT = 8600
MAX_FAILURES = 20
LOCK_SECONDS = 600

_lock = threading.Lock()
_server = None
_running_port = None
_error = ""
_failures = 0
_locked_until = 0.0


# ------------------------------------------------------------------ tokens

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_set() -> bool:
    return bool(keystore.get_key(KEY))


def create_token() -> str:
    """A new random token. Only its hash is kept, so the token is shown once, when it is made."""
    token = pysecrets.token_urlsafe(24)
    keystore.set_key(KEY, hash_token(token))
    return token


def clear_token() -> None:
    keystore.set_key(KEY, "")


def token_ok(authorization: str | None) -> bool:
    stored = keystore.get_key(KEY)
    if not stored or not authorization or not authorization.startswith("Bearer "):
        return False
    supplied = authorization[len("Bearer "):].strip()
    return bool(supplied) and hmac.compare_digest(hash_token(supplied), stored)


def _locked() -> int:
    return max(0, int(_locked_until - time.time()))


def _record(ok: bool) -> None:
    global _failures, _locked_until
    if ok:
        _failures = 0
        return
    _failures += 1
    if _failures >= MAX_FAILURES:
        _failures = 0
        _locked_until = time.time() + LOCK_SECONDS


# ------------------------------------------------------------------ data

def _tz(s) -> ZoneInfo:
    try:
        return ZoneInfo(s.timezone)
    except Exception:
        return ZoneInfo("UTC")


def status(db, s, now: float) -> dict:
    latest = storage.latest(db)
    return {"app_version": APP_VERSION, "api_version": VERSION,
            "station": stations.name_of(stations.current()),
            "latest_reading_age_seconds": int(now - latest[0]) if latest else None}


def _convert_all(data: dict, metric: bool) -> dict:
    out = {}
    for key, value in data.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            continue
        if units.converts(key):
            out[key] = {"value": round(units.convert(key, value, metric), 2), "unit": units.unit(key, metric)}
        else:
            out[key] = {"value": value, "unit": ""}
    return out


def current(db, s, now: float) -> dict:
    latest = storage.latest(db)
    metric = units.is_metric(s.units)
    if latest is None:
        return {"reading": None, "metric": metric}
    ts, data = latest
    return {"reading": {"ts": ts, "age_seconds": int(now - ts), "values": _convert_all(data, metric)},
            "metric": metric}


def today(db, s, now: float) -> dict:
    tz = _tz(s)
    local = datetime.fromtimestamp(now, tz)
    start = local.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    rows = [r for _, r in storage.readings_between(db, start, now + 1)]
    metric = units.is_metric(s.units)
    temps = [r["tempf"] for r in rows if r.get("tempf") is not None]
    rain = [r["dailyrainin"] for r in rows if r.get("dailyrainin") is not None]

    def shown(key, value):
        return None if value is None else {"value": round(units.convert(key, value, metric), 1),
                                           "unit": units.unit(key, metric)}
    return {"date": local.date().isoformat(), "readings": len(rows),
            "high": shown("tempf", max(temps) if temps else None),
            "low": shown("tempf", min(temps) if temps else None),
            "rain": shown("dailyrainin", rain[-1] if rain else None),
            "metric": metric}


def alerts(db) -> dict:
    return {"alerts": [{"ts": ts, "text": text} for ts, text in storage.recent_alerts(db, limit=20)]}


# ------------------------------------------------------------------ routing

def route(path: str, authorization: str | None, db, s, now: float) -> tuple[int, dict]:
    """(HTTP status, body). Checks the token and the lock first, then the path."""
    if _locked():
        return 429, {"error": f"Too many wrong tokens. Try again in {_locked()} seconds."}
    if not token_ok(authorization):
        _record(False)
        return 401, {"error": "Sign in with the token from Weather Lab's Settings."}
    _record(True)
    builders = {"/api/v1/status": lambda: status(db, s, now),
                "/api/v1/current": lambda: current(db, s, now),
                "/api/v1/today": lambda: today(db, s, now),
                "/api/v1/alerts": lambda: alerts(db)}
    build = builders.get(path.rstrip("/") or "/")
    if build is None:
        return 404, {"error": "No such address in the API."}
    return 200, build()


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - the name http.server expects
        from weatherlab.settings import load_settings
        path = self.path.split("?", 1)[0]
        try:
            s = load_settings()
            with stations.using(stations.MAIN):
                db = storage.connect()
                try:
                    code, body = route(path, self.headers.get("Authorization"), db, s, time.time())
                finally:
                    db.close()
        except Exception:  # keep the server alive; never send a traceback to a phone
            code, body = 500, {"error": "Weather Lab couldn't read its data just now."}
        data = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # no request log in the console
        return


def ensure(enabled: bool, port: int = PORT) -> None:
    """Start the API when it is on, stop it when it is off, and restart it on a new port. Safe to call on every page load."""
    global _server, _running_port, _error
    with _lock:
        if not enabled:
            _stop_locked()
            return
        if _server is not None and _running_port == port:
            return
        _stop_locked()
        try:
            srv = ThreadingHTTPServer(("0.0.0.0", port), _Handler)
        except OSError:
            _error = f"Port {port} is in use by another program. Choose another port in Settings."
            return
        _error = ""
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        _server, _running_port = srv, port


def _stop_locked() -> None:
    global _server, _running_port
    if _server is not None:
        _server.shutdown()
        _server.server_close()
    _server, _running_port = None, None


def status_text() -> str:
    if _error:
        return _error
    if _server is not None:
        return f"Running on port {_running_port}."
    return "Not running. Turn it on above, and allow phones and devices."
