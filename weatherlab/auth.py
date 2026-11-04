"""Password for other devices on the home network. Used only when network access is on.

The password is never stored as typed. Only a salted PBKDF2 hash goes into Windows Credential
Manager, through secrets.py. Wrong passwords are slowed down after a few tries.
"""

import hashlib
import hmac
import ipaddress
import os
import threading
import time

from weatherlab import secrets

KEY = "app-password"
ITERATIONS = 200_000
MAX_FAILURES = 5
LOCK_SECONDS = 60
MIN_LENGTH = 8

# Wrong-password counts per device address (0.37.55). One device guessing can't lock out the others, and the lock
# stops many parallel sign-ins from all slipping past the check before any failure is counted.
_lock = threading.Lock()
_state: dict[str, dict] = {}


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2${ITERATIONS}${salt.hex()}${digest.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = stored.split("$")
        if scheme != "pbkdf2":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def password_set() -> bool:
    return bool(secrets.get_key(KEY))


def set_password(password: str) -> None:
    secrets.set_key(KEY, hash_password(password))


def clear_password() -> None:
    secrets.set_key(KEY, "")


def sign_in(password: str) -> bool:
    stored = secrets.get_key(KEY)
    return bool(stored) and check_password(password, stored)


def password_version() -> str:
    """A short fingerprint of the stored password (0.37.55). A signed-in device remembers it, so changing or removing
    the password signs every other device out. Empty when no password is set."""
    stored = secrets.get_key(KEY) or ""
    return hashlib.sha256(stored.encode("utf-8")).hexdigest()[:16] if stored else ""


def _entry(client: str) -> dict:
    return _state.setdefault(client or "?", {"failures": 0, "locked_until": 0.0})


def locked_for(client: str = "") -> int:
    """Seconds left before this device may try another password (0 when allowed)."""
    with _lock:
        return max(0, int(_entry(client)["locked_until"] - time.time()))


def try_sign_in(password: str, client: str = "") -> tuple[bool, int]:
    """(signed in, seconds to wait). Checks the lock and counts a failure in one step, so parallel tries from one
    device can't get more than MAX_FAILURES guesses in before the lock."""
    with _lock:
        entry = _entry(client)
        wait = max(0, int(entry["locked_until"] - time.time()))
        if wait:
            return False, wait
        entry["failures"] += 1  # counted before the slow check, so tries made meanwhile see it
        if entry["failures"] >= MAX_FAILURES:
            entry["failures"] = 0
            entry["locked_until"] = time.time() + LOCK_SECONDS
    ok = sign_in(password)
    if ok:
        reset_failures(client)
    return ok, 0


def record_failure(client: str = "") -> None:
    with _lock:
        entry = _entry(client)
        entry["failures"] += 1
        if entry["failures"] >= MAX_FAILURES:
            entry["failures"] = 0
            entry["locked_until"] = time.time() + LOCK_SECONDS


def reset_failures(client: str = "") -> None:
    with _lock:
        _state.pop(client or "?", None)


def is_local(ip: str | None) -> bool:
    """True for a connection from this PC itself. Streamlit reports no address for localhost."""
    if ip is None or ip == "":
        return True
    try:
        return ipaddress.ip_address(ip).is_loopback
    except ValueError:
        return False


TAILSCALE_NETS = (ipaddress.ip_network("100.64.0.0/10"), ipaddress.ip_network("fd7a:115c:a1e0::/48"))


def is_tailscale(ip: str | None) -> bool:
    """True for an address Tailscale hands out (100.64.0.0/10, or its IPv6 range)."""
    try:
        addr = ipaddress.ip_address(ip or "")
    except ValueError:
        return False
    return any(addr.version == net.version and addr in net for net in TAILSCALE_NETS)


def client_allowed(ip: str | None, tailscale_only: bool) -> bool:
    """With "Tailscale only" on (0.37.55), only this PC and Tailscale devices may connect. Tailscale encrypts its
    traffic; the home network doesn't, so this keeps the password and token off plain Wi-Fi."""
    return not tailscale_only or is_local(ip) or is_tailscale(ip)


LOCAL_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def local_host_header(host: str | None) -> bool:
    """True when the Host header names this PC. With network access off, anything else is a web page trying to
    reach Weather Lab through a rebound DNS name, so it's refused (0.37.55)."""
    if not host:
        return True
    name = host.strip().lower()
    if name.startswith("["):
        name = name.split("]")[0] + "]"
    else:
        name = name.rsplit(":", 1)[0] if name.count(":") == 1 else name
    return name in LOCAL_HOSTS


def reach_lines(allow_network: bool, has_password: bool, away_address: str | None, api_on: bool = False) -> list[str]:
    """Plain-words lines saying who can open Weather Lab with the current settings, for the note in Settings.
    away_address is this PC's Tailscale address, or None when Tailscale isn't running."""
    if not allow_network:
        return ["Only this PC can open Weather Lab. Phones and other devices are blocked.",
                "This PC's own window never asks for a password."]
    lines = []
    if has_password:
        lines.append("Phones and devices on your home network can open Weather Lab once they type the password.")
    else:
        lines.append("Phones and other devices are blocked until you set a password below.")
    if away_address:
        lines.append("Away from home, only phones signed in to the same Tailscale account can reach it, and they "
                     "still need the password.")
    else:
        lines.append("Away from home, nothing can reach Weather Lab until Tailscale is set up on this PC and your phone.")
    lines.append("Weather Lab doesn't open anything to the internet. Only a router port forward would do that, "
                 "and the app doesn't set one up.")
    lines.append(f"After {MAX_FAILURES} wrong passwords, sign-in waits {LOCK_SECONDS} seconds.")
    if api_on:
        lines.append("The Android app can also read the readings, alerts and today's summary, with its own token.")
    lines.append("This PC's own window never asks for a password.")
    return lines
