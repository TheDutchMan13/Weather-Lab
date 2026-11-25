"""Writes a GitHub release's description from What's New (0.37.65).

    python tools/release_notes.py v0.37.66 [previous-tag]

Prints Markdown: every What's New entry newer than the previous release tag, up to this tag, then how to install and
the changelog link. With no previous tag given, it uses the newest v* git tag below this one."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from weatherlab.whats_new import ENTRIES  # noqa: E402

REPO = "https://github.com/TheDutchMan13/Weather-Lab"


def key(version: str) -> tuple:
    return tuple(int(x) for x in version.lstrip("v").split("."))


def previous_tag(tag: str) -> str | None:
    """The newest v* git tag below this one, or None."""
    try:
        out = subprocess.run(["git", "tag", "--list", "v*"], capture_output=True, text=True, check=True).stdout.split()
    except (OSError, subprocess.CalledProcessError):
        return None
    lower = [t for t in out if all(p.isdigit() for p in t.lstrip("v").split(".")) and key(t) < key(tag)]
    return max(lower, key=key) if lower else None


def notes(tag: str, prev: str | None) -> str:
    versions = sorted((e for e in ENTRIES if key(e["version"]) <= key(tag) and (prev is None or key(e["version"]) > key(prev))),
                      key=lambda e: key(e["version"]), reverse=True)
    if prev is None:
        versions = versions[:1]
    lines = []
    if len(versions) > 1:
        lines.append(f"This release includes {', '.join(e['version'] for e in reversed(versions))}.\n")
    for e in versions:
        lines.append(f"## What's new in {e['version']}" + (f" ({e['date']})" if e.get("date") else ""))
        lines += [f"- {item}" for item in e["items"]]
        lines.append("")
    lines.append("## Install")
    lines.append("Download **WeatherLabSetup** (the .exe) below and run it. It updates an existing install and keeps your "
                 "readings and settings. Windows may warn that the installer isn't signed: choose More info, then Run anyway.")
    if prev:
        lines += ["", f"**Full Changelog**: {REPO}/compare/{prev}...{tag}"]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    tag = sys.argv[1]
    prev = sys.argv[2] if len(sys.argv) > 2 else previous_tag(tag)
    sys.stdout.write(notes(tag, prev))
