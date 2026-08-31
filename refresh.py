#!/usr/bin/env python3
"""The one command: `python refresh.py`

Fetches every company's postings, dedupes/scores them against config.yaml,
saves everything to the local SQLite history, and writes a fresh HTML
(and optionally CSV) report sorted by relevance.
"""

import sys

import yaml

import report
import storage
from scorer import score_posting
from sources import ashby, greenhouse, lever, rss, workday


def _fmt_k(n: int) -> str:
    return f"${n / 1000:.0f}K"


def format_salary(salary_min, salary_max) -> str:
    if salary_min is None or salary_max is None:
        return "Not listed"
    if salary_min == salary_max:
        return _fmt_k(salary_min)
    return f"{_fmt_k(salary_min)}–{_fmt_k(salary_max)}"


FETCHERS = {
    "greenhouse": greenhouse.fetch,
    "lever": lever.fetch,
    "ashby": ashby.fetch,
    "workday": workday.fetch,
    "rss": rss.fetch,
}


def load_config(path: str = "config.yaml") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    cfg = load_config()

    all_postings = []
    for company_cfg in cfg.get("companies", []):
        platform = company_cfg.get("platform")
        fetcher = FETCHERS.get(platform)
        name = company_cfg.get("name", "?")
        if fetcher is None:
            print(f"  [skip] {name}: platform '{platform}' not supported yet", file=sys.stderr)
            continue
        try:
            postings = fetcher(company_cfg, cfg)
        except Exception as exc:  # noqa: BLE001 - one bad company shouldn't kill the whole run
            print(f"  [error] {name}: {exc}", file=sys.stderr)
            continue
        print(f"  [ok] {name}: {len(postings)} postings fetched")
        all_postings.extend(postings)

    db_path = cfg.get("database", {}).get("path", "output/jobs.db")
    min_score = cfg.get("output", {}).get("min_score_to_show", 0)

    rows = []
    new_count = 0
    excluded_count = 0

    with storage.connect(db_path) as conn:
        for posting in all_postings:
            result = score_posting(posting, cfg)
            is_new = storage.upsert(conn, posting, result.score, result.excluded, result.exclude_reason)

            if result.excluded:
                excluded_count += 1
                continue
            if is_new:
                new_count += 1
            if result.score < min_score:
                continue

            rows.append(
                {
                    "score": result.score,
                    "is_new": is_new,
                    "title": posting.title,
                    "company": posting.company,
                    "location": posting.location,
                    "posted_date": posting.posted_date,
                    "url": posting.url,
                    "salary_min": result.salary_min,
                    "salary_max": result.salary_max,
                    "salary_display": format_salary(result.salary_min, result.salary_max),
                }
            )

    rows.sort(key=lambda r: (r["score"], r["posted_date"] or ""), reverse=True)

    out_cfg = cfg.get("output", {})
    report.write_html(rows, out_cfg.get("html_path", "output/jobs.html"), min_score, new_count, excluded_count)
    if out_cfg.get("write_csv", False):
        report.write_csv(rows, out_cfg.get("csv_path", "output/jobs.csv"))

    print(f"\nDone. {len(rows)} postings shown, {new_count} new, {excluded_count} excluded.")
    print(f"Report: {out_cfg.get('html_path', 'output/jobs.html')}")


if __name__ == "__main__":
    main()
