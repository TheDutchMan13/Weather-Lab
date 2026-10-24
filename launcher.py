"""Windows entry point: opens Weather Lab in its own window.

How it works:
- Run with no arguments: picks a free local port, starts this same program with
  --serve in the background (which runs the Streamlit server), waits for it, then
  opens a pywebview window on it. Closing the window stops the server.
- Run with --serve PORT [HOST]: runs the Streamlit server for app.py on HOST:PORT (127.0.0.1 unless
  the Setup page turned on home-network access, which uses 0.0.0.0).

Works both as `python launcher.py` and as the packaged WeatherLab.exe.
The server log is written to %APPDATA%\\WeatherLab\\server.log.
"""

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

APP_TITLE = "Weather Lab"
STARTUP_TIMEOUT_S = 60


def base_dir() -> Path:
    """Folder that holds app.py and weatherlab/. Inside the exe it is the PyInstaller temp folder."""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def log_path() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    path = Path(base) / "WeatherLab" / "server.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def serve(port: int, host: str = "127.0.0.1") -> int:
    """Runs the Streamlit server in this process. Blocks until the server stops."""
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    os.environ["STREAMLIT_SERVER_ENABLE_STATIC_SERVING"] = "true"  # serves static/ for the phone icon
    sys.path.insert(0, str(base_dir()))
    from streamlit.web import cli

    from weatherlab import api, keepalive
    keepalive.keep_awake()  # Windows keeps the PC and its network running while the server is up
    keepalive.start_heartbeat(api.status_text)
    print(f"server starting on {host}:{port}", flush=True)
    sys.argv = ["streamlit", "run", str(base_dir() / "app.py"),
                "--server.headless=true", f"--server.address={host}", f"--server.port={port}"]
    cli.main()
    return 0


def _message_box(text: str) -> None:
    """Shows an error to the user. Falls back to stderr outside Windows."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, APP_TITLE, 0x10)
    except (AttributeError, OSError):
        print(text, file=sys.stderr)


def _wait_until_up(url: str, child: subprocess.Popen) -> bool:
    deadline = time.time() + STARTUP_TIMEOUT_S
    while time.time() < deadline:
        if child.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def open_window() -> int:
    sys.path.insert(0, str(base_dir()))
    from weatherlab import network
    from weatherlab.settings import load_settings
    allow = load_settings().allow_network
    port = network.PREFERRED_PORT if allow and network.port_free(network.PREFERRED_PORT) else free_port()
    host = "0.0.0.0" if allow else "127.0.0.1"
    token = secrets.token_urlsafe(16)  # lets this window in past the password, without a password
    url = f"http://127.0.0.1:{port}/?wl_token={token}"
    # The bundled protobuf C extension (upb) crashed the server with an access violation on 2026-10-24.
    # The pure-Python protobuf is slower but avoids that module; the page's messages are small.
    env = dict(os.environ, WEATHERLAB_PORT=str(port), WEATHERLAB_WINDOW_TOKEN=token,
               PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION="python")
    with open(log_path(), "a", encoding="utf-8") as log:
        log.write(f"\n--- starting {time.strftime('%Y-%m-%d %H:%M:%S')} on {host}:{port}\n")
        log.flush()
        child = subprocess.Popen([sys.executable, "--serve", str(port), host],
                                 stdout=log, stderr=subprocess.STDOUT, env=env)
    try:
        if not _wait_until_up(url, child):
            _message_box(f"{APP_TITLE} could not start its server. See {log_path()} for details.")
            return 1

        import webview  # pywebview: uses the Edge WebView2 control that ships with Windows 11
        webview.create_window(APP_TITLE, url, width=1200, height=800)
        webview.start()
        return 0
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()


if __name__ == "__main__":
    if len(sys.argv) in (3, 4) and sys.argv[1] == "--serve":
        host = sys.argv[3] if len(sys.argv) == 4 else "127.0.0.1"
        sys.exit(serve(int(sys.argv[2]), host))
    sys.exit(open_window())
