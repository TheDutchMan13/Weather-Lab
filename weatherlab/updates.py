"""Updates: finds the newest version at an address the user gives, checks the downloaded installer against
its checksum, and starts the installer. Weather Lab never runs an installer it hasn't checked.

The address can hold the older plain-text file (first line = version number) or latest.json, which
build_installer.py writes beside each installer:
    {"version": "0.11.0", "file": "WeatherLabSetup-0.11.0.exe", "sha256": "<64 hex characters>"}
"""

import hashlib
import json
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

# /SILENT shows only a progress window. /CLOSEAPPLICATIONS closes Weather Lab first, and
# /RESTARTAPPLICATIONS starts it again once the update is in.
INSTALL_ARGS = ["/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"]


def parse_version(text: str):
    parts = text.strip().lstrip("vV").split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    return a is not None and b is not None and a > b


def info_from_text(text: str, address: str, current: str) -> dict | None:
    """The newer version described by the text, or None. The text is latest.json or a plain version line."""
    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError("The update address doesn't hold a valid latest.json file.") from exc
        version = str(data.get("version", "")).strip()
        if not newer(version, current):
            return None
        name = Path(str(data.get("file", ""))).name
        digest = str(data.get("sha256", "")).strip().lower()
        if not name.lower().endswith(".exe") or len(digest) != 64:
            return {"version": version, "file": "", "sha256": "", "installer_url": ""}
        return {"version": version, "file": name, "sha256": digest,
                "installer_url": urllib.parse.urljoin(address, name)}
    latest_line = stripped.splitlines()[0].strip() if stripped else ""
    if not newer(latest_line, current):
        return None
    return {"version": latest_line, "file": "", "sha256": "", "installer_url": ""}


def latest(url: str, current: str, timeout: float = 8.0) -> dict | None:
    """The newer version at this address, with installer details when it names one. None when up to date.
    Raises OSError when the address can't be read and ValueError when its contents don't make sense."""
    with urllib.request.urlopen(url, timeout=timeout) as response:
        text = response.read(20000).decode("utf-8", "replace")
    return info_from_text(text, url, current)


# The official releases on GitHub. GitHub sends /releases/latest/download/<file> to that file in the newest release,
# so latest.json and the installer it names are always the newest ones (0.37.48).
OFFICIAL_URL = "https://github.com/TheDutchMan13/Weather-Lab/releases/latest/download/latest.json"


def banner_text(available: str, current: str) -> str | None:
    """The line for Home when the daily check found a newer version, or None when there is nothing newer."""
    if not available or not newer(available, current):
        return None
    return f"Weather Lab {available} is available. You have {current}."


def check(url: str, current: str, timeout: float = 8.0) -> str | None:
    """The newer version number when one is published, otherwise None. Raises OSError when the address can't be read."""
    info = latest(url, current, timeout)
    return info["version"] if info else None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(info: dict, folder: Path, timeout: float = 120.0) -> Path:
    """Download the installer into folder. It is kept only when its checksum matches; otherwise it is deleted."""
    if not info.get("installer_url") or not info.get("file"):
        raise ValueError("This update doesn't name an installer.")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / info["file"]
    partial = folder / (info["file"] + ".part")
    with urllib.request.urlopen(info["installer_url"], timeout=timeout) as response, open(partial, "wb") as out:
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            out.write(chunk)
    if file_sha256(partial) != info["sha256"]:
        partial.unlink(missing_ok=True)
        raise ValueError("The download doesn't match the published checksum, so it wasn't installed.")
    partial.replace(target)
    return target


def start_installer(path: Path) -> None:
    """Run the installer with the chosen options. Weather Lab closes while it installs and starts again afterwards."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([str(path), *INSTALL_ARGS], creationflags=flags, close_fds=True)
