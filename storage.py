"""SQLite-backed history of every posting ever seen, so refreshes can tell
what's new and you keep a record of everything that's been surfaced."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from sources.common import Posting

SCHEMA = """
CREATE TABLE IF NOT EXISTS postings (
    dedupe_key   TEXT PRIMARY KEY,
    source       TEXT NOT NULL,
    company      TEXT NOT NULL,
    title        TEXT NOT NULL,
    location     TEXT,
    url          TEXT,
    posted_date  TEXT,
    description  TEXT,
    score        INTEGER,
    excluded     INTEGER NOT NULL DEFAULT 0,
    exclude_reason TEXT,
    first_seen   TEXT NOT NULL,
    last_seen    TEXT NOT NULL
);
"""


@contextmanager
def connect(db_path: str):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert(conn, posting: Posting, score: int, excluded: bool, exclude_reason: str) -> bool:
    """Insert or update a posting. Returns True if this is a brand-new posting
    (never seen in a previous refresh)."""
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute(
        "SELECT dedupe_key FROM postings WHERE dedupe_key = ?", (posting.dedupe_key,)
    ).fetchone()
    is_new = existing is None

    if is_new:
        conn.execute(
            """
            INSERT INTO postings
                (dedupe_key, source, company, title, location, url, posted_date,
                 description, score, excluded, exclude_reason, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                posting.dedupe_key, posting.source, posting.company, posting.title,
                posting.location, posting.url, posting.posted_date, posting.description,
                score, int(excluded), exclude_reason, now, now,
            ),
        )
    else:
        conn.execute(
            """
            UPDATE postings
            SET title = ?, location = ?, url = ?, posted_date = ?, description = ?,
                score = ?, excluded = ?, exclude_reason = ?, last_seen = ?
            WHERE dedupe_key = ?
            """,
            (
                posting.title, posting.location, posting.url, posting.posted_date,
                posting.description, score, int(excluded), exclude_reason, now,
                posting.dedupe_key,
            ),
        )
    return is_new
