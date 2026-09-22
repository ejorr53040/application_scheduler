#!/usr/bin/env python3
"""
Pull upcoming career-fair and campus-recruiting signal from UVM's public
events calendar (events.uvm.edu, a Localist-hosted calendar with a public
JSON API - no login required).

This deliberately does NOT try to reach the actual employer rosters for the
big multi-employer fairs (Job & Internship Fair, Engineering & Tech Fair,
Career Expo, etc.) - those live in Handshake behind a student/employer login,
same as noted elsewhere in this toolkit for LinkedIn. What IS public: the
fair dates themselves, and - more usefully - individual info-session/
networking/"X at UVM" events that name a specific company or organization
directly on their public event page.

Two kinds of signal come out:
  - "fairs": the big named fairs - dates only, so the user knows to check
    Handshake around that date rather than relying on this script for the roster.
  - "organization_visits": individual events that name a specific company/org -
    these are usable leads right now, and get merged into the ranked
    shortlist by rank_listings.py (--career-fair-events).

Usage:
    python3 fetch_career_fair_events.py --days 180 --out career_fair_events.json
"""
import argparse
import json
import re
import sys
import urllib.request

API = "https://events.uvm.edu/api/2/events"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; internship-hunt-toolkit/1.0)"}
MAX_PAGES = 20

FAIR_KEYWORDS = ["career fair", "job fair", "internship fair", "career expo", "jobs fair"]

CAREER_TOPIC = "Career Readiness and Professional Development"

# Order matters - more specific patterns first. Each must capture the
# organization name in group(1). "trusted" patterns (network/connect with X)
# are strong signals on their own; the rest are common phrasings that also
# show up for plenty of non-employer campus content (admissions info
# sessions, internal workshops, etc.), so those additionally require the
# calendar's own "Career Readiness and Professional Development" topic tag
# before being trusted - see classify().
TRUSTED_ORG_PATTERNS = [
    re.compile(r"^(?:network(?:ing)?|connect)\s+with\s+(.+?)(?:\s*[:\-–].*)?$", re.IGNORECASE),
]
CONDITIONAL_ORG_PATTERNS = [
    re.compile(r"^(.+?)\s+(?:info(?:rmation)?\s+session)\b", re.IGNORECASE),
    re.compile(r"^(.+?)\s+at\s+UVM\b", re.IGNORECASE),
    re.compile(r"^(.+?)\s+recruit(?:ing|ment)?\b", re.IGNORECASE),
]


def fetch_page(days, page):
    url = f"{API}?days={days}&pp=100&page={page}"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _try_patterns(patterns, title):
    for pat in patterns:
        m = pat.match(title)
        if m:
            org = m.group(1).strip(" :-–")
            if org:
                return org
    return None


def extract_org(title, has_career_topic=False):
    """Pure function - try the always-trusted patterns first, then the
    conditional ones (only trusted when has_career_topic is True, since those
    phrasings alone false-positive on plenty of non-employer campus content -
    admissions info sessions, internal faculty workshops, etc.)."""
    title = title.strip()
    org = _try_patterns(TRUSTED_ORG_PATTERNS, title)
    if org:
        return org
    if has_career_topic:
        return _try_patterns(CONDITIONAL_ORG_PATTERNS, title)
    return None


def classify(event):
    """Pure function - decide if a raw Localist event is fair/org-visit signal,
    and return a normalized record, or None if it's irrelevant (the vast
    majority of a university's event calendar isn't career-related at all)."""
    title = (event.get("title") or "").strip()
    if not title:
        return None
    title_l = title.lower()
    types = [t["name"] for t in event.get("filters", {}).get("event_types", [])]
    topics = [t["name"] for t in event.get("filters", {}).get("event_topics", [])]
    has_career_topic = CAREER_TOPIC in topics

    is_fair = any(kw in title_l for kw in FAIR_KEYWORDS) or "Career fairs" in types
    org = extract_org(title, has_career_topic=has_career_topic)
    is_org_visit = org is not None or (
        has_career_topic and any(t in types for t in ("Info sessions and tabling", "Networking"))
    )
    if not is_fair and not is_org_visit:
        return None

    return {
        "date": event.get("first_date"),
        "title": title,
        "url": event.get("localist_url"),
        "event_types": types,
        "is_fair": is_fair,
        "is_org_visit": is_org_visit,
        "organization": org,
    }


def fetch_all(days):
    seen_keys = set()
    results = []
    page = 1
    while page <= MAX_PAGES:
        data = fetch_page(days, page)
        for e in data.get("events", []):
            classified = classify(e["event"])
            if not classified:
                continue
            key = (classified["title"], classified["date"])
            if key in seen_keys:
                continue
            seen_keys.add(key)
            results.append(classified)

        page_info = data.get("page", {})
        next_page = page_info.get("next_page")
        if not next_page or next_page <= page:
            break
        page = next_page
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--days", type=int, default=180, help="How many days ahead to scan (default: %(default)s)")
    p.add_argument("--out", default="career_fair_events.json")
    args = p.parse_args()

    events = fetch_all(args.days)
    fairs = [e for e in events if e["is_fair"]]
    visits = [e for e in events if e["is_org_visit"] and e["organization"]]
    print(
        f"Found {len(fairs)} fair dates and {len(visits)} named organization visits "
        f"over the next {args.days} days",
        file=sys.stderr,
    )

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"fairs": fairs, "organization_visits": visits}, f, indent=2)
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
