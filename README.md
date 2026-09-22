# internship-hunt-toolkit

The scripts and dashboard behind the `cs-internship-hunt` Claude Code skill, bundled as a standalone, testable toolkit. It scrapes current CS/SWE/DS internship postings from two community-maintained GitHub trackers, ranks them against a candidate profile, and serves a local dashboard to track application progress and packet files (posting, tailored resume, cover letter, likely application answers).

No third-party dependencies - everything runs on the Python 3 standard library.

## Layout

```
src/
  scrape_listings.py         Pull + parse SimplifyJobs and vanshb03 internship READMEs into JSON
  fetch_career_fair_events.py  Pull upcoming career-fair dates + named company campus visits from UVM's public events calendar
  rank_listings.py           Score/dedupe/rank scraped listings (+ career-fair signal) against a candidate profile
  fetch_posting.py           Pull a single job posting's real description (Greenhouse/Lever/Ashby APIs, or JSON-LD)
  build_dashboard_data.py    Combine a shortlist + application packet folders into dashboard/data.json
dashboard/
  index.html               Static dashboard frontend (reads dashboard/data.json, no build step)
data/
  profile.json              Example candidate profile - copy and edit this for yourself
tests/                      unittest suite - fixtures under tests/fixtures/, no network calls
docs/
  profile_schema.md         Full field reference for profile.json
Makefile                    scrape / rank / dashboard-data / serve / test targets
```

## Quickstart

```sh
# 1. Edit data/profile.json with your own languages, location, and constraints
#    (see docs/profile_schema.md for the full field reference)

# 2. One shot: scrape listings + fetch campus-visit signal + rank + build the
#    dashboard, all in the right order
make refresh

# 3. Serve the dashboard locally
make serve
# -> open http://127.0.0.1:8420
```

`refresh` is the target to reach for whenever anything might have changed - new postings appear on SimplifyJobs/vanshb03 daily, and new campus-visit events get added to UVM's calendar regularly. Re-run it (or point a cron/`/schedule` job at it) rather than manually chasing individual steps; the shortlist should never be older than its inputs.

Each `make` target is also a plain script you can run directly - see the Makefile for the exact `python3 src/...` invocations if you want to script around this yourself.

## Career-fair / campus-visit signal

`fetch_career_fair_events.py` hits UVM's public events calendar (`events.uvm.edu`, a Localist-hosted calendar with a real JSON API - no login) and pulls out two things:

- **Fair dates** - the big named fairs (Job & Internship Fair, Engineering & Tech Fair, Career Expo, ...). Dates only: the actual employer roster for these lives in Handshake behind a student/employer login, which this toolkit doesn't attempt to reach (same reasoning as the LinkedIn limitation below).
- **Named organization visits** - individual info-session/networking/"X at UVM" events that name a specific company or org directly on their public event page (e.g. "Network with Fidelity Investments", "GlobalFoundries at UVM"). These are real, immediately-usable leads.

`rank_listings.py --career-fair-events <file>` merges that in before scoring: a company already in the scraped listings gets boosted with a "confirmed on UVM campus" reason, and a company visiting campus with no scraped posting yet gets added to the shortlist as its own entry (category `Campus Recruiting Event`) so it doesn't get lost. "Other sources" beyond UVM's calendar (a specific target company's own campus-recruiting page, a different school's calendar) are a `WebSearch` job, not something this script tries to generalize to - see the `cs-internship-hunt` skill.

## Applying to specific roles

This toolkit produces the shortlist and the dashboard shell; the per-role work (fetching the real posting, tailoring a resume, drafting a cover letter, drafting likely application answers) is judgment-heavy and is handled by the **`cs-internship-hunt` Claude Code skill**, not a script - ask Claude (with that skill available) to "prep an application for <company>" and it will use `fetch_posting.py` from here, then write `posting.md`/`resume.md`/`cover_letter.md`/`answers.md` into an `applications/<Company>-<Role>/` folder. Point `build_dashboard_data.py --applications-root` at wherever those folders live.

The skill also runs a much deeper adversarial "hiring-manager council" review pass on top of this toolkit's coarse `match_score` - see `docs/profile_schema.md` for why that distinction matters.

## Testing

```sh
make test
# or directly:
python3 -m unittest discover -s tests -v
```

63 tests, all against fixture data in `tests/fixtures/` (or inline fixtures for the calendar API shape) - no network access required or attempted. Coverage: README table/pipe-table parsing (badges, multi-location cells, `↳` continuation rows), career-fair event classification (including the false-positive cases it deliberately rejects), the ranking/scoring/dedup/per-company-cap/campus-visit-merge logic, JSON-LD job-posting extraction, and dashboard stage computation.

## Known limitations

- **No browser automation.** Nothing here can click into a Workday/Greenhouse/iCIMS application form and submit it - `fetch_posting.py` gets what's available via public APIs or embedded JSON-LD, which most enterprise ATS platforms (Workday, iCIMS, Oracle Cloud) don't expose. The output is a copy-paste-ready packet, not a submitted application.
- **No LinkedIn scraping.** LinkedIn blocks it and this toolkit doesn't attempt it. Finding contacts is a `WebSearch`-based, publicly-indexed-only lookup handled by the skill, not this codebase.
- **No Handshake scraping.** Same reasoning - the actual employer roster for UVM's big fairs is login-gated. `fetch_career_fair_events.py` only surfaces what UVM's calendar makes genuinely public.
- **`match_score` is a coarse filter, not a verdict.** See `docs/profile_schema.md`.
