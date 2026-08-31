"""Fetch postings from a company's public Workday career site.

Workday's candidate-facing job search runs on a JSON endpoint (the "CXS" API)
that the career site's own page calls to render its results, and it doesn't
require authentication for public postings:
  https://<tenant>.<wd_host>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs

We page through it with a POST body of {"limit", "offset"} until a page
comes back empty. That list endpoint only gives a relative posted-date
string ("Posted 3 Days Ago") and no salary/description text, so for postings
that survive a cheap pre-filter we also hit each job's own detail page to
get its full description (salary, if disclosed, lives in there). The detail
endpoint's shape isn't publicly documented and this hasn't been verified
against a live Workday tenant, so it's wrapped defensively: if it fails or
doesn't match what's expected, that one posting just ends up with no salary
data rather than breaking the whole run.
"""

import re
from datetime import date, timedelta

import requests

from .common import Posting, strip_html

PAGE_SIZE = 20
# Safety cap so a huge employer-wide board (e.g. a company with thousands of
# openings across every department) can't turn one refresh into hundreds of
# requests. Use "search_text" in config.yaml to narrow those boards instead.
MAX_PAGES = 25
# Cap on how many job detail pages we'll fetch per company, spent only on
# postings that survive the cheap pre-filter below.
MAX_DETAIL_FETCHES = 50

_DAYS_AGO_RE = re.compile(r"posted\s+(\d+)\+?\s+days?\s+ago", re.IGNORECASE)


def _parse_relative_posted_date(text: str) -> str:
    """Turn Workday's relative posted-date text into an actual ISO date."""
    if not text:
        return ""
    text_lower = text.lower()
    if "today" in text_lower:
        return date.today().isoformat()
    if "yesterday" in text_lower:
        return (date.today() - timedelta(days=1)).isoformat()
    match = _DAYS_AGO_RE.search(text_lower)
    if match:
        return (date.today() - timedelta(days=int(match.group(1)))).isoformat()
    return ""


def _quick_exclude(title: str, location: str, global_cfg: dict) -> bool:
    """Cheap pre-filter using only what the list endpoint gives us, so we
    don't spend a detail-page request on a posting that's going to be
    excluded anyway once fully scored."""
    title_lower = title.lower()
    for term in global_cfg.get("exclude_title_terms", []):
        if term.lower() in title_lower:
            return True
    for term in global_cfg.get("seniority", {}).get("exclude_terms", []):
        if term.lower() in title_lower:
            return True

    location_cfg = global_cfg.get("location", {})
    if location_cfg.get("exclude_if_no_location_match", False):
        location_lower = location.lower()
        target_terms = [t.lower() for t in location_cfg.get("target_location_terms", [])]
        remote_terms = [t.lower() for t in location_cfg.get("remote_terms", [])]
        if not any(t in location_lower for t in target_terms) and not any(
            t in location_lower for t in remote_terms
        ):
            return True
    return False


def _fetch_detail_description(tenant: str, wd_host: str, site: str, external_path: str) -> str:
    url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{external_path}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    info = resp.json().get("jobPostingInfo", {})
    return strip_html(info.get("jobDescription", ""))


def fetch(company_cfg: dict, global_cfg: dict | None = None) -> list[Posting]:
    global_cfg = global_cfg or {}
    tenant = company_cfg["tenant"]
    wd_host = company_cfg["wd_host"]
    site = company_cfg["site"]
    company_name = company_cfg["name"]
    search_text = company_cfg.get("search_text", "")

    base_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    careers_base = f"https://{tenant}.{wd_host}.myworkdayjobs.com/{site}"

    postings = []
    paths = []
    offset = 0
    for _ in range(MAX_PAGES):
        resp = requests.post(
            base_url,
            json={"limit": PAGE_SIZE, "offset": offset, "searchText": search_text},
            headers={"Content-Type": "application/json"},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobPostings", [])
        if not jobs:
            break

        for job in jobs:
            path = job.get("externalPath", "")
            postings.append(
                Posting(
                    source="workday",
                    external_id=f"{tenant}:{path}",
                    company=company_name,
                    title=job.get("title", "").strip(),
                    location=job.get("locationsText", "") or job.get("location", "") or "",
                    url=careers_base + path,
                    posted_date=_parse_relative_posted_date(job.get("postedOn", "")),
                    description="",
                )
            )
            paths.append(path)

        total = data.get("total", 0)
        offset += PAGE_SIZE
        if offset >= total:
            break

    # Best-effort enrichment: fetch full description (for salary parsing)
    # for postings that would survive the cheap filters, up to the cap.
    detail_budget = MAX_DETAIL_FETCHES
    for posting, path in zip(postings, paths):
        if detail_budget <= 0:
            break
        if _quick_exclude(posting.title, posting.location, global_cfg):
            continue
        detail_budget -= 1
        try:
            description = _fetch_detail_description(tenant, wd_host, site, path)
            if description:
                posting.description = description
        except Exception:
            pass  # leave this posting without a description; it still shows up, just with no salary data

    return postings
