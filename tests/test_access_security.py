"""Who may reach Weather Lab (0.37.55): this PC, Tailscale, the Host check, sign-in locks per device."""
import unittest
from unittest import mock

from weatherlab import auth


class AddressTests(unittest.TestCase):
    def test_local(self):
        for ip in (None, "", "127.0.0.1", "::1"):
            self.assertTrue(auth.is_local(ip), ip)
        for ip in ("192.168.1.20", "100.101.102.103", "nonsense"):
            self.assertFalse(auth.is_local(ip), ip)

    def test_tailscale(self):
        self.assertTrue(auth.is_tailscale("100.101.102.103"))
        self.assertTrue(auth.is_tailscale("fd7a:115c:a1e0::1"))
        self.assertFalse(auth.is_tailscale("100.128.0.1"))
        self.assertFalse(auth.is_tailscale("192.168.1.20"))
        self.assertFalse(auth.is_tailscale(None))

    def test_client_allowed(self):
        self.assertTrue(auth.client_allowed("192.168.1.20", tailscale_only=False))
        self.assertFalse(auth.client_allowed("192.168.1.20", tailscale_only=True))
        self.assertTrue(auth.client_allowed("100.90.1.2", tailscale_only=True))
        self.assertTrue(auth.client_allowed(None, tailscale_only=True))

    def test_host_header(self):
        for host in ("localhost:8501", "127.0.0.1:8501", "[::1]:8501", "LOCALHOST", None, ""):
            self.assertTrue(auth.local_host_header(host), host)
        for host in ("evil.example:8501", "192.168.1.5:8501", "attacker.test"):
            self.assertFalse(auth.local_host_header(host), host)


class SignInLockTests(unittest.TestCase):
    def setUp(self):
        auth._state.clear()

    def test_lock_is_per_device(self):
        with mock.patch.object(auth, "sign_in", return_value=False):
            for _ in range(auth.MAX_FAILURES):
                auth.try_sign_in("wrong", "192.168.1.66")
            ok, wait = auth.try_sign_in("wrong", "192.168.1.66")
        self.assertFalse(ok)
        self.assertGreater(wait, 0)
        self.assertEqual(auth.locked_for("192.168.1.20"), 0)

    def test_success_clears_the_count(self):
        with mock.patch.object(auth, "sign_in", return_value=False):
            auth.try_sign_in("wrong", "a")
        with mock.patch.object(auth, "sign_in", return_value=True):
            self.assertEqual(auth.try_sign_in("right", "a"), (True, 0))
        self.assertNotIn("a", auth._state)

    def test_password_version_changes_with_the_password(self):
        with mock.patch.object(auth.secrets, "get_key", return_value=""):
            self.assertEqual(auth.password_version(), "")
        with mock.patch.object(auth.secrets, "get_key", return_value="pbkdf2$1$aa$bb"):
            one = auth.password_version()
        with mock.patch.object(auth.secrets, "get_key", return_value="pbkdf2$1$cc$dd"):
            two = auth.password_version()
        self.assertTrue(one and two and one != two)


if __name__ == "__main__":
    unittest.main()
