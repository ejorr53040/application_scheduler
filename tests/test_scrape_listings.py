import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import scrape_listings as sl

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _read(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


class TestParseHtmlTables(unittest.TestCase):
    def setUp(self):
        self.rows = sl.parse_html_tables(_read("sample_simplify.md"), "SimplifyJobs")

    def test_row_count(self):
        self.assertEqual(len(self.rows), 3)

    def test_continuation_row_inherits_company(self):
        self.assertEqual(self.rows[1]["company"], "Acme")

    def test_badges_parsed(self):
        backend = self.rows[0]
        self.assertTrue(backend["advanced_degree"])
        self.assertTrue(backend["faang_plus"])
        self.assertFalse(backend["closed"])

        frontend = self.rows[1]
        self.assertTrue(frontend["closed"])

        ml = self.rows[2]
        self.assertTrue(ml["us_citizen_required"])
        self.assertTrue(ml["no_sponsorship"])

    def test_role_text_strips_badges(self):
        self.assertEqual(self.rows[0]["role"], "Software Engineer Intern - Backend")
        self.assertEqual(self.rows[2]["role"], "ML Engineer Intern")

    def test_multi_location_collapsed_with_count(self):
        self.assertIn("New York, NY; Boston, MA", self.rows[2]["location"])
        self.assertIn("(2 locations)", self.rows[2]["location"])

    def test_apply_url_prefers_non_simplify_link(self):
        self.assertEqual(self.rows[0]["apply_url"], "https://acme.example.com/careers/123")

    def test_category_captured(self):
        self.assertIn("Software Engineering", self.rows[0]["category"])


class TestParsePipeTable(unittest.TestCase):
    def setUp(self):
        self.rows = sl.parse_pipe_table(_read("sample_vansh.md"), "vanshb03")

    def test_row_count(self):
        self.assertEqual(len(self.rows), 3)

    def test_continuation_row_inherits_company(self):
        self.assertEqual(self.rows[1]["company"], "Foobar Inc")

    def test_no_sponsorship_badge(self):
        self.assertTrue(self.rows[1]["no_sponsorship"])
        self.assertFalse(self.rows[0]["no_sponsorship"])

    def test_multi_location_collapsed(self):
        self.assertIn("Seattle, WA; Denver, CO", self.rows[2]["location"])
        self.assertIn("(2 locations)", self.rows[2]["location"])

    def test_apply_url_extracted(self):
        self.assertEqual(self.rows[0]["apply_url"], "https://foobar.example.com/apply/1")


if __name__ == "__main__":
    unittest.main()
