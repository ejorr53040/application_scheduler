# internship-hunt-toolkit

The scripts and dashboard behind the `cs-internship-hunt` Claude Code skill, bundled as a standalone, testable toolkit. It scrapes current CS/SWE/DS internship postings from two community-maintained GitHub trackers, ranks them against a candidate profile, and serves a local dashboard to track application progress and packet files (posting, tailored resume, cover letter, likely application answers).

No third-party dependencies - everything runs on the Python 3 standard library.

## Layout

```
src/
  scrape_listings.py       Pull + parse SimplifyJobs and vanshb03 internship READMEs into JSON
  rank_listings.py         Score/dedupe/rank scraped listings against a candidate profile
  fetch_posting.py         Pull a single job posting's real description (Greenhouse/Lever/Ashby APIs, or JSON-LD)
  build_dashboard_data.py  Combine a shortlist + application packet folders into dashboard/data.json
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

# 2. Scrape the current cycle's listings (defaults to Summer 2027 - the repos
#    rename themselves every year, pass YEAR= for a different cycle)
make scrape YEAR=2027

# 3. Rank them against your profile
make rank

# 4. Build the dashboard data and serve it locally
make serve
# -> open http://127.0.0.1:8420
```

Each `make` target is also a plain script you can run directly - see the Makefile for the exact `python3 src/...` invocations if you want to script around this yourself.

## Applying to specific roles

This toolkit produces the shortlist and the dashboard shell; the per-role work (fetching the real posting, tailoring a resume, drafting a cover letter, drafting likely application answers) is judgment-heavy and is handled by the **`cs-internship-hunt` Claude Code skill**, not a script - ask Claude (with that skill available) to "prep an application for <company>" and it will use `fetch_posting.py` from here, then write `posting.md`/`resume.md`/`cover_letter.md`/`answers.md` into an `applications/<Company>-<Role>/` folder. Point `build_dashboard_data.py --applications-root` at wherever those folders live.

The skill also runs a much deeper adversarial "hiring-manager council" review pass on top of this toolkit's coarse `match_score` - see `docs/profile_schema.md` for why that distinction matters.

## Testing

```sh
make test
# or directly:
python3 -m unittest discover -s tests -v
```

46 tests, all against fixture data in `tests/fixtures/` - no network access required or attempted. Coverage: README table/pipe-table parsing (badges, multi-location cells, `↳` continuation rows), the ranking/scoring/dedup/per-company-cap logic, JSON-LD job-posting extraction, and dashboard stage computation.

## Known limitations

- **No browser automation.** Nothing here can click into a Workday/Greenhouse/iCIMS application form and submit it - `fetch_posting.py` gets what's available via public APIs or embedded JSON-LD, which most enterprise ATS platforms (Workday, iCIMS, Oracle Cloud) don't expose. The output is a copy-paste-ready packet, not a submitted application.
- **No LinkedIn scraping.** LinkedIn blocks it and this toolkit doesn't attempt it. Finding contacts is a `WebSearch`-based, publicly-indexed-only lookup handled by the skill, not this codebase.
- **`match_score` is a coarse filter, not a verdict.** See `docs/profile_schema.md`.
