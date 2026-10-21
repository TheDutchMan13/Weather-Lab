"""Stuck sensor check: an outdoor reading that has not changed at all for three hours usually means the sensor
has frozen or lost contact. Only temperature and humidity are checked, because wind and pressure can stay still."""

LABELS = {"tempf": "outdoor temperature", "humidity": "outdoor humidity"}


def stuck_keys(rows: list[tuple], hours: float = 3) -> list[str]:
    """rows: [(timestamp, reading)] in time order. Returns the keys that have one unchanging value across the span."""
    if len(rows) < 2:
        return []
    if rows[-1][0] - rows[0][0] < 0.95 * hours * 3600:
        return []
    out = []
    for key in LABELS:
        values = [reading[key] for _, reading in rows if reading.get(key) is not None]
        if len(values) >= 2 and len(set(values)) == 1:
            out.append(key)
    return out
