"""Build the Windows installer with Inno Setup, then write latest.json beside it for the update check.

Run build_exe.py first, then:
    python build_installer.py

Needs Inno Setup 6, a free install from jrsoftware.org. Output: installer\\WeatherLabSetup-<version>.exe and
installer\\latest.json. Upload both to the place your update address points to.
"""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def app_version() -> str:
    text = (ROOT / "weatherlab" / "config.py").read_text(encoding="utf-8")
    match = re.search(r'APP_VERSION = "([^"]+)"', text)
    if not match:
        raise SystemExit("Couldn't find APP_VERSION in weatherlab/config.py")
    return match.group(1)


def find_iscc() -> Path | None:
    """ISCC.exe from the ISCC environment variable if set, else from any Inno Setup version (6, 7, ...) in the usual install folders."""
    override = os.environ.get("ISCC", "").strip()
    if override and Path(override).exists():
        return Path(override)
    roots = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
             Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
             Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"]
    for root in roots:
        for folder in sorted(root.glob("Inno Setup *"), reverse=True):
            if (folder / "ISCC.exe").exists():
                return folder / "ISCC.exe"
    return None


def write_manifest(installer: Path, version: str) -> Path:
    """latest.json: the version, the installer's file name and its SHA-256, which the app checks before installing."""
    digest = hashlib.sha256(installer.read_bytes()).hexdigest()
    installer.parent.mkdir(exist_ok=True)
    manifest = installer.parent / "latest.json"
    manifest.write_text(json.dumps({"version": version, "file": installer.name, "sha256": digest}, indent=2) + "\n",
                        encoding="utf-8")
    return manifest


def main() -> int:
    if not (ROOT / "dist" / "WeatherLab" / "WeatherLab.exe").exists():
        print("Build the exe first: python build_exe.py")
        return 1
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup 6 wasn't found. Install it from jrsoftware.org, then run this again.")
        return 1
    version = app_version()
    (ROOT / "installer").mkdir(exist_ok=True)
    subprocess.run([str(iscc), str(ROOT / "installer.iss")], check=True, cwd=ROOT)
    installer = ROOT / "installer" / f"WeatherLabSetup-{version}.exe"
    manifest = write_manifest(installer, version)
    print(f"Built installer\\{installer.name}")
    print(f"Wrote {manifest}. Upload both files to the place your update address points to.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
