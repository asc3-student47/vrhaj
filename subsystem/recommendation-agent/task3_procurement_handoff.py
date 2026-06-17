from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import json
import sys


# Traceability references for task 3 implementation.
TRACEABILITY_FILTERING = "openspec/specs/procurement-handoff/spec.md::Requirement: Inventory query filtering"
TRACEABILITY_RANKING = "openspec/specs/procurement-handoff/spec.md::Requirement: Result ranking for search relevance"
TRACEABILITY_CONDITIONAL_COMPLIANCE = "openspec/specs/procurement-handoff/spec.md::Requirement: Conditional compliance detail in search response"
TRACEABILITY_NO_MATCH = "openspec/specs/procurement-handoff/spec.md::Requirement: Explicit no-match response"


def _load_module(module_name: str, file_name: str) -> object:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "subsystem" / "recommendation-agent" / file_name
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {module_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_task1 = _load_module("task1_compliance", "task1_compliance.py")
_task2 = _load_module("task2_recommendation", "task2_recommendation.py")

PreprocessRequest = _task1.PreprocessRequest
preprocess_candidates_with_compliance = _task1.preprocess_candidates_with_compliance

ScoringRequest = _task2.ScoringRequest
rank_compliant_candidates = _task2.rank_compliant_candidates


@dataclass(frozen=True)
class SearchRequest:
    tire_size: str
    load_index: int
    speed_rating: str
    region_code: str
    quantity_needed: int
    replacement_urgency: str
    include_compliance_summary: bool = False
    required_certifications: list[str] | None = None
    application: str | None = None


def _load_supplier_contracts_by_sku(suppliers_db_path: str | Path) -> dict[str, dict[str, float]]:
    path = Path(suppliers_db_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("Supplier database must be a JSON array")

    metrics: dict[str, dict[str, float]] = {}
    for supplier in payload:
        if not isinstance(supplier, dict):
            continue
        contracts = supplier.get("contracts", [])
        if not isinstance(contracts, list):
            continue

        for contract in contracts:
            if not isinstance(contract, dict):
                continue

            sku = str(contract.get("sku", "")).strip()
            if not sku:
                continue

            unit_price = float(contract.get("unit_price", 0.0) or 0.0)
            available_quantity = float(contract.get("available_quantity", 0.0) or 0.0)
            lead_time_days = float(contract.get("lead_time_days", 999.0) or 999.0)

            current = metrics.get(sku)
            if current is None:
                metrics[sku] = {
                    "unit_price": unit_price,
                    "available_quantity": available_quantity,
                    "lead_time_days": lead_time_days,
                }
                continue

            if unit_price < current["unit_price"] or (
                unit_price == current["unit_price"] and lead_time_days < current["lead_time_days"]
            ):
                current["unit_price"] = unit_price
                current["lead_time_days"] = lead_time_days
            current["available_quantity"] += available_quantity

    return metrics


def _build_reason_codes(
    ranked_count: int,
    inventory_filtered_count: int,
    preprocess_result: object,
) -> list[str]:
    if ranked_count == 0:
        return ["NO_COMPLIANT_CANDIDATES"]

    reason_codes: list[str] = []
    if inventory_filtered_count == 0:
        reason_codes.append("INSUFFICIENT_AVAILABILITY")

    if getattr(preprocess_result, "auto_recommendation_blocked", False):
        reason_codes.append("REQUIRES_HUMAN_REVIEW")

    return reason_codes or ["NO_MATCH_UNSPECIFIED"]


def _suggested_relaxations(reason_codes: list[str]) -> list[str]:
    suggestions: list[str] = []
    if "INSUFFICIENT_AVAILABILITY" in reason_codes:
        suggestions.append("allow_longer_lead_time")
        suggestions.append("split_across_suppliers")
    if "NO_COMPLIANT_CANDIDATES" in reason_codes:
        suggestions.append("widen_fitment_if_policy_allows")
        suggestions.append("request_manual_compliance_review")
    if "REQUIRES_HUMAN_REVIEW" in reason_codes:
        suggestions.append("resolve_policy_precedence")
    return suggestions


def search_inventory(
    compliance_db_path: str | Path,
    suppliers_db_path: str | Path,
    request: SearchRequest,
    *,
    policy_version: str,
    scoring_weights: dict[str, float] | None = None,
) -> dict[str, object]:
    """Task 3 inventory/procurement handoff response.

    Deterministic output order is inherited from task 2 ranking flow.
    """
    preprocess_result = preprocess_candidates_with_compliance(
        compliance_db_path,
        suppliers_db_path,
        PreprocessRequest(
            tire_size=request.tire_size,
            min_load_index=request.load_index,
            min_speed_rating=request.speed_rating,
            application=request.application,
            region_code=request.region_code,
            required_certifications=request.required_certifications,
        ),
        policy_version=policy_version,
    )

    ranking = rank_compliant_candidates(
        preprocess_result,
        suppliers_db_path,
        compliance_db_path,
        ScoringRequest(
            quantity_needed=request.quantity_needed,
            replacement_urgency=request.replacement_urgency,
            weights=scoring_weights,
        ),
    )

    contracts_by_sku = _load_supplier_contracts_by_sku(suppliers_db_path)
    ranked_items: list[dict[str, object]] = []

    for candidate in ranking.ranked_candidates:
        supplier_metrics = contracts_by_sku.get(candidate.sku)
        if supplier_metrics is None:
            continue

        # Availability filter for handoff contract: must satisfy required quantity.
        if float(supplier_metrics["available_quantity"]) < request.quantity_needed:
            continue

        item = {
            "sku": candidate.sku,
            "score": candidate.total_score,
            "stock_qty": int(supplier_metrics["available_quantity"]),
            "lead_time_days": int(supplier_metrics["lead_time_days"]),
            "unit_price": float(supplier_metrics["unit_price"]),
            "compliance_status": "compliant",
            "fulfillment_rationale": candidate.fulfillment_rationale,
            "traceability_refs": [TRACEABILITY_FILTERING, TRACEABILITY_RANKING],
        }

        if request.include_compliance_summary:
            compliance = next((r for r in preprocess_result.compliance_results if r.sku == candidate.sku), None)
            item["compliance_summary"] = {
                "failed_rules": [] if compliance is None else list(compliance.failed_rules),
                "reasons": [] if compliance is None else list(compliance.reasons),
                "policy_version": policy_version,
                "evaluated_at_utc": None if compliance is None else compliance.evaluated_at_utc,
                "traceability_refs": [
                    TRACEABILITY_CONDITIONAL_COMPLIANCE,
                    TRACEABILITY_FILTERING,
                ],
            }

        ranked_items.append(item)

    if ranked_items:
        return {
            "status": "match",
            "request": {
                "tire_size": request.tire_size,
                "load_index": request.load_index,
                "speed_rating": request.speed_rating,
                "region_code": request.region_code,
                "quantity_needed": request.quantity_needed,
            },
            "results": ranked_items,
            "ranking_rule": ranking.tie_break_rule,
            "traceability_refs": [
                TRACEABILITY_FILTERING,
                TRACEABILITY_RANKING,
                TRACEABILITY_CONDITIONAL_COMPLIANCE,
            ],
        }

    reason_codes = _build_reason_codes(
        ranked_count=len(ranking.ranked_candidates),
        inventory_filtered_count=len(ranked_items),
        preprocess_result=preprocess_result,
    )
    return {
        "status": "no_match",
        "request": {
            "tire_size": request.tire_size,
            "load_index": request.load_index,
            "speed_rating": request.speed_rating,
            "region_code": request.region_code,
            "quantity_needed": request.quantity_needed,
        },
        "reason_codes": reason_codes,
        "suggested_relaxations": _suggested_relaxations(reason_codes),
        "traceability_refs": [
            TRACEABILITY_FILTERING,
            TRACEABILITY_NO_MATCH,
        ],
    }