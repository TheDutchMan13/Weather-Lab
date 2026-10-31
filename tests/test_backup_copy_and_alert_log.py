"""Second backup folder and the alert history. Uses temporary files only."""

import tempfile
import unittest
from pathlib import Path

from weatherlab import backup, storage


class BackupCopyTests(unittest.TestCase):
    def test_copy_lands_in_the_folder_and_blank_means_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "weatherlab-20261001-030000.db"
            from tests.test_backup import make_db
            make_db(source, 3)  # copies are checked from 0.37.54, so this has to be a real database
            copy = backup.copy_to_folder(source, str(root / "usb"), 5)
            self.assertEqual(copy.read_bytes(), source.read_bytes())
            self.assertIsNone(backup.copy_to_folder(source, "   ", 5))


class AlertLogTests(unittest.TestCase):
    def test_newest_first_with_a_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = storage.connect(Path(tmp) / "test.db")
            storage.log_alert(db, 100, "first")
            storage.log_alert(db, 200, "second")
            self.assertEqual(storage.recent_alerts(db, 1), [(200, "second")])
            self.assertEqual(storage.recent_alerts(db), [(200, "second"), (100, "first")])
            db.close()


if __name__ == "__main__":
    unittest.main()
