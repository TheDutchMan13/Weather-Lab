"""Password for other devices on the home network. Used only when network access is on.

The password is never stored as typed. Only a salted PBKDF2 hash goes into Windows Credential
Manager, through secrets.py. Wrong passwords are slowed down after a few tries.
"""

import hashlib
import hmac
import os
import time

from weatherlab import secrets

KEY = "app-password"
ITERATIONS = 200_000
MAX_FAILURES = 5
LOCK_SECONDS = 60
MIN_LENGTH = 8

_state = {"failures": 0, "locked_until": 0.0}


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


def locked_for() -> int:
    """Seconds left before another password try is allowed (0 when allowed)."""
    return max(0, int(_state["locked_until"] - time.time()))


def record_failure() -> None:
    _state["failures"] += 1
    if _state["failures"] >= MAX_FAILURES:
        _state["failures"] = 0
        _state["locked_until"] = time.time() + LOCK_SECONDS


def reset_failures() -> None:
    _state["failures"] = 0
    _state["locked_until"] = 0.0


def reach_lines(allow_network: bool, has_password: bool, away_address: str | None) -> list[str]:
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
    lines.append("This PC's own window never asks for a password.")
    return lines
