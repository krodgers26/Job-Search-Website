"""Render the current, non-excluded postings to HTML and (optionally) CSV."""

import csv
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"


def write_html(rows: list[dict], html_path: str, min_score: int, new_count: int, excluded_count: int):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report.html.j2")
    html = template.render(
        postings=rows,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        min_score=min_score,
        new_count=new_count,
        excluded_count=excluded_count,
    )
    Path(html_path).parent.mkdir(parents=True, exist_ok=True)
    Path(html_path).write_text(html, encoding="utf-8")


def write_csv(rows: list[dict], csv_path: str):
    Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["score", "is_new", "title", "company", "location", "posted_date", "url"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})
