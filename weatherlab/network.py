"""Access from other devices on the home network. Off by default.

Weather Lab has no login, so anyone who can reach the address can see the readings. The setting
is only for networks the user trusts. The launcher checks the port before listening on the network.
"""

import ipaddress
import os
import re
import shutil
import socket
import subprocess

PREFERRED_PORT = 8501


def app_port() -> int:
    """The port Weather Lab is running on. The launcher sets WEATHERLAB_PORT; run from source it's 8501."""
    try:
        return int(os.environ.get("WEATHERLAB_PORT", PREFERRED_PORT))
    except ValueError:
        return PREFERRED_PORT


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def lan_address() -> str:
    """This PC's address on the home network. No packets are sent."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return "your PC's IP address"


TAILSCALE_RANGE = ipaddress.IPv4Network("100.64.0.0/10")  # Tailscale gives each device an address in this range


def tailscale_addresses(text: str) -> list[str]:
    """IPv4 addresses inside the Tailscale range, found in the text."""
    found = []
    for match in re.findall(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", text):
        try:
            if ipaddress.IPv4Address(match) in TAILSCALE_RANGE and match not in found:
                found.append(match)
        except ValueError:
            continue
    return found


def tailscale_address() -> str | None:
    """This PC's Tailscale address, such as 100.101.102.103. None when the Tailscale program isn't found or isn't running."""
    for exe in [shutil.which("tailscale"), r"C:\Program Files\Tailscale\tailscale.exe"]:
        if not exe or not os.path.exists(exe):
            continue
        try:
            out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=5,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        found = tailscale_addresses(out)
        if found:
            return found[0]
    return None
