from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import json
import sys
from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, ValidationError, field_validator, model_validator


# Traceability references for task 3 implementation.
TRACEABILITY_FILTERING = "openspec/specs/procurement-handoff/spec.md::Requirement: Inventory query filtering"
TRACEABILITY_RANKING = "openspec/specs/procurement-handoff/spec.md::Requirement: Result ranking for search relevance"
TRACEABILITY_CONDITIONAL_COMPLIANCE = "openspec/specs/procurement-handoff/spec.md::Requirement: Conditional compliance detail in search response"
TRACEABILITY_NO_MATCH = "openspec/specs/procurement-handoff/spec.md::Requirement: Explicit no-match response"

OUT_OF_POLICY_REASON_CODE = "OUT_OF_POLICY_REFUSAL"
REQUEST_SCHEMA_INVALID_REASON = "REQUEST_SCHEMA_INVALID"
UNSUPPORTED_URGENCY_REASON = "UNSUPPORTED_URGENCY"
QUANTITY_EXCEEDS_AUTOMATION_LIMIT_REASON = "QUANTITY_EXCEEDS_AUTOMATION_LIMIT"
MAX_AUTOMATION_QUANTITY = 2500
SUPPORTED_URGENCY = {"low", "medium", "high"}


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


class DecisionEvidence(BaseModel):
    source: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    traceability_ref: str | None = None


class ComplianceSummary(BaseModel):
    failed_rules: list[str]
    reasons: list[str]
    policy_version: str = Field(min_length=1)
    evaluated_at_utc: str | None = None
    traceability_refs: list[str]


class MatchResultItem(BaseModel):
    sku: str = Field(min_length=1)
    score: float = Field(ge=0.0)
    stock_qty: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)
    unit_price: float = Field(ge=0.0)
    compliance_status: Literal["compliant"]
    fulfillment_rationale: str = Field(min_length=1)
    traceability_refs: list[str]
    compliance_summary: ComplianceSummary | None = None


class MatchRequest(BaseModel):
    tire_size: str = Field(min_length=3)
    load_index: int = Field(ge=1)
    speed_rating: str = Field(min_length=1, max_length=1)
    region_code: str = Field(min_length=2, max_length=2)
    quantity_needed: int = Field(ge=1)

    @field_validator("speed_rating")
    @classmethod
    def normalize_speed_rating(cls, value: str) -> str:
        return value.upper()

    @field_validator("region_code")
    @classmethod
    def normalize_region_code(cls, value: str) -> str:
        return value.upper()


class MatchResponse(BaseModel):
    status: Literal["match"]
    decision: Literal["approve"]
    rationale: str = Field(min_length=1)
    evidence: list[DecisionEvidence] = Field(min_length=1)
    request: MatchRequest
    results: list[MatchResultItem] = Field(min_length=1)
    ranking_rule: str = Field(min_length=1)
    traceability_refs: list[str]


class NoMatchResponse(BaseModel):
    status: Literal["no_match"]
    decision: Literal["deny", "escalate"]
    rationale: str = Field(min_length=1)
    evidence: list[DecisionEvidence] = Field(min_length=1)
    request: MatchRequest
    reason_codes: list[str] = Field(min_length=1)
    suggested_relaxations: list[str]
    traceability_refs: list[str]

    @field_validator("reason_codes")
    @classmethod
    def reason_codes_must_be_non_empty_strings(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().upper() for value in values if value.strip()]
        if not normalized:
            raise ValueError("reason_codes must contain at least one non-empty code")
        return normalized

    @model_validator(mode="after")
    def enforce_escalation_consistency(self) -> "NoMatchResponse":
        has_human_review = "REQUIRES_HUMAN_REVIEW" in self.reason_codes
        if has_human_review and self.decision != "escalate":
            raise ValueError("REQUIRES_HUMAN_REVIEW requires decision=escalate")
        if not has_human_review and self.decision != "deny":
            raise ValueError("no_match without human review should set decision=deny")
        return self


SearchResponse = Annotated[MatchResponse | NoMatchResponse, Field(discriminator="status")]
SEARCH_RESPONSE_ADAPTER = TypeAdapter(SearchResponse)


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


def _build_match_evidence(preprocess_result: object, ranked_items: list[dict[str, object]]) -> list[DecisionEvidence]:
    evidence: list[DecisionEvidence] = [
        DecisionEvidence(
            source="ranking",
            detail=f"{len(ranked_items)} compliant in-stock candidate(s) satisfy requested quantity",
            traceability_ref=TRACEABILITY_RANKING,
        )
    ]

    top = ranked_items[0] if ranked_items else None
    if top is not None:
        evidence.append(
            DecisionEvidence(
                source="top_candidate",
                detail=f"top SKU {top['sku']} selected by deterministic ranking and fulfillment preference",
                traceability_ref=TRACEABILITY_FILTERING,
            )
        )

    if getattr(preprocess_result, "auto_recommendation_blocked", False):
        evidence.append(
            DecisionEvidence(
                source="compliance",
                detail="policy precedence ambiguity detected in preprocessing",
                traceability_ref=TRACEABILITY_CONDITIONAL_COMPLIANCE,
            )
        )
    return evidence


