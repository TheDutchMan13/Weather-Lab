"""The US/metric display: conversions, alert and record text, and the wind and tropics labels."""

import unittest

from weatherlab import alert_rules, record_alerts, tropics, units, wind_rose


class ConversionTests(unittest.TestCase):
    def test_temperature_converts_and_back(self):
        self.assertAlmostEqual(units.convert("tempf", 212, True), 100)
        self.assertAlmostEqual(units.to_us("tempf", 100, True), 212)
        self.assertEqual(units.convert("tempf", 50, False), 50)

    def test_temperature_change_has_no_offset(self):
        self.assertAlmostEqual(units.convert_change("tempf", 9, True), 5)

    def test_wind_and_rain(self):
        self.assertAlmostEqual(units.convert("windspeedmph", 10, True), 16.09344)
        self.assertAlmostEqual(units.convert("dailyrainin", 1, True), 25.4)
        self.assertAlmostEqual(units.to_us("dailyrainin", 25.4, True), 1)

    def test_readings_without_a_unit_pass_through(self):
        self.assertEqual(units.to_us("humidity", 40, True), 40)
        self.assertEqual(units.convert("humidity", 40, True), 40)

    def test_format_value_metric_and_us(self):
        self.assertEqual(units.format_value("tempf", 212, True), "100.0 °C")
        self.assertEqual(units.format_value("tempf", 72, False, 0), "72 °F")
        self.assertEqual(units.format_value("tempf", None, True), "--")

    def test_suffix_spacing(self):
        self.assertEqual(units.suffix("tempf", False), "°F")
        self.assertEqual(units.suffix("windgustmph", True), " km/h")


class AlertTextTests(unittest.TestCase):
    def test_rule_is_shown_in_the_chosen_units(self):
        rule = {"name": "Hot", "metric": "tempf", "op": ">=", "value": 110}
        self.assertEqual(alert_rules.describe(rule), "Hot: Temperature at or above 110°F")
        self.assertEqual(alert_rules.describe(rule, True), "Hot: Temperature at or above 43.3°C")

    def test_humidity_rule_keeps_percent(self):
        rule = {"name": "Dry", "metric": "humidity", "op": "<=", "value": 20}
        self.assertEqual(alert_rules.describe(rule, True), "Dry: Humidity at or below 20%")

    def test_evaluate_passes_the_units_through(self):
        rule = {"name": "Hot", "metric": "tempf", "op": ">=", "value": 110}
        msgs = alert_rules.evaluate([rule], {"tempf": 115}, 0, {}, True)
        self.assertEqual(msgs, ["Hot: Temperature at or above 43.3°C"])

    def test_record_message_in_metric(self):
        best = {"tempf_max": 90}
        out = record_alerts.check(best, {"tempf": 95}, True)
        self.assertEqual(out[0][2], "New record: Highest temperature 35.0°C (was 32.2°C)")

    def test_record_message_in_us_is_unchanged(self):
        best = {"tempf_max": 90}
        out = record_alerts.check(best, {"tempf": 95})
        self.assertEqual(out[0][2], "New record: Highest temperature 95°F (was 90°F)")


class LabelTests(unittest.TestCase):
    def test_wind_bins(self):
        self.assertEqual(wind_rose.label(0), "0-5 mph")
        self.assertEqual(wind_rose.label(0, True), "0-8 km/h")
        self.assertEqual(wind_rose.label(4, True), "32+ km/h")

    def test_tropics_move_has_number_and_direction(self):
        raw = {"activeStorms": [{"latitudeNumeric": 20, "longitudeNumeric": -70, "name": "Test",
                                 "movementDir": 270, "movementSpeed": 10, "intensity": 60}]}
        row = tropics.parse(raw, (25, -80))[0]
        self.assertEqual(row["move_mph"], 10)
        self.assertEqual(row["move_dir"], tropics.compass(270))


try:
    import reportlab  # noqa: F401
    HAVE_REPORTLAB = True
except ImportError:
    HAVE_REPORTLAB = False


@unittest.skipUnless(HAVE_REPORTLAB, "reportlab is not installed")
class ReportTests(unittest.TestCase):
    def test_reports_build_in_both_systems(self):
        from weatherlab import report
        summary = {"tempf_max": 90, "tempf_min": 60, "tempf_avg": 75, "rain_in": 0.2, "gust_max": 25,
                   "wind_run_mi": 120, "sun_hours": 10, "humidity_min": 20, "humidity_max": 60}
        for metric in (False, True):
            self.assertTrue(report.daily_pdf("2026-10-21", summary, None, metric).startswith(b"%PDF"))
            rows = [(type("D", (), {"month": 10, "year": 2026})(), summary)]
            self.assertTrue(report.yearly_pdf(2026, rows, metric).startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
