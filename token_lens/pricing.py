"""Pricing calculator.

Pricing is per 1K tokens (USD) for input text. The table is intentionally
small and easy to override via the CLI ``--price-per-1k`` flag.
"""

from __future__ import annotations

DEFAULT_PRICING = {
    # USD per 1K tokens, input side
    "gpt-4": 0.03,
    "gpt-4o": 0.005,
    "gpt-4o-mini": 0.00015,
    "gpt-3.5-turbo": 0.0015,
    "claude-3-opus": 0.015,
    "claude-3-sonnet": 0.003,
    "claude-3-haiku": 0.00025,
    "gemini-1.5-pro": 0.0035,
    "gemini-1.5-flash": 0.00035,
}


def estimate_cost(model: str, tokens: int, override_per_1k: float | None) -> tuple[float | None, str | None]:
    """Return (usd_cost, label). ``None`` if no price is known."""

    if override_per_1k is not None:
        return (tokens / 1000.0) * override_per_1k, f"override@${override_per_1k:.5f}/1K"

    if not model:
        return None, None
    key = model.lower()
    if key in DEFAULT_PRICING:
        rate = DEFAULT_PRICING[key]
        return (tokens / 1000.0) * rate, f"{key}@${rate:.5f}/1K"

    # Substring match for variant identifiers
    for prefix, rate in DEFAULT_PRICING.items():
        if prefix in key:
            return (tokens / 1000.0) * rate, f"{prefix}@${rate:.5f}/1K"

    return None, None


__all__ = ["estimate_cost", "DEFAULT_PRICING"]
