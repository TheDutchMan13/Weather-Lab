"""API keys in Windows Credential Manager (via the keyring package). Keys never go in files."""

SERVICE = "WeatherLab"


def get_key(name: str) -> str:
    try:
        import keyring
        return keyring.get_password(SERVICE, name) or ""
    except Exception:
        return ""


def set_key(name: str, value: str) -> None:
    import keyring
    if value:
        keyring.set_password(SERVICE, name, value)
    else:
        try:
            keyring.delete_password(SERVICE, name)
        except Exception:
            pass
