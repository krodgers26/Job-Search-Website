"""Relevance scoring against your target-role profile in config.yaml."""

from dataclasses import dataclass
from datetime import date

from salary import parse_salary_range
from sources.common import Posting


@dataclass
class ScoreResult:
    score: int
    excluded: bool
    exclude_reason: str
    salary_min: int | None = None
    salary_max: int | None = None


def score_posting(posting: Posting, cfg: dict) -> ScoreResult:
    title_lower = posting.title.lower()
    desc_lower = posting.description.lower()
    location_lower = posting.location.lower()

    salary_min, salary_max = parse_salary_range(posting.description)

    # --- Hard excludes: title terms ------------------------------------
    for term in cfg.get("exclude_title_terms", []):
        if term.lower() in title_lower:
            return ScoreResult(0, True, f"title contains excluded term '{term}'", salary_min, salary_max)

    seniority_cfg = cfg.get("seniority", {})
    for term in seniority_cfg.get("exclude_terms", []):
        if term.lower() in title_lower:
            return ScoreResult(0, True, f"title contains junior-level term '{term}'", salary_min, salary_max)

    # --- Hard exclude: location ------------------------------------------
    location_cfg = cfg.get("location", {})
    target_terms = [t.lower() for t in location_cfg.get("target_location_terms", [])]
    remote_terms = [t.lower() for t in location_cfg.get("remote_terms", [])]

    has_target_location = any(t in location_lower for t in target_terms)
    has_remote = any(t in location_lower for t in remote_terms) or any(
        t in desc_lower for t in remote_terms
    )

    if location_cfg.get("exclude_if_no_location_match", False):
        if not has_target_location and not has_remote:
            return ScoreResult(
                0, True, f"location '{posting.location}' doesn't match Boston or remote", salary_min, salary_max
            )

    # --- Hard exclude: salary too low ---------------------------------------
    salary_cfg = cfg.get("salary", {})
    exclude_at_or_below = salary_cfg.get("exclude_if_max_at_or_below")
    if exclude_at_or_below is not None and salary_max is not None and salary_max <= exclude_at_or_below:
        return ScoreResult(
            0, True,
            f"salary tops out at ${salary_max:,}, at or below your ${exclude_at_or_below:,} cutoff",
            salary_min, salary_max,
        )

    # --- Scoring -----------------------------------------------------------
    score = 0

    for kw in cfg.get("scoring", {}).get("priority_keywords", []):
        phrase = kw["phrase"].lower()
        if phrase in title_lower:
            score += kw.get("weight_title", 0)
        elif phrase in desc_lower:
            score += kw.get("weight_description", 0)

    for kw in cfg.get("scoring", {}).get("firm_type_bonus", []):
        phrase = kw["phrase"].lower()
        if phrase in title_lower or phrase in desc_lower:
            score += kw.get("weight", 0)

    if has_target_location:
        score += location_cfg.get("target_location_bonus", 0)
    elif has_remote:
        score += location_cfg.get("remote_bonus", 0)

    for term in seniority_cfg.get("include_terms", []):
        if term.lower() in title_lower:
            score += seniority_cfg.get("include_bonus", 0)
            break

    # --- Salary bonus: reward being in or near your target range -----------
    if salary_min is not None and salary_max is not None:
        target_min = salary_cfg.get("target_min")
        target_max = salary_cfg.get("target_max")
        if target_min is not None and target_max is not None:
            overlaps_target = salary_min <= target_max and salary_max >= target_min
            buffer = salary_cfg.get("near_range_buffer", 0)
            near_target = (target_min - buffer) <= salary_max and salary_min <= (target_max + buffer)
            if overlaps_target:
                score += salary_cfg.get("in_range_bonus", 0)
            elif near_target:
                score += salary_cfg.get("near_range_bonus", 0)

    # --- Recency bonus: newer postings rank higher --------------------------
    if posting.posted_date:
        try:
            posted = date.fromisoformat(posting.posted_date)
            days_since_posted = (date.today() - posted).days
            for tier in cfg.get("recency", {}).get("bonus_tiers", []):
                if days_since_posted <= tier.get("within_days", 0):
                    score += tier.get("bonus", 0)
                    break
        except ValueError:
            pass

    return ScoreResult(score, False, "", salary_min, salary_max)
