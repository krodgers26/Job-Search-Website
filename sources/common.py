"""Shared data shape that every source module normalizes into."""

from dataclasses import dataclass
import re


@dataclass
class Posting:
    source: str          # "greenhouse", "lever", "ashby", "workday", "rss"
    external_id: str      # ID from the source system, unique within that source
    company: str
    title: str
    location: str
    url: str
    posted_date: str      # ISO date string "YYYY-MM-DD", or "" if unknown
    description: str      # plain text, HTML stripped

    @property
    def dedupe_key(self) -> str:
        return f"{self.source}:{self.external_id}"


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def strip_html(html: str) -> str:
    """Turn a chunk of job-description HTML into plain, whitespace-collapsed text."""
    if not html:
        return ""
    text = _TAG_RE.sub(" ", html)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    return _WS_RE.sub(" ", text).strip()
