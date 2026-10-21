"""Import and export tests. Offline, using temporary databases and files."""

import io
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

from weatherlab import importer, storage

PHOENIX = ZoneInfo("America/Phoenix")


class ImporterTests(unittest.TestCase):
    def test_reads_iso_and_epoch_times(self):
        raw = b"time,tempf,humidity\n2026-10-20 13:00,88.5,22\n1792512000,70,40\n"
        rows, ignored = importer.read_csv(raw, PHOENIX)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1][0], 1792512000)
        self.assertEqual(rows[0][1]["tempf"], 88.5)
        self.assertEqual(ignored, [])

    def test_ignores_unknown_columns_and_blank_cells(self):
        raw = b"Timestamp,tempf,mystery,humidity\n2026-10-20 13:00,,x,22\n"
        rows, ignored = importer.read_csv(raw, PHOENIX)
        self.assertEqual(rows[0][1], {"humidity": 22.0})
        self.assertEqual(ignored, ["mystery"])

    def test_missing_time_column(self):
        with self.assertRaises(importer.ImportProblem):
            importer.read_csv(b"tempf,humidity\n88,22\n", PHOENIX)

    def test_bad_time_names_the_line(self):
        with self.assertRaises(importer.ImportProblem) as ctx:
            importer.read_csv(b"time,tempf\n2026-10-20 13:00,80\nnot a time,81\n", PHOENIX)
        self.assertIn("Line 3", str(ctx.exception))

    def test_non_utf8_file_is_rejected(self):
        with self.assertRaises(importer.ImportProblem):
            importer.read_file("time,tempf\n2026-10-20,ü\n".encode("utf-16"), "data.csv")

    def test_store_skips_duplicates_and_rebuilds_days(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = storage.connect(Path(tmp) / "t.db")
            rows, _ = importer.read_csv(b"time,tempf\n2026-10-20 13:00,88\n2026-10-20 13:01,89\n", PHOENIX)
            with mock.patch.object(importer.daily, "rollup_days") as rollup:
                first = importer.store(db, rows, 0.0, 0.0, 0.0, PHOENIX)
                second = importer.store(db, rows, 0.0, 0.0, 0.0, PHOENIX)
            db.close()
        self.assertEqual(first["inserted"], 2)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(second["skipped"], 2)
        self.assertEqual(first["days"], 1)
        self.assertTrue(rollup.called)

    def test_guesses_weather_underground_headers(self):
        headers = ["Time", "Temperature (°F)", "Dew Point", "Humidity", "Wind Speed", "Wind Gust",
                   "Pressure", "Precip. Rate.", "UV", "Solar"]
        self.assertEqual(importer.guess_time_column(headers), "Time")
        m = importer.guess_mapping(headers, "Time")
        self.assertEqual(m["Temperature (°F)"], "tempf")
        self.assertEqual(m["Dew Point"], "dewpointf")
        self.assertEqual(m["Wind Gust"], "windgustmph")
        self.assertEqual(m["Pressure"], "baromrelin")
        self.assertEqual(m["Precip. Rate."], "rainratein")
        self.assertEqual(m["Solar"], "solarradiation")
        self.assertEqual(len(m), 9)

    def test_metric_values_are_converted(self):
        rows = [{"time": "2026-10-20 13:00", "Temperature": "20", "Wind Speed": "10"}]
        out = importer.build_readings(rows, "time", {"Temperature": "tempf", "Wind Speed": "windspeedmph"},
                                      PHOENIX, "metric")
        r = out[0][1]
        self.assertAlmostEqual(r["tempf"], 68.0)
        self.assertAlmostEqual(r["windspeedmph"], 6.21371, places=3)

    def test_export_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = storage.connect(Path(tmp) / "t.db")
            storage.store_reading(db, {"tempf": 88.5, "humidity": 22.0}, ts=1792512000)
            rows = storage.readings_between(db, 0, 2e10)
            db.close()
        raw = importer.export_csv(rows, PHOENIX)
        headers, data = importer.read_file(raw, "export.csv")
        time_col = importer.guess_time_column(headers)
        back = importer.build_readings(data, time_col, importer.guess_mapping(headers, time_col), PHOENIX)
        self.assertEqual(back[0][0], 1792512000)
        self.assertEqual(back[0][1]["tempf"], 88.5)
        self.assertEqual(back[0][1]["humidity"], 22.0)

    def test_export_only_writes_columns_with_values(self):
        raw = importer.export_csv([(1792512000, {"tempf": 80.0})], PHOENIX)
        self.assertEqual(raw.decode("utf-8").splitlines()[0], "time,tempf")

    def test_bad_excel_file_is_rejected(self):
        with self.assertRaises(importer.ImportProblem):
            importer.read_file(b"not a workbook", "data.xlsx")

    def test_excel_file_is_read(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl is not installed")
        wb = Workbook()
        ws = wb.active
        ws.append(["Time", "Temperature", "Humidity"])
        ws.append([datetime(2026, 10, 20, 13, 0), 90, 25])
        buf = io.BytesIO()
        wb.save(buf)
        headers, rows = importer.read_file(buf.getvalue(), "data.xlsx")
        self.assertEqual(headers, ["Time", "Temperature", "Humidity"])
        out = importer.build_readings(rows, "Time", {"Temperature": "tempf", "Humidity": "humidity"}, PHOENIX)
        self.assertEqual(out[0][1]["tempf"], 90.0)


if __name__ == "__main__":
    unittest.main()
