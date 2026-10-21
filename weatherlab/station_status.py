"""Station status: one answer to "is everything working", and what needs attention if not."""


def summary(reporting_state, feed_errors, sensors):
    """reporting_state: "ok", "slow", "silent" or "none" (from health.age_status). sensors: dicts with name, battery and
    signal states (see gateway_sensors). Returns (ok, problems)."""
    problems = []
    if reporting_state == "silent":
        problems.append("The station hasn't reported for a while. Check its power and network connection.")
    elif reporting_state == "slow":
        problems.append("Readings are arriving late.")
    elif reporting_state == "none":
        problems.append("No readings yet.")
    problems.extend(feed_errors)
    for sensor in sensors:
        if sensor["battery"] == "low":
            problems.append(f"{sensor['name']}: battery is low.")
        elif sensor["battery"] == "watch":
            problems.append(f"{sensor['name']}: battery is getting low.")
        if sensor["signal"] in ("weak", "none"):
            problems.append(f"{sensor['name']}: weak radio signal.")
    return (not problems), problems
