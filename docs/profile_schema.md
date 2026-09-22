# Candidate profile schema

`rank_listings.py` scores listings against a profile JSON file. All fields are optional except that an empty profile (`{}`) just falls back to generic tech-role defaults.

| Field | Type | Meaning |
|---|---|---|
| `languages` | list[str] | Languages/frameworks to look for in role titles (lowercase). A hit adds +2 and is reported in `why_it_fits`. |
| `domain_keywords` | list[str] | Role-type keywords (e.g. `"backend"`, `"graphics"`) that indicate a domain match. Falls back to a generic SWE keyword list if omitted. |
| `ai_ml_keywords` | list[str] | Keywords marking an AI/ML-adjacent role. Falls back to a generic list if omitted. |
| `home_state_codes` | list[str] | Two-letter state codes treated as "close to home" (small score boost). |
| `home_city_hint` | str | Lowercase city/state string (e.g. `"burlington, vt"`) - an exact substring match in the location gets a bigger boost than the state-level one. |
| `exclude_categories` | list[str] | Category names (substring match) to penalize - e.g. `["Product Management"]` if you're only interested in engineering roles. |
| `exclude_advanced_degree` | bool | Default `true`. Excludes roles flagged as requiring a Master's/PhD (the 🎓 badge). Set `false` if you are a grad student. |
| `needs_sponsorship` | bool or `null` | Set `true` if you will need visa sponsorship now or in the future. Any role flagged "no sponsorship" is then hard-excluded. Leave `null`/omit to not filter on this. |
| `is_us_citizen` | bool or `null` | Set `true` if you are NOT a US citizen and the role requires one, to hard-exclude 🇺🇸-flagged roles. Leave `null`/omit to not filter on this. |
| `max_per_company` | int | Cap on how many roles from the same company appear in the final shortlist (default 2), so one company with many postings doesn't crowd out variety. |

## Why this exists

The scoring in `score_entry()` is a **coarse pre-filter**, meant to cut ~2,000 raw listings down to a manageable candidate set cheaply. It is not the final word on fit - the `cs-internship-hunt` Claude Code skill runs a much more rigorous "hiring-manager council" adversarial review (see that skill's `SKILL.md`, Step 4) on whatever survives this filter, which is where hard-to-encode judgment calls (does the resume's evidence actually support this specific posting, are there eligibility landmines buried in the real posting text, etc.) happen. Don't expect `match_score` alone to be a trustworthy final ranking - treat it as "worth a closer look," not "apply here first."
