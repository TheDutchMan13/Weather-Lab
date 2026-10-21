"""Dew point in plain words. Dew point is the better guide to how muggy it feels."""


def text(dew_point_f: float) -> str:
    if dew_point_f < 55:
        return "dry and comfortable"
    if dew_point_f < 60:
        return "comfortable"
    if dew_point_f < 65:
        return "a little humid"
    if dew_point_f < 70:
        return "muggy"
    return "oppressive"
