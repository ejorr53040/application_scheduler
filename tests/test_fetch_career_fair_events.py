import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fetch_career_fair_events as cf


def make_event(title, types=None, topics=None):
    return {
        "title": title,
        "first_date": "2026-10-01",
        "localist_url": "https://events.uvm.edu/event/x",
        "filters": {
            "event_types": [{"name": t} for t in (types or [])],
            "event_topics": [{"name": t} for t in (topics or [])],
        },
    }


class TestExtractOrg(unittest.TestCase):
    def test_network_with_pattern_is_always_trusted(self):
        self.assertEqual(cf.extract_org("Network with Marsh Captive Solutions"), "Marsh Captive Solutions")

    def test_connect_with_pattern_strips_trailing_colon_clause(self):
        org = cf.extract_org("Connect with Fidelity Investments: Networking, Career Conversations")
        self.assertEqual(org, "Fidelity Investments")

    def test_at_uvm_pattern_requires_career_topic(self):
        self.assertIsNone(cf.extract_org("GlobalFoundries at UVM", has_career_topic=False))
        self.assertEqual(cf.extract_org("GlobalFoundries at UVM", has_career_topic=True), "GlobalFoundries")

    def test_info_session_pattern_requires_career_topic(self):
        self.assertIsNone(cf.extract_org("Sustainable Campus Fund Info Session", has_career_topic=False))

    def test_no_match_returns_none(self):
        self.assertIsNone(cf.extract_org("Field Hockey vs Merrimack"))


class TestClassify(unittest.TestCase):
    def test_fair_keyword_in_title_is_fair(self):
        ev = make_event("2026 UVM Job and Internship Fair")
        result = cf.classify(ev)
        self.assertTrue(result["is_fair"])

    def test_network_with_is_org_visit(self):
        ev = make_event("Network with Acme Corp")
        result = cf.classify(ev)
        self.assertTrue(result["is_org_visit"])
        self.assertEqual(result["organization"], "Acme Corp")

    def test_admissions_info_session_is_rejected(self):
        ev = make_event("Admissions Information Session and Campus Tour", types=["Info sessions and tabling"])
        self.assertIsNone(cf.classify(ev))

    def test_faculty_workshop_at_uvm_is_rejected(self):
        ev = make_event('Demystifying the RPT Process at UVM Workshop II', types=["Classes and workshops"])
        self.assertIsNone(cf.classify(ev))

    def test_at_uvm_with_career_topic_is_accepted(self):
        ev = make_event(
            "GlobalFoundries at UVM",
            types=["Meetings and gatherings", "Networking"],
            topics=["Career Readiness and Professional Development"],
        )
        result = cf.classify(ev)
        self.assertIsNotNone(result)
        self.assertEqual(result["organization"], "GlobalFoundries")

    def test_irrelevant_event_returns_none(self):
        ev = make_event("Board Game Night", types=["Free"])
        self.assertIsNone(cf.classify(ev))


if __name__ == "__main__":
    unittest.main()
