"""Security fixes from the audit (0.37.67)."""
import io
import pathlib
import re
import unittest

from weatherlab import netread

ROOT = pathlib.Path(__file__).resolve().parents[1]


def src(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


class RebindingGate(unittest.TestCase):
    def test_this_pc_must_also_name_this_pc(self):
        gate = src("app.py").split("def access_gate", 1)[1].split("\ndef ", 1)[0]
        # the Host check runs before a local connection is trusted, with network access on as well as off
        self.assertIn('if local and not auth.local_host_header(st.context.headers.get("Host")):', gate)
        self.assertLess(gate.index("if local and not auth.local_host_header"), gate.index('st.session_state["on_pc"] = True\n        st.session_state["signed_in"]'))

    def test_window_token_needs_a_local_name_too(self):
        gate = src("app.py").split("def access_gate", 1)[1]
        self.assertRegex(gate, r'wl_token"\) == token\s+and auth\.local_host_header')


class PcOnly(unittest.TestCase):
    def test_restore_import_and_remove_are_pc_only(self):
        data = src("weatherlab/screens/data.py")
        self.assertEqual(data.count('pc_only("Restoring a backup")'), 2)
        self.assertIn('pc_only("Importing")', data)
        self.assertIn('pc_only("Removing a station")', src("weatherlab/screens/system.py"))

    def test_station_and_broker_address_are_pc_only(self):
        system = src("weatherlab/screens/system.py")
        self.assertIn("if moved and not on_this_pc():", system)
        tools = system.split("def _station_tools", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("if not on_this_pc():", tools)
        self.assertIn('st.session_state.get("on_pc", True)', src("weatherlab/screens/setup_wizard.py"))


class SizeLimit(unittest.TestCase):
    def test_small_reply_passes(self):
        self.assertEqual(netread.read_limited(io.BytesIO(b"abc"), limit=10), b"abc")

    def test_large_reply_refused_as_value_error(self):
        with self.assertRaises(ValueError):
            netread.read_limited(io.BytesIO(b"x" * 11), limit=10)

    def test_every_outside_reader_uses_the_limit(self):
        for name in ("parse", "gateway_sensors", "nws", "windmap", "tropics", "airquality", "noaa", "discover", "uploads"):
            text = src(f"weatherlab/{name}.py")
            self.assertIn("netread.read_limited(", text, name)
            self.assertNotRegex(text, r"\b(r|response|resp)\.read\(\)", name)


class Supply(unittest.TestCase):
    def test_release_installs_the_lock_with_hashes(self):
        self.assertIn("pip install --require-hashes -r requirements-lock.txt", src(".github/workflows/release.yml"))

    def test_lock_matches_requirements(self):
        lock = dict(re.findall(r"^([a-z0-9_.\-]+)==([^\s\\]+)", src("requirements-lock.txt"), re.M))
        for line in src("requirements.txt").splitlines() + src("requirements-build.txt").splitlines():
            line = line.split("#", 1)[0].strip()
            if not line or line.startswith("-r"):
                continue
            name = re.split(r"[<>=!~ ]", line, 1)[0].lower()
            self.assertIn(name, lock, f"{name} is in the requirements but not in requirements-lock.txt")
        self.assertEqual(lock["streamlit"], "1.67.0")
        self.assertTrue(lock["pillow"].startswith("13."))

    def test_actions_are_pinned_to_commits(self):
        for wf in (ROOT / ".github" / "workflows").glob("*.yml"):
            for use in re.findall(r"uses:\s*(\S+)", wf.read_text(encoding="utf-8")):
                self.assertRegex(use, r"@[0-9a-f]{40}$", f"{wf.name}: {use}")


if __name__ == "__main__":
    unittest.main()
