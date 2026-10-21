"""Station watch: one notification when readings stop for a while, and one when they start again."""

LIMIT_SECONDS = 900  # no reading for this long counts as offline


def check(was_offline: bool, last_seen, now: float, limit: float = LIMIT_SECONDS) -> tuple[bool, str | None]:
    """(offline now, message to send or None). last_seen is when a reading last arrived, or None if not known yet."""
    if last_seen is None:
        return was_offline, None
    stale = now - last_seen > limit
    if stale and not was_offline:
        return True, "Weather Lab hasn't received a reading from the station for 15 minutes. Check its power and network connection."
    if was_offline and not stale:
        return False, "The station is sending readings again."
    return was_offline, None
