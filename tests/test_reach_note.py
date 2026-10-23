"""The note in Settings that says who can reach Weather Lab."""
import unittest

from weatherlab import auth


class ReachNoteTests(unittest.TestCase):
    def test_network_off_means_this_pc_only(self):
        lines = auth.reach_lines(False, False, None)
        self.assertIn("Only this PC", lines[0])
        self.assertEqual(len(lines), 2)

    def test_network_on_without_password_is_blocked(self):
        self.assertIn("blocked until you set a password", auth.reach_lines(True, False, None)[0])

    def test_network_on_with_password_asks_for_it(self):
        self.assertIn("type the password", auth.reach_lines(True, True, None)[0])

    def test_tailscale_line_changes_with_the_address(self):
        with_ts = " ".join(auth.reach_lines(True, True, "100.101.102.103"))
        without = " ".join(auth.reach_lines(True, True, None))
        self.assertIn("same Tailscale account", with_ts)
        self.assertIn("until Tailscale is set up", without)

    def test_internet_and_lockout_are_always_said_when_open(self):
        text = " ".join(auth.reach_lines(True, True, None))
        self.assertIn("doesn't open anything to the internet", text)
        self.assertIn(f"After {auth.MAX_FAILURES} wrong passwords", text)


if __name__ == "__main__":
    unittest.main()
