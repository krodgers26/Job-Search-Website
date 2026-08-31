"""Fetch postings from a company's public Workday career site.

Workday's candidate-facing job search runs on a JSON endpoint (the "CXS" API)
that the career site's own page calls to render its results, and it doesn't
require authentication for public postings:
  https://<tenant>.<wd_host>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs

We page through it with a POST body of {"limit", "offset"} until a page
comes back empty.
"""

import requests

from .common import Posting

PAGE_SIZE = 20
# Safety cap so a huge employer-wide board (e.g. a company with thousands of
# openings across every department) can't turn one refresh into hundreds of
# requests. Use "search_text" in config.yaml to narrow those boards instead.
MAX_PAGES = 25


def fetch(company_cfg: dict) -> list[Posting]:
    tenant = company_cfg["tenant"]
    wd_host = company_cfg["wd_host"]
    site = company_cfg["site"]
    company_name = company_cfg["name"]
    search_text = company_cfg.get("search_text", "")

    base_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    careers_base = f"https://{tenant}.{wd_host}.myworkdayjobs.com/{site}"

    postings = []
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
                    posted_date="",  # Workday only gives a relative "posted X days ago" string
                    description=job.get("postedOn", ""),
                )
            )

        total = data.get("total", 0)
        offset += PAGE_SIZE
        if offset >= total:
            break

    return postings