def _build_no_match_evidence(reason_codes: list[str]) -> list[DecisionEvidence]:
    detail = "no candidate satisfies required fitment, compliance, and availability constraints"
    if "INSUFFICIENT_AVAILABILITY" in reason_codes:
        detail = "candidates exist but none can satisfy quantity at current availability/lead constraints"
    if "REQUIRES_HUMAN_REVIEW" in reason_codes:
        detail = "request requires manual compliance resolution before recommendation can proceed"

    return [
        DecisionEvidence(
            source="no_match_analysis",
            detail=detail,
            traceability_ref=TRACEABILITY_NO_MATCH,
        )
    ]


def _safe_match_request(request: SearchRequest) -> MatchRequest:
    tire_size = str(getattr(request, "tire_size", "") or "").strip() or "UNK"
    if len(tire_size) < 3:
        tire_size = "UNK"

    try:
        load_index = int(getattr(request, "load_index", 1) or 1)
    except (TypeError, ValueError):
        load_index = 1
    load_index = max(load_index, 1)

    speed_rating_raw = str(getattr(request, "speed_rating", "") or "K").strip().upper()
    speed_rating = speed_rating_raw[:1] if speed_rating_raw else "K"

    region_raw = str(getattr(request, "region_code", "") or "TX").strip().upper()
    region_code = region_raw[:2] if len(region_raw) >= 2 else "TX"

    try:
        quantity_needed = int(getattr(request, "quantity_needed", 1) or 1)
    except (TypeError, ValueError):
        quantity_needed = 1
    quantity_needed = max(quantity_needed, 1)

    return MatchRequest(
        tire_size=tire_size,
        load_index=load_index,
        speed_rating=speed_rating,
        region_code=region_code,
        quantity_needed=quantity_needed,
    )


def _out_of_policy_reason_codes(
    request_payload: MatchRequest,
    replacement_urgency: str,
) -> list[str]:
    reasons: list[str] = []
    if request_payload.quantity_needed > MAX_AUTOMATION_QUANTITY:
        reasons.append(QUANTITY_EXCEEDS_AUTOMATION_LIMIT_REASON)
    if replacement_urgency.lower() not in SUPPORTED_URGENCY:
        reasons.append(UNSUPPORTED_URGENCY_REASON)
    return reasons


def _build_out_of_policy_refusal(
    request_payload: MatchRequest,
    reason_codes: list[str],
) -> dict[str, object]:
    normalized_reason_codes = [OUT_OF_POLICY_REASON_CODE, *reason_codes]
    response = NoMatchResponse(
        status="no_match",
        decision="deny",
        rationale="request is out of policy for autonomous recommendation processing",
        evidence=[
            DecisionEvidence(
                source="policy_guardrail",
                detail="request refused before scoring due to policy guardrails",
                traceability_ref=TRACEABILITY_FILTERING,
            ),
            DecisionEvidence(
                source="policy_guardrail",
                detail="out-of-policy refusal generated as safe boundary response",
                traceability_ref=TRACEABILITY_NO_MATCH,
            ),
        ],
        request=request_payload,
        reason_codes=normalized_reason_codes,
        suggested_relaxations=["request_manual_review"],
        traceability_refs=[
            TRACEABILITY_FILTERING,
            TRACEABILITY_NO_MATCH,
        ],
    )
    return SEARCH_RESPONSE_ADAPTER.validate_python(response).model_dump(exclude_none=True)


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
    request_payload = _safe_match_request(request)

    try:
        MatchRequest(
            tire_size=request.tire_size,
            load_index=request.load_index,
            speed_rating=request.speed_rating,
            region_code=request.region_code,
            quantity_needed=request.quantity_needed,
        )
    except ValidationError:
        return _build_out_of_policy_refusal(request_payload, [REQUEST_SCHEMA_INVALID_REASON])

    refusal_reason_codes = _out_of_policy_reason_codes(request_payload, request.replacement_urgency)
    if refusal_reason_codes:
        return _build_out_of_policy_refusal(request_payload, refusal_reason_codes)

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
        response = MatchResponse(
            status="match",
            decision="approve",
            rationale="compliant and fulfillable inventory options were found and ranked deterministically",
            evidence=_build_match_evidence(preprocess_result, ranked_items),
            request=request_payload,
            results=[MatchResultItem.model_validate(item) for item in ranked_items],
            ranking_rule=ranking.tie_break_rule,
            traceability_refs=[
                TRACEABILITY_FILTERING,
                TRACEABILITY_RANKING,
                TRACEABILITY_CONDITIONAL_COMPLIANCE,
            ],
        )
        return SEARCH_RESPONSE_ADAPTER.validate_python(response).model_dump(exclude_none=True)

    reason_codes = _build_reason_codes(
        ranked_count=len(ranking.ranked_candidates),
        inventory_filtered_count=len(ranked_items),
        preprocess_result=preprocess_result,
    )
    decision = "escalate" if "REQUIRES_HUMAN_REVIEW" in reason_codes else "deny"
    response = NoMatchResponse(
        status="no_match",
        decision=decision,
        rationale="no inventory option currently satisfies all mandatory constraints",
        evidence=_build_no_match_evidence(reason_codes),
        request=request_payload,
        reason_codes=reason_codes,
        suggested_relaxations=_suggested_relaxations(reason_codes),
        traceability_refs=[
            TRACEABILITY_FILTERING,
            TRACEABILITY_NO_MATCH,
        ],
    )
    return SEARCH_RESPONSE_ADAPTER.validate_python(response).model_dump(exclude_none=True)