"""Fetch postings from a company's public Greenhouse job board.

Greenhouse exposes a free, no-auth-required JSON API per company:
  https://boards-api.greenhouse.io/v1/boards/<board_id>/jobs?content=true
"""

import requests

from .common import Posting, strip_html

API_URL = "https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs"


def fetch(company_cfg: dict, global_cfg: dict | None = None) -> list[Posting]:
    board_id = company_cfg["board_id"]
    company_name = company_cfg["name"]

    resp = requests.get(
        API_URL.format(board_id=board_id),
        params={"content": "true"},
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()

    postings = []
    for job in data.get("jobs", []):
        location = (job.get("location") or {}).get("name", "") or ""
        posted_date = (job.get("updated_at") or "")[:10]  # "YYYY-MM-DD..."
        postings.append(
            Posting(
                source="greenhouse",
                external_id=str(job["id"]),
                company=company_name,
                title=job.get("title", "").strip(),
                location=location.strip(),
                url=job.get("absolute_url", ""),
                posted_date=posted_date,
                description=strip_html(job.get("content", "")),
            )
        )
    return postings
