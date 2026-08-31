"""Fetch postings from a plain RSS/Atom job feed."""

import xml.etree.ElementTree as ET

import requests

from .common import Posting, strip_html


def fetch(company_cfg: dict) -> list[Posting]:
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
                posted_date=(pub_date or "")[:10],
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
