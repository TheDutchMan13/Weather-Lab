"""A short log of errors the background collector hit, so Health check can show them.

Each line is: time (seconds), where it happened, and the error. The file keeps the newest lines when it gets big.
Logging never raises: a failing log must not become another way for the collector to fail.
"""

import threading
import time
from pathlib import Path

MAX_BYTES = 100_000
_lock = threading.Lock()


def _file(folder=None) -> Path:
    if folder is None:
        from weatherlab import stations
        folder = stations.folder()
    return Path(folder) / "app_errors.log"


def log(where: str, exc: BaseException, folder=None, now: float | None = None) -> None:
    """Add one line for this error."""
    try:
        stamp = int(now if now is not None else time.time())
        text = f"{type(exc).__name__}: {exc}".replace("\n", " ").replace("\t", " ")[:300]
        path = _file(folder)
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(f"{stamp}\t{where}\t{text}\n")
            if path.stat().st_size > MAX_BYTES:
                lines = path.read_text(encoding="utf-8").splitlines()
                path.write_text("\n".join(lines[len(lines) // 2:]) + "\n", encoding="utf-8")
    except Exception:  # noqa: BLE001 - see the module note
        pass


def recent(since_ts: float, folder=None) -> list[tuple[int, str, str]]:
    """(time, where, error) for each line at or after since_ts, newest first."""
    try:
        lines = _file(folder).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        try:
            stamp = int(parts[0])
        except ValueError:
            continue
        if stamp >= since_ts:
            out.append((stamp, parts[1], parts[2]))
    return sorted(out, reverse=True)
