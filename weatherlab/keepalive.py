"""Keeps the PC awake while Weather Lab runs, and writes a heartbeat line to the server log every minute.

The heartbeat shows, in server.log, the last moment the app was still running. If the log stops mid-day, the
app (or the PC) stopped then. Windows can be told to stay awake by the program itself: the screen may still turn off,
but the PC and its network keep running. Nothing here changes what the app does with your data.
"""

import sys
import threading
import time
from datetime import datetime

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
HEARTBEAT_SECONDS = 60


def keep_awake() -> bool:
    """Asks Windows not to sleep while this process runs. Returns True when Windows accepted the request."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        result = ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        return bool(result)
    except (AttributeError, OSError):
        return False


def format_beat(now: float, threads: list[str], api_text: str) -> str:
    """One heartbeat line: the time, how many app threads are alive, and the API status."""
    pollers = sum(1 for name in threads if name.startswith("weatherlab-poller"))
    stamp = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
    return f"heartbeat {stamp} threads={len(threads)} collectors={pollers} api={api_text}"


def _beat(api_status) -> None:
    while True:
        try:
            names = [t.name for t in threading.enumerate()]
            print(format_beat(time.time(), names, api_status()), flush=True)
        except Exception as exc:  # a failing log line must never stop the app
            print(f"heartbeat error {type(exc).__name__}: {exc}", flush=True)
        time.sleep(HEARTBEAT_SECONDS)


def start_heartbeat(api_status) -> None:
    """Starts the heartbeat thread once. api_status is a function that returns the API's status text."""
    threading.Thread(target=_beat, args=(api_status,), daemon=True, name="weatherlab-heartbeat").start()
