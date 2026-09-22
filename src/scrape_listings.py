#!/usr/bin/env python3
"""
Scrape structured internship listings out of the two community-maintained
GitHub READMEs that track CS/SWE/DS/quant/hardware internships:

  - SimplifyJobs/Summer<YEAR>-Internships  (HTML <table> per category)
  - vanshb03/Summer<YEAR>-Internships       (Markdown pipe table)

Both repos get renamed every year - pass --year to point at a different cycle.

Usage:
    python3 scrape_listings.py --year 2027 --out all_internships.json
"""
import argparse
import json
import re
import sys
import urllib.request

TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; internship-hunt-toolkit/1.0)"}

SIMPLIFY_URL_TMPL = "https://raw.githubusercontent.com/SimplifyJobs/Summer{year}-Internships/dev/README.md"
VANSH_URL_TMPL = "https://raw.githubusercontent.com/vanshb03/Summer{year}-Internships/dev/README.md"


def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _clean_location(location_cell, multi_pattern):
    """Collapse a <details><summary>N locations</summary>a<br>b</details> cell,
    or its Markdown-table equivalent, into a single readable string."""
    multi_match = multi_pattern.search(location_cell)
    body = re.sub(r"<summary>.*?</summary>", "", location_cell, flags=re.DOTALL)
    body = re.sub(r"</?details>", "", body)
    body = body.replace("<br>", "; ").replace("<br/>", "; ").replace("</br>", "; ")
    body = re.sub(r"<[^>]+>", "", body).strip()
    if multi_match:
        body = f"{body} ({multi_match.group(1)})"
    return body


HTML_MULTI_LOCATION_RE = re.compile(r"<summary><strong>(\d+ locations)</strong></summary>")
PIPE_MULTI_LOCATION_RE = re.compile(r"<summary>\*\*(\d+ locations)\*\*</summary>")

_ROW_RE = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)
_CELL_RE = re.compile(r"<td>(.*?)</td>", re.DOTALL)
_LINK_RE = re.compile(r'href="([^"]+)"')
_HEADING_RE = re.compile(r"^##+.*Internship Roles.*$", re.MULTILINE)
_TABLE_RE = re.compile(r"<table>.*?</table>", re.DOTALL)


def parse_html_tables(text, source):
    """Parse SimplifyJobs-style READMEs: one <table> per category, each row
    Company | Role | Location | Application | Age, with a leading '↳' cell
    meaning 'same company as the row above'."""
    headings = [(m.start(), re.sub(r"<[^>]+>", "", m.group(0)).strip()) for m in _HEADING_RE.finditer(text)]
    table_positions = [(m.start(), m.group(0)) for m in _TABLE_RE.finditer(text)]

    def nearest_heading(pos):
        best = "Unknown"
        for hpos, htext in headings:
            if hpos < pos:
                best = htext
        return best

    results = []
    last_company = None
    for pos, table_html in table_positions:
        category = re.sub(r"^#+\s*", "", nearest_heading(pos))
        for row in _ROW_RE.findall(table_html):
            cells = _CELL_RE.findall(row)
            if len(cells) != 5:
                continue
            company_cell, role_cell, location_cell, app_cell, age_cell = cells

            company_text = re.sub(r"<[^>]+>", "", company_cell).strip()
            faang = "🔥" in company_cell
            if company_text in ("↳", ""):
                company = last_company
            else:
                company = company_text.replace("🔥", "").strip()
                last_company = company

            role_text = re.sub(r"<[^>]+>", "", role_cell).strip()
            role_clean = re.sub(r"[🔒🛂🇺🇸🎓]", "", role_text).strip()

            location = _clean_location(location_cell, HTML_MULTI_LOCATION_RE)

            links = _LINK_RE.findall(app_cell)
            apply_url = next((l for l in links if "simplify.jobs/p/" not in l and "utm_medium=company" not in l), None)
            if not apply_url and links:
                apply_url = links[0]

            results.append({
                "source": source,
                "category": category,
                "company": company,
                "role": role_clean,
                "location": location,
                "apply_url": apply_url,
                "age": re.sub(r"<[^>]+>", "", age_cell).strip(),
                "closed": "🔒" in role_cell,
                "no_sponsorship": "🛂" in role_cell,
                "us_citizen_required": "🇺🇸" in role_cell,
                "advanced_degree": "🎓" in role_cell,
                "faang_plus": faang,
            })
    return results


def parse_pipe_table(text, source):
    """Parse vanshb03-style READMEs: a single Markdown pipe table,
    Company | Role | Location | Application/Link | Date Posted."""
    results = []
    last_company = None
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| Company") and "Role" in stripped:
            in_table = True
            continue
        if in_table and re.match(r"^\|\s*-+\s*\|", stripped):
            continue
        if in_table and not stripped.startswith("|"):
            in_table = False
            continue
        if not in_table:
            continue

        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 5:
            continue
        company_cell, role_cell, location_cell, app_cell, age_cell = cells[:5]

        company_text = re.sub(r"<[^>]+>", "", company_cell).strip()
        if company_text in ("↳", ""):
            company = last_company
        else:
            company = company_text
            last_company = company

        role_clean = re.sub(r"[🔒🛂🇺🇸🎓]", "", role_cell).strip()
        location = _clean_location(location_cell, PIPE_MULTI_LOCATION_RE)
        links = _LINK_RE.findall(app_cell)

        results.append({
            "source": source,
            "category": "General",
            "company": company,
            "role": role_clean,
            "location": location,
            "apply_url": links[0] if links else None,
            "age": age_cell.strip(),
            "closed": "🔒" in role_cell,
            "no_sponsorship": "🛂" in role_cell,
            "us_citizen_required": "🇺🇸" in role_cell,
            "advanced_degree": "🎓" in role_cell,
            "faang_plus": False,
        })
    return results


def scrape(year):
    simplify_text = fetch_url(SIMPLIFY_URL_TMPL.format(year=year))
    vansh_text = fetch_url(VANSH_URL_TMPL.format(year=year))
    return parse_html_tables(simplify_text, "SimplifyJobs") + parse_pipe_table(vansh_text, "vanshb03")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--year", default="2027", help="Summer cycle year, e.g. 2027 (default: %(default)s)")
    p.add_argument("--out", default="all_internships.json", help="Output JSON path")
    args = p.parse_args()

    listings = scrape(args.year)
    open_count = sum(1 for r in listings if not r["closed"])
    print(f"Scraped {len(listings)} rows ({open_count} open) for Summer {args.year}", file=sys.stderr)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(listings, f, indent=2)
    print(f"Wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
