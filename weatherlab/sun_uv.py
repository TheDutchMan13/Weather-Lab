"""Sun and UV: sunburn time by skin type, and sunshine hours. Rough estimates from the station's readings.

Sunburn time uses the minimal erythema dose (MED) for each skin type from the WHO's sun guidance.
Sunshine counts time when solar radiation is at least 120 W/m², the WMO threshold.
"""

MED_J_M2 = {  # minimal erythema dose by skin type
    "Type I (always burns)": 200,
    "Type II (burns easily)": 250,
    "Type III (sometimes burns)": 300,
    "Type IV (rarely burns)": 400,
    "Type V (very rarely burns)": 500,
    "Type VI (never burns)": 1000,
}
ERYTHEMAL_W_M2_PER_UVI = 0.025  # erythemal irradiance per UV index point
SUNSHINE_W_M2 = 120
MAX_GAP_S = 600  # a bigger gap between readings is not counted as sunshine


def burn_minutes(uvi, skin):
    """Minutes of full sun before skin of this type starts to burn, or None without a UV reading."""
    if uvi is None or uvi <= 0:
        return None
    return MED_J_M2[skin] / (uvi * ERYTHEMAL_W_M2_PER_UVI) / 60


def sunshine_hours(samples):
    """samples: (timestamp, solar W/m²) pairs in time order. Returns hours of sunshine."""
    seconds = 0.0
    for (t0, s0), (t1, _) in zip(samples, samples[1:]):
        if s0 is not None and s0 >= SUNSHINE_W_M2:
            seconds += min(t1 - t0, MAX_GAP_S)
    return seconds / 3600
