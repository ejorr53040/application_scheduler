#!/usr/bin/env python3
"""
Build dashboard/data.json by combining a shortlist.json (from rank_listings.py)
with whatever files exist in each entry's application packet folder.

Usage:
    python3 build_dashboard_data.py --shortlist shortlist.json \\
        --applications-dir applications --out dashboard/data.json

A shortlist entry opts into a packet by having an "application_folder" field
(relative to --applications-root, default: the shortlist file's directory)
pointing at a folder containing any of: posting.md/.json, resume.md,
cover_letter.md, answers.md, contacts.md.
"""
import argparse
import json
import os

FILE_STAGES = [
    ("posting", ["posting.md", "posting.json"]),
    ("resume", ["resume.md"]),
    ("cover_letter", ["cover_letter.md"]),
    ("answers", ["answers.md"]),
]

STAGE_LABELS = {
    0: "Shortlisted",
    1: "Posting researched",
    2: "Resume tailored",
    3: "Cover letter drafted",
    4: "Packet ready",
}

STATUS_OVERRIDE_STAGE = {
    "not started": None,
    "packet ready": 4,
    "applied": 5,
    "interviewing": 6,
    "offer": 7,
    "rejected": -1,
}
STATUS_LABELS = {5: "Applied", 6: "Interviewing", 7: "Offer", -1: "Rejected"}


def read_file(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return None


def load_packet_files(folder_abs):
    files = {}
    if not os.path.isdir(folder_abs):
        return files
    for name in sorted(os.listdir(folder_abs)):
        full = os.path.join(folder_abs, name)
        if os.path.isfile(full):
            files[name] = read_file(full)
    return files


def compute_stage(entry, files):
    stage = 0
    for i, (_key, names) in enumerate(FILE_STAGES, start=1):
        if any(n in files for n in names):
            stage = i
    status = (entry.get("application_status") or "not started").strip().lower()
    override = STATUS_OVERRIDE_STAGE.get(status)
    if override is not None:
        stage = override
    return stage


def stage_label(stage):
    return STATUS_LABELS.get(stage) or STAGE_LABELS.get(stage, "Unknown")


def build(shortlist_data, applications_root):
    entries = []
    for entry in shortlist_data["shortlist"]:
        folder_rel = entry.get("application_folder")
        files = {}
        if folder_rel:
            files = load_packet_files(os.path.join(applications_root, folder_rel))

        stage = compute_stage(entry, files)
        entries.append({
            "rank": entry["rank"],
            "company": entry["company"],
            "role": entry["role"],
            "location": entry["location"],
            "category": entry["category"],
            "apply_url": entry["apply_url"],
            "match_score": entry["match_score"],
            "why_it_fits": entry["why_it_fits"],
            "flags": entry["flags"],
            "application_status": entry.get("application_status", "not started"),
            "notes": entry.get("notes", ""),
            "linkedin_leads": entry.get("linkedin_leads", []),
            "has_packet": bool(folder_rel),
            "stage": stage,
            "stage_label": stage_label(stage),
            "files": files,
        })

    return {
        "generated_on": shortlist_data.get("generated_on"),
        "candidate_profile": shortlist_data.get("candidate_profile"),
        "total_open_roles_scanned": shortlist_data.get("total_open_roles_scanned") or shortlist_data.get("total_scanned"),
        "entries": entries,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--shortlist", required=True)
    p.add_argument("--applications-root", default=None,
                   help="Base dir application_folder paths are relative to (default: shortlist file's directory)")
    p.add_argument("--out", default="dashboard/data.json")
    args = p.parse_args()

    with open(args.shortlist, encoding="utf-8") as f:
        shortlist_data = json.load(f)

    applications_root = args.applications_root or os.path.dirname(os.path.abspath(args.shortlist))
    out = build(shortlist_data, applications_root)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {len(out['entries'])} entries to {args.out}")


if __name__ == "__main__":
    main()
