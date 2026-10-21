"""Build WeatherLab.exe with PyInstaller.

Run from the project folder:
    python build_exe.py            windowed build (no console)
    python build_exe.py --console  keeps a console window, useful when something fails

Output: dist\\WeatherLab\\WeatherLab.exe (run it from that folder, or copy the whole folder).
"""

import subprocess
import sys

args = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--name", "WeatherLab",
    "--collect-all", "streamlit",
    "--copy-metadata", "streamlit",
    "--collect-all", "webview",
    "--collect-all", "reportlab",
    "--collect-all", "keyring",
    "--collect-all", "plyer",
    "--collect-all", "openpyxl",
    "--add-data", "app.py;.",
    "--add-data", "weatherlab;weatherlab",
    "--add-data", "static;static",
]
if "--console" not in sys.argv:
    args.append("--noconsole")
args.append("launcher.py")

subprocess.run(args, check=True)
print("Built dist\\WeatherLab\\WeatherLab.exe")
