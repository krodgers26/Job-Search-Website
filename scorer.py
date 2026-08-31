"""Relevance scoring against your target-role profile in config.yaml."""

from dataclasses import dataclass

from sources.common import Posting


@dataclass
class ScoreResult:
    score: int
    excluded: bool
    exclude_reason: str


def score_posting(posting: Posting, cfg: dict) -> ScoreResult:
    title_lower = posting.title.lower()
    desc_lower = posting.description.lower()
    location_lower = posting.location.lower()

    # --- Hard excludes: title terms ------------------------------------
    for term in cfg.get("exclude_title_terms", []):
        if term.lower() in title_lower:
            return ScoreResult(0, True, f"title contains excluded term '{term}'")

    seniority_cfg = cfg.get("seniority", {})
    for term in seniority_cfg.get("exclude_terms", []):
        if term.lower() in title_lower:
            return ScoreResult(0, True, f"title contains junior-level term '{term}'")

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
            return ScoreResult(0, True, f"location '{posting.location}' doesn't match Boston or remote")

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

    return ScoreResult(score, False, "")
