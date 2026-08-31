"""Fetch postings from a plain RSS/Atom job feed."""

import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests

from .common import Posting, strip_html


def _parse_pub_date(pub_date: str) -> str:
    """RSS uses RFC822 dates ("Wed, 02 Oct 2024 13:00:00 GMT"), Atom uses
    ISO 8601 - handle either and fall back to unknown rather than guessing."""
    if not pub_date:
        return ""
    try:
        return parsedate_to_datetime(pub_date).date().isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(pub_date.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return ""


def fetch(company_cfg: dict, global_cfg: dict | None = None) -> list[Posting]:
    feed_url = company_cfg["feed_url"]
    company_name = company_cfg["name"]

    resp = requests.get(feed_url, timeout=20)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)

    postings = []
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for item in items:
        title = _text(item, "title")
        link = _text(item, "link") or _attr(item, "link", "href")
        guid = _text(item, "guid") or link
        pub_date = _text(item, "pubDate") or _text(item, "{http://www.w3.org/2005/Atom}published")
        description = strip_html(_text(item, "description") or _text(item, "{http://www.w3.org/2005/Atom}summary") or "")

        postings.append(
            Posting(
                source="rss",
                external_id=guid or link or title,
                company=company_name,
                title=title.strip(),
                location="",
                url=link or "",
                posted_date=_parse_pub_date(pub_date),
                description=description,
            )
        )
    return postings


def _text(elem, tag):
    child = elem.find(tag)
    return child.text if child is not None and child.text else ""


def _attr(elem, tag, attr):
    child = elem.find(tag)
    return child.get(attr) if child is not None else ""
