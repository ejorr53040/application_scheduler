#!/usr/bin/env python3
"""
Rank scraped internship listings (from scrape_listings.py) against a
candidate profile, dedupe, and produce a final shortlist.

Usage:
    python3 rank_listings.py --listings all_internships.json \\
        --profile profile.json --out shortlist.json --top 50

profile.json shape (see ../docs/profile_schema.md for full details):
{
  "languages": ["Python", "Java", "C++", ...],
  "domain_keywords": ["backend", "machine learning", ...],
  "home_state_codes": ["VT", "NH", "MA"],
  "home_city_hint": "burlington, vt",
  "exclude_categories": ["Quantitative Finance", "Product Management"],
  "exclude_advanced_degree": true,
  "max_per_company": 2
}
"""
import argparse
import json
import re
import sys
from collections import defaultdict

DEFAULT_GOOD_DOMAIN = [
    "backend", "back-end", "back end", "full stack", "full-stack", "fullstack",
    "software engineer", "software engineering", "software development",
    "platform", "infrastructure", "systems", "distributed", "database",
    "graphics", "game", "engine", "compiler", "devtools", "developer tools",
    "cloud", "api", "web", "server", "site reliability", "sre",
]
DEFAULT_AI_ML = [
    "machine learning", " ml ", "ml intern", "artificial intelligence", " ai ",
    "ai/ml", "data science", "llm", "model",
]


def score_entry(row, profile):
    """Return (score, reasons[]) for one listing against a candidate profile.
    This is a coarse pre-filter, not a verdict - see the toolkit's cs-internship-hunt
    skill for the deeper "hiring-manager council" review pass meant to run on
    whatever survives this filter."""
    s = 0.0
    reasons = []
    role_l = (row.get("role") or "").lower()
    loc_l = (row.get("location") or "").lower()
    cat = row.get("category", "")

    domain_kw = profile.get("domain_keywords") or DEFAULT_GOOD_DOMAIN
    for kw in domain_kw:
        if kw.lower() in role_l:
            s += 2
            reasons.append(f"role matches '{kw.strip()}'")
            break

    languages = [l.lower() for l in profile.get("languages", [])]
    # Word-boundary match, not substring - a naive "in" check makes a
    # single-letter language like "c" match inside "Engineer" or "Science"
    # and every role scores an irrelevant "language" hit.
    lang_hits = [l for l in languages if re.search(r"(?<![a-z0-9+#])" + re.escape(l) + r"(?![a-z0-9+#])", role_l)]
    if lang_hits:
        s += 2
        reasons.append(f"posting calls out {', '.join(lang_hits)}, which is on the resume")

    ai_kw = profile.get("ai_ml_keywords") or DEFAULT_AI_ML
    if any(kw.lower() in role_l for kw in ai_kw):
        s += 1.5
        reasons.append("AI/ML-adjacent role")

    exclude_categories = profile.get("exclude_categories", [])
    if any(c.lower() in cat.lower() for c in exclude_categories):
        s -= 1.5
    elif "software engineering" in cat.lower():
        s += 1.5
    elif "data science" in cat.lower():
        s += 1.0

    if profile.get("exclude_advanced_degree", True) and row.get("advanced_degree"):
        s -= 100
    if row.get("closed"):
        s -= 100

    home_city_hint = (profile.get("home_city_hint") or "").lower()
    if home_city_hint and home_city_hint in loc_l:
        s += 4
        reasons.append(f"matches home location ({profile['home_city_hint']})")
    else:
        home_states = profile.get("home_state_codes", [])
        if any(f", {st}".lower() in loc_l for st in home_states):
            s += 1.5
            reasons.append("in candidate's home region")
    if "remote" in loc_l:
        s += 1
        reasons.append("remote-eligible")

    for sponsor_flag, needed in (("no_sponsorship", "needs_sponsorship"), ("us_citizen_required", "is_us_citizen")):
        if row.get(sponsor_flag) and profile.get(needed) is True:
            s -= 100
            reasons = [f"EXCLUDED: {sponsor_flag} conflicts with candidate's stated status"]

    for reason in row.get("_campus_visit_reasons", []):
        s += 3
        reasons.append(reason)

    return s, reasons


def _names_match(a_l, b_l):
    """Word-boundary containment, not raw substring - otherwise e.g. company
    "Tive" false-matches inside organization "Marsh Captive Solutions"."""
    return bool(
        re.search(r"\b" + re.escape(a_l) + r"\b", b_l)
        or re.search(r"\b" + re.escape(b_l) + r"\b", a_l)
    )


