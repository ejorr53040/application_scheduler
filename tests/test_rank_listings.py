import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import rank_listings as rl

PROFILE = {
    "languages": ["python", "c++", "opengl"],
    "domain_keywords": ["backend", "graphics"],
    "home_state_codes": ["VT", "MA"],
    "home_city_hint": "burlington, vt",
    "exclude_categories": ["Product Management"],
    "exclude_advanced_degree": True,
    "max_per_company": 2,
}


def make_row(**overrides):
    row = {
        "source": "test",
        "category": "Software Engineering Internship Roles",
        "company": "TestCo",
        "role": "Software Engineer Intern",
        "location": "San Francisco, CA",
        "apply_url": "https://example.com/apply",
        "age": "1d",
        "closed": False,
        "no_sponsorship": False,
        "us_citizen_required": False,
        "advanced_degree": False,
        "faang_plus": False,
    }
    row.update(overrides)
    return row


class TestScoreEntry(unittest.TestCase):
    def test_language_match_beats_no_match(self):
        matching = make_row(role="Backend Engineer Intern - Python")
        non_matching = make_row(role="Product Marketing Intern")
        s_match, _ = rl.score_entry(matching, PROFILE)
        s_no, _ = rl.score_entry(non_matching, PROFILE)
        self.assertGreater(s_match, s_no)

    def test_home_location_boosts_score(self):
        home = make_row(location="Burlington, VT")
        away = make_row(location="San Francisco, CA")
        s_home, reasons_home = rl.score_entry(home, PROFILE)
        s_away, _ = rl.score_entry(away, PROFILE)
        self.assertGreater(s_home, s_away)
        self.assertTrue(any("home location" in r for r in reasons_home))

    def test_advanced_degree_excluded(self):
        row = make_row(advanced_degree=True)
        score, _ = rl.score_entry(row, PROFILE)
        self.assertLessEqual(score, -50)

    def test_closed_excluded(self):
        row = make_row(closed=True)
        score, _ = rl.score_entry(row, PROFILE)
        self.assertLessEqual(score, -50)

    def test_sponsorship_conflict_excludes(self):
        row = make_row(no_sponsorship=True)
        profile = dict(PROFILE, needs_sponsorship=True)
        score, reasons = rl.score_entry(row, profile)
        self.assertLessEqual(score, -50)
        self.assertTrue(any("EXCLUDED" in r for r in reasons))


class TestDedupe(unittest.TestCase):
    def test_exact_duplicate_removed(self):
        rows = [make_row(), make_row()]
        self.assertEqual(len(rl.dedupe(rows)), 1)

    def test_different_location_kept_distinct(self):
        rows = [make_row(location="Boston, MA"), make_row(location="Austin, TX")]
        self.assertEqual(len(rl.dedupe(rows)), 2)


class TestCollapseMultiLocationDupes(unittest.TestCase):
    def test_keeps_richer_location_string(self):
        rows = [
            {**make_row(), "location": "Seattle, WA"},
            {**make_row(), "location": "Seattle, WA; Denver, CO (2 locations)"},
        ]
        collapsed = rl.collapse_multi_location_dupes(rows)
        self.assertEqual(len(collapsed), 1)
        self.assertIn("2 locations", collapsed[0]["location"])


class TestBuildShortlist(unittest.TestCase):
    def test_per_company_cap_enforced(self):
        rows = [make_row(role=f"Software Engineer Intern {i}", location="Burlington, VT") for i in range(5)]
        shortlist = rl.build_shortlist(rows, PROFILE, top_n=50)
        self.assertLessEqual(len(shortlist), PROFILE["max_per_company"])

    def test_closed_roles_never_appear(self):
        rows = [make_row(closed=True), make_row(role="Backend Engineer Intern - Python")]
        shortlist = rl.build_shortlist(rows, PROFILE, top_n=50)
        self.assertEqual(len(shortlist), 1)
        self.assertIn("Python", shortlist[0]["role"])

    def test_output_is_ranked_best_first(self):
        rows = [
            make_row(company="A", role="Product Marketing Intern"),
            make_row(company="B", role="Backend Engineer Intern - Python", location="Burlington, VT"),
        ]
        shortlist = rl.build_shortlist(rows, PROFILE, top_n=50)
        self.assertEqual(shortlist[0]["company"], "B")
        self.assertEqual(shortlist[0]["rank"], 1)


if __name__ == "__main__":
    unittest.main()
