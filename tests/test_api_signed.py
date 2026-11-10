"""Signed API requests (0.37.59): the token never crosses the network, and captured requests can't be replayed."""

import hashlib
import secrets
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from weatherlab import api, storage
from weatherlab.settings import Settings



class FakeKeys:
    def __init__(self):
        self.values = {}

    def get_key(self, name):
        return self.values.get(name, "")

    def set_key(self, name, value):
        self.values[name] = value


def signed(token, path, when, nonce=None):
    nonce = nonce or secrets.token_hex(12)
    key = hashlib.sha256(token.encode()).hexdigest()
    return f"WL-HMAC {api.signature(key, path, str(int(when)), nonce)}", {"X-WL-Time": str(int(when)), "X-WL-Nonce": nonce}


class SignedTests(unittest.TestCase):
    def setUp(self):
        self.keys = FakeKeys()
        p = mock.patch.object(api, "keystore", self.keys)
        p.start()
        self.addCleanup(p.stop)
        api._fails.clear()
        api._nonces.clear()
        self.tmp = Path(tempfile.mkdtemp())
        self.db = storage.connect(self.tmp / "t.db")
        self.addCleanup(self.db.close)
        self.s = replace(Settings(), timezone="America/Phoenix", units="US")
        self.now = time.time()
        self.t = api.create_token()

    def call(self, path, auth, headers=None, client="10.0.0.9"):
        return api.route(path, auth, self.db, self.s, self.now, client, headers)

    def test_signed_request_works(self):
        auth, h = signed(self.t, "/api/v1/status", self.now)
        self.assertEqual(self.call("/api/v1/status", auth, h)[0], 200)

    def test_known_vector_matches_the_phone(self):
        # The same values are checked in the Android and watch unit tests, so all three sign alike.
        key = hashlib.sha256(b"test-token").hexdigest()
        self.assertEqual(api.signature(key, "/api/v1/status", "1700000000", "abcdef0123456789"),
                         "f0ee0c626b7f8daaf4975dc0ca319909551b52d04209421a3ad845d08d49f06d")

    def test_replay_is_refused(self):
        auth, h = signed(self.t, "/api/v1/status", self.now)
        self.assertEqual(self.call("/api/v1/status", auth, h)[0], 200)
        self.assertEqual(self.call("/api/v1/status", auth, h)[0], 401)

    def test_signature_is_tied_to_the_path(self):
        auth, h = signed(self.t, "/api/v1/status", self.now)
        self.assertEqual(self.call("/api/v1/export/daily", auth, h)[0], 401)

    def test_wrong_token_and_bad_headers(self):
        auth, h = signed("not-the-token", "/api/v1/status", self.now)
        self.assertEqual(self.call("/api/v1/status", auth, h)[0], 401)
        auth, h = signed(self.t, "/api/v1/status", self.now, nonce="short")
        self.assertEqual(self.call("/api/v1/status", auth, h)[0], 401)
        self.assertEqual(self.call("/api/v1/status", auth, None)[0], 401)

    def test_clock_too_far_off_says_so_and_isnt_counted(self):
        auth, h = signed(self.t, "/api/v1/status", self.now - 3600)
        code, body = self.call("/api/v1/status", auth, h)
        self.assertEqual(code, 401)
        self.assertIn("clock", body["error"])
        self.assertNotIn("10.0.0.9", api._fails)

    def test_bearer_works_until_signing_is_seen_then_is_refused(self):
        self.assertEqual(self.call("/api/v1/status", f"Bearer {self.t}")[0], 200)
        auth, h = signed(self.t, "/api/v1/status", self.now)
        self.assertEqual(self.call("/api/v1/status", auth, h)[0], 200)
        code, body = self.call("/api/v1/status", f"Bearer {self.t}")
        self.assertEqual(code, 401)
        self.assertIn("Update this app", body["error"])

    def test_new_token_resets_the_bearer_lock(self):
        auth, h = signed(self.t, "/api/v1/status", self.now)
        self.call("/api/v1/status", auth, h)
        fresh = api.create_token()
        self.assertEqual(self.call("/api/v1/status", f"Bearer {fresh}")[0], 200)

    def test_query_string_is_not_part_of_the_signature(self):
        auth, h = signed(self.t, "/api/v1/status", self.now)
        self.assertNotEqual(self.call("/api/v1/status?x=1", auth, h)[0], 401)


if __name__ == "__main__":
    unittest.main()
