"""Build the Windows installer with Inno Setup.

Run build_exe.py first, then:
    python build_installer.py

Needs Inno Setup 6, a free install from jrsoftware.org. Output: installer\\WeatherLabSetup-0.10.0.exe
"""

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def find_iscc() -> Path | None:
    """ISCC.exe from any Inno Setup version (6, 7, ...) in the usual install folders."""
    roots = [Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
             Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
             Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"]
    for root in roots:
        for folder in sorted(root.glob("Inno Setup *"), reverse=True):
            if (folder / "ISCC.exe").exists():
                return folder / "ISCC.exe"
    return None


def main() -> int:
    if not (ROOT / "dist" / "WeatherLab" / "WeatherLab.exe").exists():
        print("Build the exe first: python build_exe.py")
        return 1
    iscc = find_iscc()
    if iscc is None:
        print("Inno Setup 6 wasn't found. Install it from jrsoftware.org, then run this again.")
        return 1
    subprocess.run([str(iscc), str(ROOT / "installer.iss")], check=True, cwd=ROOT)
    print("Built installer\\WeatherLabSetup-0.10.0.exe")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
