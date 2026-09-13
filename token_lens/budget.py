"""Token budget configuration: load from YAML, expose as BudgetConfig."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

if TYPE_CHECKING:
    from .types import AnalysisReport


@dataclass(frozen=True)
class BudgetBreach:
    """A single overage detected by check_budget()."""

    code: str
    actual: float
    limit: float
    severity: str = "error"


@dataclass(frozen=True)
class BudgetConfig:
    """Token and cost budgets for `token-lens check`.

    All fields are optional. ``zones`` maps a zone name to a per-zone token
    ceiling. ``cost_usd`` caps the total estimated cost of a single trace.
    """

    total_tokens: int | None = None
    zones: Mapping[str, int] = field(default_factory=dict)
    cost_usd: float | None = None


def _coerce_int(v):
    if v is None:
        return None
    return int(v)


def _coerce_float(v):
    if v is None:
        return None
    return float(v)


def load_budget(path):
    """Load a budget config from a YAML file.

    Accepts the budget either at the top level of the file or nested under a
    ``budgets:`` key.
    """
    import yaml

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"budget config not found: {path}")

    with p.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    budgets = raw.get("budgets", raw) if isinstance(raw, dict) else {}

    total = _coerce_int(budgets.get("total_tokens"))
    cost = _coerce_float(budgets.get("cost_usd"))
    zones_raw = budgets.get("zones") or {}
    if not isinstance(zones_raw, dict):
        zones_raw = {}
    zones = {str(k): _coerce_int(v) for k, v in zones_raw.items() if v is not None}
    zones = {k: v for k, v in zones.items() if v is not None}

    return BudgetConfig(total_tokens=total, zones=zones, cost_usd=cost)


def check_budget(cfg, report):
    """Compare an AnalysisReport against a BudgetConfig; return all breaches."""
    breaches = []
    if cfg.total_tokens is not None and report.total_tokens > cfg.total_tokens:
        breaches.append(BudgetBreach(code="total_tokens", actual=float(report.total_tokens), limit=float(cfg.total_tokens)))
    by_zone = {z.zone.value: z.token_count for z in report.zones}
    for zone_name, limit in cfg.zones.items():
        actual = by_zone.get(zone_name, 0)
        if actual > limit:
            breaches.append(BudgetBreach(code=zone_name, actual=float(actual), limit=float(limit)))
    if cfg.cost_usd is not None and report.estimated_cost_usd is not None and report.estimated_cost_usd > cfg.cost_usd:
        breaches.append(BudgetBreach(code="cost_usd", actual=float(report.estimated_cost_usd), limit=float(cfg.cost_usd)))
    return breaches


__all__ = ["BudgetConfig", "BudgetBreach", "load_budget", "check_budget"]