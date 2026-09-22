#!/usr/bin/env python3
"""
Fetch a structured job posting (title, company, location, full description,
and application questions where available) from a posting URL.

Tries, in order:
  1. Known ATS public APIs (Greenhouse, Lever, Ashby) - these return clean
     JSON including the full description and, for Greenhouse, the actual
     application form questions.
  2. schema.org JobPosting JSON-LD embedded in the page HTML - many ATS
     pages (including some Workday/iCIMS instances) server-render this for
     SEO even though the rest of the page is a JS app.
  3. Falls back to raw HTML with a note that it's likely a JS-rendered shell
     (this is expected for most Workday/iCIMS/Oracle Cloud postings - there
     is no reliable public API for those, so the caller should fall back to
     what's already known from the internship listing (title/company/location)
     plus general company research instead of the raw page).

Usage: python3 fetch_posting.py <url>
Prints JSON to stdout.
"""
import json
import re
import sys
import urllib.request

TIMEOUT = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; internship-hunt-toolkit/1.0)"}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def try_greenhouse(url):
    m = re.search(r"greenhouse\.io/([^/]+)/jobs/(\d+)", url)
    if not m:
        return None
    board, job_id = m.groups()
    api = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs/{job_id}?questions=true"
    try:
        data = json.loads(fetch(api))
    except Exception:
        return None
    return {
        "platform": "greenhouse",
        "title": data.get("title"),
        "location": (data.get("location") or {}).get("name"),
        "description_html": data.get("content"),
        "questions": [q.get("label") for q in data.get("questions", []) if q.get("label")],
        "absolute_url": data.get("absolute_url"),
    }


def try_lever(url):
    m = re.search(r"jobs\.lever\.co/([^/]+)/([a-f0-9-]+)", url)
    if not m:
        return None
    company, posting_id = m.groups()
    api = f"https://api.lever.co/v0/postings/{company}/{posting_id}"
    try:
        data = json.loads(fetch(api))
    except Exception:
        return None
    return {
        "platform": "lever",
        "title": data.get("text"),
        "location": (data.get("categories") or {}).get("location"),
        "description_html": data.get("descriptionPlain") or data.get("description"),
        "questions": [],
        "absolute_url": data.get("hostedUrl"),
    }


def try_ashby(url):
    m = re.search(r"jobs\.ashbyhq\.com/([^/]+)/([a-f0-9-]+)", url)
    if not m:
        return None
    company, posting_id = m.groups()
    api = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
    try:
        data = json.loads(fetch(api))
    except Exception:
        return None
    for job in data.get("jobs", []):
        if job.get("id") == posting_id or posting_id in (job.get("jobUrl") or ""):
            return {
                "platform": "ashby",
                "title": job.get("title"),
                "location": job.get("location"),
                "description_html": job.get("descriptionHtml") or job.get("descriptionPlain"),
                "questions": [],
                "absolute_url": job.get("jobUrl"),
            }
    return None


def extract_jsonld_jobposting(html, url):
    """Pure parsing step (no network I/O) - pulled out of try_jsonld so it's
    directly unit-testable against a fixed HTML string."""
    blocks = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL,
    )
    for block in blocks:
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        candidates = data if isinstance(data, list) else [data]
        for item in candidates:
            if isinstance(item, dict) and item.get("@type") == "JobPosting":
                loc = item.get("jobLocation")
                loc_str = None
                if isinstance(loc, dict):
                    addr = loc.get("address", {})
                    loc_str = ", ".join(
                        filter(None, [addr.get("addressLocality"), addr.get("addressRegion")])
                    )
                elif isinstance(loc, list):
                    loc_str = "; ".join(
                        ", ".join(filter(None, [
                            (l.get("address", {}) or {}).get("addressLocality"),
                            (l.get("address", {}) or {}).get("addressRegion"),
                        ]))
                        for l in loc if isinstance(l, dict)
                    )
                return {
                    "platform": "jsonld",
                    "title": item.get("title"),
                    "location": loc_str,
                    "description_html": item.get("description"),
                    "questions": [],
                    "absolute_url": url,
                }

    likely_spa = any(host in url for host in ["myworkdayjobs.com", "icims.com", "oraclecloud.com"])
    return {
        "platform": "unknown",
        "note": (
            "No structured data found. This is very likely a JS-rendered application "
            "(Workday/iCIMS/Oracle Cloud typically don't server-render content), so raw "
            "fetching won't get the job description or application questions. Fall back "
            "to the title/company/location already known from the listing plus general "
            "company research (WebSearch) instead of trying to scrape this page further."
            if likely_spa else
            "No JobPosting JSON-LD found on this page."
        ),
        "absolute_url": url,
    }


def try_jsonld(url):
    try:
        html = fetch(url)
    except Exception as e:
        return {"platform": "unknown", "error": f"fetch failed: {e}"}
    return extract_jsonld_jobposting(html, url)


def clean_html(html):
    if not html:
        return None
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<li>", "\n- ", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_posting(url):
    result = try_greenhouse(url) or try_lever(url) or try_ashby(url) or try_jsonld(url)
    if result and result.get("description_html"):
        result["description_text"] = clean_html(result["description_html"])
        del result["description_html"]
    return result


def main():
    if len(sys.argv) != 2:
        print("Usage: fetch_posting.py <url>", file=sys.stderr)
        sys.exit(1)
    print(json.dumps(fetch_posting(sys.argv[1]), indent=2))


if __name__ == "__main__":
    main()
