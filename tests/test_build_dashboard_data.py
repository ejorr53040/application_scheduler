import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import build_dashboard_data as bd


class TestComputeStage(unittest.TestCase):
    def test_no_files_is_shortlisted(self):
        self.assertEqual(bd.compute_stage({}, {}), 0)

    def test_posting_only(self):
        self.assertEqual(bd.compute_stage({}, {"posting.md": "x"}), 1)

    def test_full_packet_is_ready(self):
        files = {"posting.md": "x", "resume.md": "x", "cover_letter.md": "x", "answers.md": "x"}
        self.assertEqual(bd.compute_stage({}, files), 4)

    def test_status_override_beats_files(self):
        files = {"posting.md": "x", "resume.md": "x"}
        entry = {"application_status": "interviewing"}
        self.assertEqual(bd.compute_stage(entry, files), 6)

    def test_rejected_status_is_negative_one(self):
        entry = {"application_status": "rejected"}
        self.assertEqual(bd.compute_stage(entry, {}), -1)

    def test_unrecognized_status_falls_back_to_files(self):
        entry = {"application_status": "some future status"}
        files = {"posting.md": "x"}
        self.assertEqual(bd.compute_stage(entry, files), 1)


class TestStageLabel(unittest.TestCase):
    def test_known_stage(self):
        self.assertEqual(bd.stage_label(4), "Packet ready")

    def test_status_label_takes_priority(self):
        self.assertEqual(bd.stage_label(5), "Applied")

    def test_rejected_label(self):
        self.assertEqual(bd.stage_label(-1), "Rejected")


class TestBuild(unittest.TestCase):
    def test_builds_entries_with_no_packet(self):
        shortlist_data = {
            "generated_on": "2026-01-01",
            "total_scanned": 10,
            "shortlist": [{
                "rank": 1, "company": "Acme", "role": "SWE Intern", "location": "Remote",
                "category": "Software Engineering", "apply_url": "https://x", "match_score": 5.0,
                "why_it_fits": "test", "flags": {"no_sponsorship": False, "us_citizen_required": False, "faang_plus": False},
            }],
        }
        out = bd.build(shortlist_data, applications_root="/tmp/does-not-matter")
        self.assertEqual(len(out["entries"]), 1)
        self.assertFalse(out["entries"][0]["has_packet"])
        self.assertEqual(out["entries"][0]["stage"], 0)


if __name__ == "__main__":
    unittest.main()