def apply_career_fair_signal(rows, fair_data):
    """Merge career-fair/campus-visit signal (from fetch_career_fair_events.py)
    into the listing set before scoring: boost companies that already have a
    scraped posting, and synthesize a placeholder entry for organizations
    confirmed to be visiting campus that don't have one yet - so "this company
    is recruiting on your campus right now" surfaces as its own lead even when
    no specific role posting was found for it."""
    rows = [dict(r) for r in rows]
    visits = fair_data.get("organization_visits", [])

    for visit in visits:
        org = visit.get("organization")
        if not org:
            continue
        org_l = org.lower()
        reason = f'confirmed on UVM campus: "{visit["title"]}" ({visit["date"]})'

        matched = False
        for r in rows:
            company_l = (r.get("company") or "").lower()
            if _names_match(org_l, company_l):
                r.setdefault("_campus_visit_reasons", []).append(reason)
                matched = True

        if not matched:
            rows.append({
                "source": "UVM Career Center calendar",
                "category": "Campus Recruiting Event",
                "company": org,
                "role": "(No specific posting found yet - confirmed recruiting/visiting at UVM; check their careers page directly)",
                "location": "Burlington, VT (UVM campus event)",
                "apply_url": visit.get("url"),
                "age": visit.get("date"),
                "closed": False,
                "no_sponsorship": False,
                "us_citizen_required": False,
                "advanced_degree": False,
                "faang_plus": False,
                "_campus_visit_reasons": [reason],
            })

    return rows


def dedupe(rows):
    seen = {}
    for r in rows:
        key = (
            (r.get("company") or "").strip().lower(),
            (r.get("role") or "").strip().lower(),
            (r.get("location") or "").strip().lower(),
        )
        if key not in seen:
            seen[key] = r
    return list(seen.values())


def collapse_multi_location_dupes(rows):
    """When the same (company, role) appears more than once (e.g. a listing
    updated to add a location), keep only the entry with the richest location
    string rather than showing near-identical duplicates."""
    by_cr = {}
    for r in rows:
        key = (r["company"].lower(), r["role"].lower())
        if key not in by_cr or len(r.get("location") or "") > len(by_cr[key].get("location") or ""):
            by_cr[key] = r
    return list(by_cr.values())


def build_shortlist(listings, profile, top_n=50):
    deduped = dedupe(listings)

    scored = []
    for r in deduped:
        sc, reasons = score_entry(r, profile)
        if sc <= -50:
            continue
        r = dict(r)
        r["_score"] = sc
        r["_reasons"] = reasons
        scored.append(r)

    scored.sort(key=lambda r: r["_score"], reverse=True)
    scored = collapse_multi_location_dupes(scored)
    scored.sort(key=lambda r: r["_score"], reverse=True)

    max_per_company = profile.get("max_per_company", 2)
    per_company_count = defaultdict(int)
    final = []
    for r in scored:
        c = r["company"].lower()
        if per_company_count[c] >= max_per_company:
            continue
        per_company_count[c] += 1
        final.append(r)
        if len(final) >= top_n:
            break

    out = []
    for i, r in enumerate(final, 1):
        why = "; ".join(r["_reasons"]) if r["_reasons"] else "general fit with candidate profile"
        out.append({
            "rank": i,
            "company": r["company"],
            "role": r["role"],
            "location": r["location"],
            "category": r["category"],
            "apply_url": r["apply_url"],
            "posted_age": r.get("age"),
            "flags": {
                "no_sponsorship": r["no_sponsorship"],
                "us_citizen_required": r["us_citizen_required"],
                "faang_plus": r["faang_plus"],
            },
            "match_score": round(r["_score"], 1),
            "why_it_fits": why,
            "source": r["source"],
            "application_status": "not started",
            "notes": "",
        })
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--listings", required=True, help="Path to scrape_listings.py output")
    p.add_argument("--profile", required=True, help="Path to candidate profile JSON")
    p.add_argument("--out", default="shortlist.json")
    p.add_argument("--top", type=int, default=50)
    p.add_argument("--career-fair-events", default=None,
                   help="Path to fetch_career_fair_events.py output - merges campus-visit signal in before ranking")
    args = p.parse_args()

    with open(args.listings, encoding="utf-8") as f:
        listings = json.load(f)
    with open(args.profile, encoding="utf-8") as f:
        profile = json.load(f)

    if args.career_fair_events:
        try:
            with open(args.career_fair_events, encoding="utf-8") as f:
                fair_data = json.load(f)
        except FileNotFoundError:
            print(
                f"Note: {args.career_fair_events} not found - ranking without campus-visit signal "
                f"(run fetch_career_fair_events.py first to include it)",
                file=sys.stderr,
            )
            fair_data = None
        if fair_data:
            listings = apply_career_fair_signal(listings, fair_data)

    shortlist = build_shortlist(listings, profile, top_n=args.top)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({
            "total_scanned": len(listings),
            "shortlist": shortlist,
        }, f, indent=2)
    print(f"Wrote {len(shortlist)} ranked entries to {args.out}")


if __name__ == "__main__":
    main()
