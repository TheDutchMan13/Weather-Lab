"""Reads a reply with a size limit (0.37.67), so a broken or hostile station or service can't fill the PC's memory
by sending an endless answer."""

MAX_BYTES = 8 * 1024 * 1024  # 8 MB: far more than any weather reply


class TooLarge(ValueError):
    """The reply was bigger than the limit. A ValueError, so the callers' existing error handling covers it."""


def read_limited(response, limit: int = MAX_BYTES) -> bytes:
    data = response.read(limit + 1)
    if len(data) > limit:
        raise TooLarge(f"The reply was larger than {limit // (1024 * 1024)} MB, so it was ignored.")
    return data
