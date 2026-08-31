"""Fetch postings from a company's public Ashby job board.

Ashby exposes a free, no-auth-required JSON API per company:
  https://api.ashbyhq.com/posting-api/job-board/<board_id>
"""

import requests

from .common import Posting, strip_html

API_URL = "https://api.ashbyhq.com/posting-api/job-board/{board_id}"


def fetch(company_cfg: dict, global_cfg: dict | None = None) -> list[Posting]:
    board_id = company_cfg["board_id"]
    company_name = company_cfg["name"]

    resp = requests.get(API_URL.format(board_id=board_id), timeout=20)
    resp.raise_for_status()
    data = resp.json()

    postings = []
    for job in data.get("jobs", []):
        posted_date = (job.get("publishedAt") or "")[:10]
        postings.append(
            Posting(
                source="ashby",
                external_id=str(job.get("id", "")),
                company=company_name,
                title=job.get("title", "").strip(),
                location=job.get("location", "") or "",
                url=job.get("jobUrl", ""),
                posted_date=posted_date,
                description=strip_html(job.get("descriptionHtml", "")),
            )
        )
    return postings
