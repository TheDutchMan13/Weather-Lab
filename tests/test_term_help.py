"""The ? help beside terms is turned off (0.37.17): term_help draws nothing on any page."""
import unittest
from unittest import mock

try:
    import streamlit  # noqa: F401
    from weatherlab.screens import common
except ImportError:
    common = None


@unittest.skipIf(common is None, "streamlit is not installed")
class TermHelpTests(unittest.TestCase):
    def test_no_question_mark_for_a_known_term(self):
        with mock.patch.object(common.st, "popover") as pop:
            common.term_help("dew_point")
        pop.assert_not_called()

    def test_no_question_mark_for_an_unknown_term(self):
        with mock.patch.object(common.st, "popover") as pop:
            common.term_help("not_a_term")
        pop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
