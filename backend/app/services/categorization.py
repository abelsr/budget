import re
import unicodedata

from app.models import MerchantRule

_WHITESPACE = re.compile(r"\s+")


def normalize_match_text(value: str) -> str:
    """Normalize descriptions consistently before matching merchant rules."""
    normalized = unicodedata.normalize("NFD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    # Punctuation is formatting, not a word boundary: "S.A." and "SA" (or
    # "Sam's" and "Sams") should resolve to the same merchant.
    return _WHITESPACE.sub(" ", "".join(char if char.isalnum() or char.isspace() else "" for char in normalized)).strip()


def matching_category_id(rules: list[MerchantRule], description: str | None, tx_type: str) -> str | None:
    normalized = normalize_match_text(description or "")
    if not normalized:
        return None
    matches = [rule for rule in rules if rule.category.type == tx_type and rule.match_text in normalized]
    if not matches:
        return None
    # Longer patterns are more specific; the ID makes same-length ties deterministic.
    return max(matches, key=lambda rule: (len(rule.match_text), rule.id)).category_id
