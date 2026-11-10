"""Network errors in plain words (0.37.58). Users saw "(URLError)" or "(TimeoutError)"; now they see what happened
and what to try. Kept free of Streamlit so it can be tested."""

import socket
import ssl
import urllib.error


def why(exc: BaseException) -> str:
    """A short reason for a failed network request, without Python class names."""
    reason = getattr(exc, "reason", None)
    inner = reason if isinstance(reason, BaseException) else None
    for e in (exc, inner):
        if e is None:
            continue
        if isinstance(e, urllib.error.HTTPError):
            if e.code in (401, 403):
                return "it refused the key or sign-in"
            if e.code == 404:
                return "the address was not found"
            if e.code == 429:
                return "too many requests, so it asked us to wait"
            if e.code >= 500:
                return "the service had a problem on its side"
            return f"it answered with error {e.code}"
        if isinstance(e, (socket.timeout, TimeoutError)):
            return "it didn't answer in time"
        if isinstance(e, socket.gaierror):
            return "the address couldn't be found. Check the internet connection"
        if isinstance(e, ConnectionRefusedError):
            return "it refused the connection"
        if isinstance(e, ssl.SSLError):
            return "the secure connection failed"
        if isinstance(e, OSError) and getattr(e, "errno", None) in (51, 65, 101, 113, 10051, 10065):
            return "it isn't reachable from this network"
    if isinstance(exc, ValueError):
        return "its answer didn't make sense"
    return "the connection failed"


def station(ip: str, exc: BaseException) -> str:
    return (f"Can't reach the station at {ip}: {why(exc)}. Check that the station is powered on and on the same "
            "network, and that the address in Settings, Station is right.")


def service(name: str, exc: BaseException) -> str:
    return f"Couldn't reach {name}: {why(exc)}."
