import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fetch_posting as fp

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


class TestCleanHtml(unittest.TestCase):
    def test_br_becomes_newline(self):
        self.assertEqual(fp.clean_html("a<br>b"), "a\nb")

    def test_paragraphs_become_blank_lines(self):
        self.assertEqual(fp.clean_html("<p>a</p><p>b</p>"), "a\n\nb")

    def test_list_items_become_bullets(self):
        self.assertIn("- one", fp.clean_html("<ul><li>one</li></ul>"))

    def test_none_input_returns_none(self):
        self.assertIsNone(fp.clean_html(None))

    def test_tags_stripped(self):
        self.assertEqual(fp.clean_html("<strong>bold</strong>"), "bold")


class TestExtractJsonLdJobPosting(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(FIXTURES, "sample_jobposting.html"), encoding="utf-8") as f:
            self.html = f.read()

    def test_extracts_title(self):
        result = fp.extract_jsonld_jobposting(self.html, "https://example.com/job/1")
        self.assertEqual(result["platform"], "jsonld")
        self.assertEqual(result["title"], "Intern - Sample Role")

    def test_extracts_location_from_address(self):
        result = fp.extract_jsonld_jobposting(self.html, "https://example.com/job/1")
        self.assertEqual(result["location"], "Springfield, IL")

    def test_description_html_present_for_cleaning(self):
        result = fp.extract_jsonld_jobposting(self.html, "https://example.com/job/1")
        self.assertIn("Write code", result["description_html"])

    def test_no_jsonld_returns_unknown_platform(self):
        result = fp.extract_jsonld_jobposting("<html><body>nothing here</body></html>", "https://example.com/job/2")
        self.assertEqual(result["platform"], "unknown")

    def test_workday_url_gets_spa_hint(self):
        result = fp.extract_jsonld_jobposting(
            "<html><body>empty shell</body></html>",
            "https://acme.wd1.myworkdayjobs.com/job/1",
        )
        self.assertIn("JS-rendered", result["note"])


class TestPlatformUrlDetection(unittest.TestCase):
    def test_greenhouse_url_not_matched_returns_none(self):
        self.assertIsNone(fp.try_greenhouse("https://example.com/not-greenhouse"))

    def test_lever_url_not_matched_returns_none(self):
        self.assertIsNone(fp.try_lever("https://example.com/not-lever"))

    def test_ashby_url_not_matched_returns_none(self):
        self.assertIsNone(fp.try_ashby("https://example.com/not-ashby"))


if __name__ == "__main__":
    unittest.main()
