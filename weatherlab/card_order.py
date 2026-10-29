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
