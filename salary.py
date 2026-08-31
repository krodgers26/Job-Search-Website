"""Best-effort extraction of a base salary range from free-text job descriptions.

Job descriptions -- especially for Massachusetts-based roles, where state
pay-transparency law requires it for many employers -- often state a salary
range somewhere in the text. This looks for dollar amounts near an obvious
salary-related phrase, rather than scanning the whole description for any
dollar sign. That distinction matters here: PE/asset-management job postings
are full of unrelated dollar figures (fund size, deal size, AUM, portfolio
company revenue), so a blind scan would produce garbage.
"""

import re

_ANCHOR_RE = re.compile(
    r"(salary\s*range|base\s*salary|compensation\s*range|pay\s*range|"
    r"annual\s*salary|base\s*pay|salary|compensation)",
    re.IGNORECASE,
)

_AMOUNT_RE = re.compile(r"\$\s?(?P<comma>\d{1,3}(?:,\d{3})+)|\$\s?(?P<k>\d{2,3})\s?[kK]\b")

# Window of text scanned after each anchor phrase for dollar amounts.
_WINDOW_CHARS = 160

# Sanity bounds on any individual amount, so an anchor sitting near an
# unrelated big number (fund size, ARR, etc.) can't be mistaken for a salary.
_MIN_PLAUSIBLE = 20_000
_MAX_PLAUSIBLE = 1_000_000


def _amount_to_int(match: re.Match) -> int:
    if match.group("comma"):
        return int(match.group("comma").replace(",", ""))
    return int(match.group("k")) * 1000


def parse_salary_range(text: str) -> tuple[int | None, int | None]:
    """Return (min, max) base salary found near a salary-related phrase, or
    (None, None) if nothing confident was found. A single disclosed figure
    (no range) comes back as (that figure, that figure)."""
    if not text:
        return (None, None)

    for anchor in _ANCHOR_RE.finditer(text):
        window = text[anchor.end():anchor.end() + _WINDOW_CHARS]
        amounts = [_amount_to_int(m) for m in _AMOUNT_RE.finditer(window)]
        amounts = [a for a in amounts if _MIN_PLAUSIBLE <= a <= _MAX_PLAUSIBLE]

        if len(amounts) >= 2:
            return (min(amounts[:2]), max(amounts[:2]))
        if len(amounts) == 1:
            return (amounts[0], amounts[0])

    return (None, None)
