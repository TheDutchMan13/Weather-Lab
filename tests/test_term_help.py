"""The small ? beside a term: it shows the short meaning on hover, and the full text inside its popover."""
import sys
import unittest
from unittest import mock

try:
    import streamlit  # noqa: F401
    from weatherlab.screens import common
except ImportError:
    common = None


@unittest.skipIf(common is None, "streamlit is not installed")
class TermHelpTests(unittest.TestCase):
    def test_known_term_gets_a_popover_with_its_help_text(self):
        with mock.patch.object(common.st, "popover") as pop, mock.patch.object(common.st, "markdown") as md:
            common.term_help("dew_point")
        pop.assert_called_once()
        self.assertEqual(pop.call_args.args[0], "?")
        self.assertIn("muggier", pop.call_args.kwargs["help"])
        self.assertTrue(any("Dew point" in str(c.args[0]) for c in md.call_args_list))

    def test_unknown_term_draws_nothing(self):
        with mock.patch.object(common.st, "popover") as pop:
            common.term_help("not_a_term")
        pop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
