"""Password tests. The keyring is replaced with an in-memory fake; no real credentials are touched."""

import unittest
from unittest import mock

from weatherlab import auth


class AuthTests(unittest.TestCase):
    def setUp(self):
        auth.reset_failures()

    def test_hash_and_check(self):
        stored = auth.hash_password("correct horse")
        self.assertTrue(auth.check_password("correct horse", stored))
        self.assertFalse(auth.check_password("wrong password", stored))

    def test_same_password_gets_different_salts(self):
        self.assertNotEqual(auth.hash_password("samepass1"), auth.hash_password("samepass1"))

    def test_malformed_stored_value_is_rejected(self):
        self.assertFalse(auth.check_password("anything", "not-a-hash"))
        self.assertFalse(auth.check_password("anything", ""))

    def test_set_stores_only_the_hash(self):
        with mock.patch.object(auth.secrets, "set_key") as set_key:
            auth.set_password("correct horse")
        name, value = set_key.call_args[0]
        self.assertEqual(name, auth.KEY)
        self.assertNotIn("correct horse", value)
        self.assertTrue(value.startswith("pbkdf2$"))

    def test_sign_in_uses_stored_hash(self):
        stored = auth.hash_password("correct horse")
        with mock.patch.object(auth.secrets, "get_key", return_value=stored):
            self.assertTrue(auth.sign_in("correct horse"))
            self.assertFalse(auth.sign_in("nope"))

    def test_no_password_means_no_sign_in(self):
        with mock.patch.object(auth.secrets, "get_key", return_value=""):
            self.assertFalse(auth.password_set())
            self.assertFalse(auth.sign_in("anything"))

    def test_repeated_failures_lock_for_a_while(self):
        for _ in range(auth.MAX_FAILURES):
            auth.record_failure()
        self.assertGreater(auth.locked_for(), 0)
        auth.reset_failures()
        self.assertEqual(auth.locked_for(), 0)


if __name__ == "__main__":
    unittest.main()
