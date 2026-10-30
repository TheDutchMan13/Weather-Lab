"""The order of the reading cards on Home (0.37.35): move one up or down, or add and remove cards.

Pure helpers with no streamlit, so the tests run without the page's dependencies."""


def move(cards: list, key: str, step: int) -> list:
    """The list with key moved up (step -1) or down (step +1) one place. Unknown keys and the ends change nothing."""
    cards = list(cards)
    if key not in cards:
        return cards
    i = cards.index(key)
    j = i + step
    if 0 <= j < len(cards):
        cards[i], cards[j] = cards[j], cards[i]
    return cards


def merge(current: list, picked: list) -> list:
    """The cards after the multiselect changed: cards still picked keep their place, new ones go on the end."""
    kept = [k for k in current if k in picked]
    return kept + [k for k in picked if k not in kept]


WIND_WORDS = ("wind", "gust", "rain")


def group_of(label: str) -> str:
    """Which section of Home a card sits in: "Wind and rain" for wind, gust and rain cards, else "Air"."""
    return "Wind and rain" if any(w in label.lower() for w in WIND_WORDS) else "Air"


def rows(keys: list, wide, per_row: int = 3) -> list[list]:
    """The cards in display rows (0.37.42): a wide card has a row to itself; small cards share rows of up to
    per_row, keeping their order. None keys (cards with no setting, such as comfort tiles) are always small."""
    out, row = [], []
    for k in keys:
        if k is not None and k in wide:
            if row:
                out.append(row)
                row = []
            out.append([k])
            continue
        row.append(k)
        if len(row) == per_row:
            out.append(row)
            row = []
    if row:
        out.append(row)
    return out
