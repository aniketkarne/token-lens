"""Pricing calculator.

Pricing is USD per 1K INPUT tokens. The table is intentionally small: only
current, well-known models whose prices were verified against the providers'
published price sheets. Anything not listed here reports as unknown (None)
instead of guessing from a stale rate — use the CLI ``--price-per-1k``
override (or the ``price_per_1k`` config key) for models outside the table.

Table verified 2026-11-12 against OpenAI and Anthropic published pricing and
the OpenRouter model catalog. Re-verify at every release: models retire and
prices move. Prefer adding a row only when you are willing to keep it
current; a wrong price is worse than no price.
"""

from __future__ import annotations

import re

DEFAULT_PRICING = {
    # USD per 1K tokens, input side. Verified 2026-11-12 (see docstring).
    "gpt-6-luna": 0.0001,
    "gpt-6.1-terra": 0.001,
    "gpt-6.1-sol": 0.002,
    "claude-haiku-5-5": 0.0001,
    "claude-sonnet-5-5": 0.002,
    "claude-opus-5-5": 0.004,
    "grok-4.7": 0.002,
}

# A priced base id may carry a snapshot/alias suffix and still match, e.g.
# "claude-sonnet-5-5-20260928" or "gpt-6-luna:latest". Any other suffix
# (-mini, -pro, -turbo, ...) is a different SKU with its own price and is
# NOT matched — it reports as unknown until listed explicitly.
_SNAPSHOT_SUFFIX = re.compile(
    r"^[-:@](20\d{2}[-_]?\d{2}[-_]?\d{2}|\d{8}|latest|snapshot)$", re.IGNORECASE
)

# Optional vendor prefix as it appears in routed logs ("openai/gpt-6-luna").
_VENDOR_PREFIX = re.compile(r"^[a-z0-9][a-z0-9._-]*/", re.IGNORECASE)


def _normalize(model: str) -> str:
    key = (model or "").strip().lower()
    m = _VENDOR_PREFIX.match(key)
    if m:
        key = key[m.end() :]
    # digit.digit -> digit-digit so "claude-sonnet-5.5" hits "claude-sonnet-5-5"
    return re.sub(r"(?<=\d)\.(?=\d)", "-", key)


def _lookup_rate(model: str):
    """Return (rate_per_1k, matched_key) or (None, None)."""
    key = _normalize(model)
    if not key:
        return None, None
    table = {_normalize(k): v for k, v in DEFAULT_PRICING.items()}
    if key in table:
        return table[key], key
    for base, rate in table.items():
        if key.startswith(base) and _SNAPSHOT_SUFFIX.match(key[len(base) :]):
            return rate, base
    return None, None


def estimate_cost(model: str, tokens: int, override_per_1k: float | None) -> tuple[float | None, str | None]:
    """Return (usd_cost, label). ``None`` if no price is known."""
    if override_per_1k is not None:
        return (tokens / 1000.0) * override_per_1k, f"override@${override_per_1k:.5f}/1K"

    if not model:
        return None, None
    rate, base = _lookup_rate(model)
    if rate is None:
        return None, None
    return (tokens / 1000.0) * rate, f"{base}@${rate:.5f}/1K"


__all__ = ["estimate_cost", "DEFAULT_PRICING"]
