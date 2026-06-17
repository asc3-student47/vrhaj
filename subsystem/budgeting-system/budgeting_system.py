from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any


@dataclass(frozen=True)
class BudgetLookupRequest:
    contract_id: str
    total_cost: Any | None = None
    unit_cost: Any | None = None
    count: Any | None = None


@dataclass(frozen=True)
class BudgetDecision:
    response_code: str
    reason_codes: list[str]
    contract_id: str
    total_cost: float | None
    cost_center_id: str | None


@dataclass(frozen=True)
class BudgetRecord:
    cost_center_id: str
    name: str
    allocated: float
    remaining: float


def load_budget_record(db_path: str | Path) -> BudgetRecord:
    """Load and validate the single-cost-center MVP budget record."""
    path = Path(db_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("Mock budget database must be a JSON array of records")
    if len(payload) != 1:
        raise ValueError("MVP budget database must contain exactly one cost center")

    item = payload[0]
    if not isinstance(item, dict):
        raise ValueError("Each budget record must be a JSON object")

    cost_center_id = str(item.get("cost_center_id", "")).strip()
    name = str(item.get("name", "")).strip()
    allocated = _parse_number(item.get("allocated"))
    remaining = _parse_number(item.get("remaining"))

    if not cost_center_id:
        raise ValueError("Budget record requires non-empty cost_center_id")
    if not name:
        raise ValueError("Budget record requires non-empty name")
    if allocated is None or allocated < 0:
        raise ValueError("Budget record requires non-negative numeric allocated")
    if remaining is None or remaining < 0:
        raise ValueError("Budget record requires non-negative numeric remaining")

    return BudgetRecord(
        cost_center_id=cost_center_id,
        name=name,
        allocated=allocated,
        remaining=remaining,
    )


def evaluate_request(db_path: str | Path, request: BudgetLookupRequest) -> BudgetDecision:
    """Evaluate budget eligibility using total_cost-only semantics."""
    budget = load_budget_record(db_path)

    if request.unit_cost is not None or request.count is not None:
        return _deny_invalid_cost_input(request, budget.cost_center_id)

    total_cost = _parse_number(request.total_cost)
    if total_cost is None or total_cost <= 0:
        return _deny_invalid_cost_input(request, budget.cost_center_id)

    if total_cost <= budget.remaining:
        return BudgetDecision(
            response_code="allow",
            reason_codes=[],
            contract_id=request.contract_id,
            total_cost=total_cost,
            cost_center_id=budget.cost_center_id,
        )

    return BudgetDecision(
        response_code="deny",
        reason_codes=["insufficient_budget"],
        contract_id=request.contract_id,
        total_cost=total_cost,
        cost_center_id=budget.cost_center_id,
    )


def _deny_invalid_cost_input(
    request: BudgetLookupRequest, cost_center_id: str | None
) -> BudgetDecision:
    parsed_total_cost = _parse_number(request.total_cost)
    return BudgetDecision(
        response_code="deny",
        reason_codes=["invalid_cost_input"],
        contract_id=request.contract_id,
        total_cost=parsed_total_cost,
        cost_center_id=cost_center_id,
    )


def _parse_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None
