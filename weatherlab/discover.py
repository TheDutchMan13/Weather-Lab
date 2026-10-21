"""Finding the Ecowitt gateway on the home network. It checks each address on this computer's network range."""

import concurrent.futures
import json
import socket
import urllib.request


def local_ip() -> str | None:
    """This computer's address on the local network, found without sending any data."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("10.255.255.255", 1))
            return sock.getsockname()[0]
    except OSError:
        return None


def candidates(ip: str) -> list[str]:
    """Every other address in the same /24 range (the first three numbers match)."""
    prefix = ".".join(ip.split(".")[:3])
    return [f"{prefix}.{n}" for n in range(1, 255) if f"{prefix}.{n}" != ip]


def is_gateway(ip: str, timeout: float = 0.6) -> bool:
    """True when the address answers like an Ecowitt gateway's live data page."""
    try:
        with urllib.request.urlopen(f"http://{ip}/get_livedata_info", timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and "common_list" in data


def find(timeout: float = 0.6) -> list[str]:
    """Addresses on this network that look like an Ecowitt gateway."""
    ip = local_ip()
    if not ip:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as pool:
        results = list(pool.map(lambda host: (host, is_gateway(host, timeout)), candidates(ip)))
    return [host for host, found in results if found]
