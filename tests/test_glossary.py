import unittest

from weatherlab import glossary


class GlossaryTests(unittest.TestCase):
    def test_every_term_has_both_texts(self):
        for t in glossary.TERMS:
            self.assertTrue(t["name"].strip(), t["key"])
            self.assertTrue(t["short"].strip(), t["key"])
            self.assertTrue(t["long"].strip(), t["key"])

    def test_one_line_is_short(self):
        for t in glossary.TERMS:
            self.assertLessEqual(len(t["short"]), 130, t["key"])

    def test_keys_are_unique(self):
        keys = [t["key"] for t in glossary.TERMS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_short_lookup(self):
        self.assertIn("muggier", glossary.short("dew_point"))
        self.assertEqual(glossary.short("no_such_term"), "")

    def test_search(self):
        self.assertEqual(glossary.search("")[0]["key"], glossary.TERMS[0]["key"])
        self.assertTrue(any(t["key"] == "dew_point" for t in glossary.search("dew")))
        self.assertEqual(glossary.search("zzzz-nothing"), [])

    def test_matches_app_levels(self):
        from weatherlab import dew, sun_uv
        self.assertEqual(dew.text(54), "dry and comfortable")
        self.assertIn("55", glossary.find("dew_point")["long"])
        self.assertEqual(sun_uv.uv_word(2), "low")
        self.assertIn("0–2 low", glossary.find("uv_index")["short"])


if __name__ == "__main__":
    unittest.main()
