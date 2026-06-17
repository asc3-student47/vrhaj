from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import json
from typing import Any


@dataclass(frozen=True)
class SupplierLookupRequest:
    sku: str
    requested_quantity: int
    max_lead_time_days: int


@dataclass(frozen=True)
class RuleResult:
    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class SupplierMatchResult:
    supplier_id: str | None
    supplier_name: str | None
    preferred: bool
    contract_id: str | None
    sku: str | None
    status: str
    reasons: list[str]
    failed_rules: list[str]
    rule_results: list[RuleResult]


def load_supplier_records(db_path: str | Path) -> list[dict[str, Any]]:
    """Load mock supplier records from JSON file and validate basic structure."""
    path = Path(db_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("Mock supplier database must be a JSON array of records")

    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each supplier record must be a JSON object")
        records.append(dict(item))

    return records


def lookup_contract_candidates(
    records: list[dict[str, Any]], request: SupplierLookupRequest
) -> list[dict[str, Any]]:
    """Flatten supplier contracts and keep only contracts that match the requested SKU."""
    wanted_sku = request.sku.upper()
    candidates: list[dict[str, Any]] = []

    for supplier in records:
        contracts = supplier.get("contracts", [])
        if not isinstance(contracts, list):
            continue

        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            contract_sku = str(contract.get("sku", "")).upper()
            if contract_sku != wanted_sku:
                continue

            candidates.append(
                {
                    "supplier_id": supplier.get("id"),
                    "supplier_name": supplier.get("name"),
                    "preferred": bool(supplier.get("preferred", False)),
                    "contract": contract,
                }
            )

    return candidates


def evaluate_contract_candidate(
    candidate: dict[str, Any],
    request: SupplierLookupRequest,
    *,
    evaluation_date: date,
) -> SupplierMatchResult:
    """Evaluate one supplier contract against active, quantity, and lead-time constraints."""
    contract = candidate.get("contract", {})
    preferred = bool(candidate.get("preferred", False))

    rule_results: list[RuleResult] = []

    expiration_raw = str(contract.get("expiration_date", ""))
    try:
        expiration_date = date.fromisoformat(expiration_raw)
        is_active = expiration_date > evaluation_date
        reason = "contract active" if is_active else "contract inactive"
    except ValueError:
        is_active = False
        reason = "invalid contract expiration date"
    rule_results.append(RuleResult(name="contract_active", passed=is_active, reason=reason))

    available_quantity = int(contract.get("available_quantity", -1))
    quantity_ok = available_quantity >= request.requested_quantity
    quantity_reason = "sufficient quantity" if quantity_ok else "insufficient quantity"
    rule_results.append(
        RuleResult(name="available_quantity", passed=quantity_ok, reason=quantity_reason)
    )

    lead_time_days = int(contract.get("lead_time_days", 10**9))
    lead_time_ok = lead_time_days <= request.max_lead_time_days
    lead_time_reason = "lead time met" if lead_time_ok else "lead time exceeds request"
    rule_results.append(
        RuleResult(name="lead_time_days", passed=lead_time_ok, reason=lead_time_reason)
    )

    failed_rules = [result.name for result in rule_results if not result.passed]
    status = "eligible" if not failed_rules else "ineligible"
    reasons = [result.reason for result in rule_results]

    return SupplierMatchResult(
        supplier_id=str(candidate.get("supplier_id")) if candidate.get("supplier_id") else None,
        supplier_name=(
            str(candidate.get("supplier_name")) if candidate.get("supplier_name") else None
        ),
        preferred=preferred,
        contract_id=str(contract.get("contract_id")) if contract.get("contract_id") else None,
        sku=str(contract.get("sku")) if contract.get("sku") else None,
        status=status,
        reasons=reasons,
        failed_rules=failed_rules,
        rule_results=rule_results,
    )


def _rank_key(result: SupplierMatchResult) -> tuple[int, int, str, str]:
    """Rank eligible before ineligible, preferred before non-preferred, then stable keys."""
    eligibility_rank = 0 if result.status == "eligible" else 1
    preferred_rank = 0 if result.preferred else 1
    supplier_name = (result.supplier_name or "").lower()
    contract_id = (result.contract_id or "").lower()
    return (eligibility_rank, preferred_rank, supplier_name, contract_id)


def evaluate_request(
    db_path: str | Path,
    request: SupplierLookupRequest,
    *,
    evaluation_date: date | None = None,
) -> list[SupplierMatchResult]:
    """Lookup supplier contracts by SKU and evaluate eligibility against request constraints."""
    records = load_supplier_records(db_path)
    candidates = lookup_contract_candidates(records, request)

    if not candidates:
        return [
            SupplierMatchResult(
                supplier_id=None,
                supplier_name=None,
                preferred=False,
                contract_id=None,
                sku=request.sku,
                status="ineligible",
                reasons=["no supplier contract found for requested sku"],
                failed_rules=["lookup"],
                rule_results=[
                    RuleResult(
                        name="lookup",
                        passed=False,
                        reason="no supplier contract found for requested sku",
                    )
                ],
            )
        ]

    today = evaluation_date or date.today()
    evaluated = [
        evaluate_contract_candidate(candidate, request, evaluation_date=today)
        for candidate in candidates
    ]

    return sorted(evaluated, key=_rank_key)
