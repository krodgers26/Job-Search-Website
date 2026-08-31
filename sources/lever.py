"""Fetch postings from a company's public Lever job board.

Lever exposes a free, no-auth-required JSON API per company:
  https://api.lever.co/v0/postings/<board_id>?mode=json
"""

import requests

from .common import Posting, strip_html

API_URL = "https://api.lever.co/v0/postings/{board_id}"


def fetch(company_cfg: dict, global_cfg: dict | None = None) -> list[Posting]:
    board_id = company_cfg["board_id"]
    company_name = company_cfg["name"]

    resp = requests.get(
        API_URL.format(board_id=board_id),
        params={"mode": "json"},
        timeout=20,
    )
    resp.raise_for_status()
    jobs = resp.json()

    postings = []
    for job in jobs:
        categories = job.get("categories", {}) or {}
        location = categories.get("location", "") or ""
        posted_ms = job.get("createdAt")
        posted_date = ""
        if posted_ms:
            from datetime import datetime, timezone

            posted_date = datetime.fromtimestamp(posted_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

        description_parts = [job.get("descriptionPlain", "") or strip_html(job.get("description", ""))]
        for list_block in job.get("lists", []) or []:
            description_parts.append(strip_html(list_block.get("content", "")))

        postings.append(
            Posting(
                source="lever",
                external_id=str(job.get("id", "")),
                company=company_name,
                title=job.get("text", "").strip(),
                location=location.strip(),
                url=job.get("hostedUrl", ""),
                posted_date=posted_date,
                description=" ".join(p for p in description_parts if p),
            )
        )
    return postings
