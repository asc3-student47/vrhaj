from __future__ import annotations

from pathlib import Path
import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# Traceability references for task 2 implementation.
TRACEABILITY_RANK_ONLY_COMPLIANT = "openspec/specs/tire-recommendation/spec.md::Requirement: Rank only compliant candidates"
TRACEABILITY_WEIGHTED_SCORING = "openspec/specs/tire-recommendation/spec.md::Requirement: Weighted objective scoring"
TRACEABILITY_FULFILLMENT = "openspec/specs/tire-recommendation/spec.md::Requirement: Volume fulfillment preference"
TRACEABILITY_TIE_BREAK = "openspec/specs/tire-recommendation/spec.md::Requirement: Deterministic tie-breaking"

DEFAULT_URGENCY_MAX_LEAD_DAYS = {
    "low": 30,
    "medium": 14,
    "high": 5,
}

DEFAULT_WEIGHTS = {
    "availability": 0.25,
    "lifecycle_cost": 0.35,
    "fuel_impact": 0.15,
    "warranty_quality": 0.25,
}


class ScoringRequest(BaseModel):
    quantity_needed: int = Field(ge=1)
    replacement_urgency: Literal["low", "medium", "high"]
    weights: dict[str, float] | None = None


class ScoreComponents(BaseModel):
    availability: float = Field(ge=0.0, le=1.0)
    lifecycle_cost: float = Field(ge=0.0, le=1.0)
    fuel_impact: float = Field(ge=0.0, le=1.0)
    warranty_quality: float = Field(ge=0.0, le=1.0)


class ScoringEvidence(BaseModel):
    source: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    traceability_ref: str | None = None


class ScoredCandidate(BaseModel):
    sku: str = Field(min_length=1)
    total_score: float = Field(ge=0.0)
    component_scores: ScoreComponents
    fulfillment_score: float = Field(ge=0.0, le=1.0)
    fulfillment_rationale: str = Field(min_length=1)
    lead_time_days: int = Field(ge=0)
    unit_price: float = Field(ge=0.0)
    traceability_refs: list[str] = Field(min_length=1)
    evidence: list[ScoringEvidence] = Field(min_length=1)

    @field_validator("traceability_refs")
    @classmethod
    def traceability_refs_must_be_non_empty(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item.strip()]
        if not normalized:
            raise ValueError("traceability_refs must include at least one value")
        return normalized


class RankingResult(BaseModel):
    ranked_candidates: list[ScoredCandidate] = Field(default_factory=list)
    excluded_skus: list[str] = Field(default_factory=list)
    tie_break_rule: str = Field(min_length=1)


def _load_json_array(path: str | Path, label: str) -> list[dict]:
    payload_path = Path(path)
    with payload_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, list):
        raise ValueError(f"{label} must be a JSON array")
    records = [item for item in payload if isinstance(item, dict)]
    return records


def _load_supplier_metrics_by_sku(suppliers_db_path: str | Path) -> dict[str, dict[str, float]]:
    suppliers = _load_json_array(suppliers_db_path, "Supplier database")
    metrics: dict[str, dict[str, float]] = {}

    for supplier in suppliers:
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

            # Keep the contract option that is cheaper first, then faster.
            if unit_price < current["unit_price"] or (
                unit_price == current["unit_price"] and lead_time_days < current["lead_time_days"]
            ):
                current["unit_price"] = unit_price
                current["lead_time_days"] = lead_time_days

            # Quantity can be aggregated across contracts for practical fulfillment signal.
            current["available_quantity"] += available_quantity

    return metrics


def _load_compliance_attrs_by_sku(compliance_db_path: str | Path) -> dict[str, dict[str, float]]:
    compliance_records = _load_json_array(compliance_db_path, "Compliance database")
    attrs: dict[str, dict[str, float]] = {}

    for record in compliance_records:
        sku = str(record.get("sku", "")).strip()
        if not sku:
            continue
        estimated_mileage = float(record.get("estimated_mileage", 0.0) or 0.0)
        certifications = record.get("certifications", [])
        cert_set = {str(cert).upper() for cert in certifications} if isinstance(certifications, list) else set()

        # EPA-SmartWay is used as a lightweight fuel-efficiency proxy in v1.
        fuel_impact = 1.0 if "EPA-SMARTWAY" in cert_set else 0.5

        # Optional warranty quality signal defaults to neutral when absent.
        warranty_quality = float(record.get("warranty_quality", 0.5) or 0.5)
        warranty_quality = max(0.0, min(1.0, warranty_quality))

        attrs[sku] = {
            "estimated_mileage": estimated_mileage,
            "fuel_impact": fuel_impact,
            "warranty_quality": warranty_quality,
        }

    return attrs


def _get_eligible_skus(preprocess_result: object) -> tuple[list[str], list[str]]:
    eligible_skus = [item.sku for item in preprocess_result.compliance_results if item.eligible]
    excluded_skus = [item.sku for item in preprocess_result.compliance_results if not item.eligible]
    return eligible_skus, excluded_skus


def _urgency_max_lead_days(urgency: str) -> int:
    return DEFAULT_URGENCY_MAX_LEAD_DAYS.get(urgency.lower(), DEFAULT_URGENCY_MAX_LEAD_DAYS["medium"])


def _effective_weights(overrides: dict[str, float] | None) -> dict[str, float]:
    weights = dict(DEFAULT_WEIGHTS)
    if overrides:
        for key in weights:
            if key in overrides:
                weights[key] = float(overrides[key])
    total = sum(weights.values())
    if total <= 0:
        raise ValueError("Score weights must sum to a positive value")
    return {key: value / total for key, value in weights.items()}


def _fulfillment_score(
    quantity_needed: int,
    lead_time_days: float,
    available_quantity: float,
    urgency: str,
) -> tuple[float, str]:
    max_lead = _urgency_max_lead_days(urgency)
    lead_ok = lead_time_days <= max_lead
    quantity_ok = available_quantity >= quantity_needed

    if lead_ok and quantity_ok:
        return 1.0, "fulfillable within urgency lead-time constraints"
    if quantity_ok and not lead_ok:
        return 0.65, "inventory is sufficient but lead time exceeds urgency window"
    if lead_ok and not quantity_ok:
        return 0.35, "lead time is acceptable but available quantity is insufficient"
    return 0.0, "cannot fulfill quantity within urgency lead-time constraints"


def _cost_per_mile(unit_price: float, estimated_mileage: float) -> float:
    if estimated_mileage <= 0:
        return float("inf")
    return unit_price / estimated_mileage


def _tie_break_key(candidate: ScoredCandidate) -> tuple[float, float, float, int, float, str]:
    return (
        candidate.total_score,
        candidate.fulfillment_score,
        candidate.component_scores.availability,
        -candidate.lead_time_days,
        -candidate.unit_price,
        "".join(chr(255 - ord(c)) for c in candidate.sku),
    )


def rank_compliant_candidates(
    preprocess_result: object,
    suppliers_db_path: str | Path,
    compliance_db_path: str | Path,
    scoring_request: ScoringRequest,
) -> RankingResult:
    """Task 2 ranking flow.

    Tie-break rule for identical total scores:
    1) higher fulfillment score
    2) higher availability score
    3) shorter lead time
    4) lower unit price
    5) lexical SKU ascending
    """

    eligible_skus, excluded_skus = _get_eligible_skus(preprocess_result)
    supplier_metrics = _load_supplier_metrics_by_sku(suppliers_db_path)
    compliance_attrs = _load_compliance_attrs_by_sku(compliance_db_path)
    weights = _effective_weights(scoring_request.weights)

    raw_scored: list[dict[str, object]] = []
    valid_costs: list[float] = []

    for sku in eligible_skus:
        supplier = supplier_metrics.get(sku)
        compliance = compliance_attrs.get(sku)
        if supplier is None or compliance is None:
            # Missing data cannot be scored in task 2.
            excluded_skus.append(sku)
            continue

        unit_price = float(supplier["unit_price"])
        available_quantity = float(supplier["available_quantity"])
        lead_time_days = int(supplier["lead_time_days"])
        estimated_mileage = float(compliance["estimated_mileage"])

        fulfillment_score, fulfillment_rationale = _fulfillment_score(
            quantity_needed=scoring_request.quantity_needed,
            lead_time_days=lead_time_days,
            available_quantity=available_quantity,
            urgency=scoring_request.replacement_urgency,
        )

        availability_score = min(available_quantity / max(scoring_request.quantity_needed, 1), 1.0)
        cost_per_mile = _cost_per_mile(unit_price, estimated_mileage)
        if cost_per_mile != float("inf"):
            valid_costs.append(cost_per_mile)

        raw_scored.append(
            {
                "sku": sku,
                "unit_price": unit_price,
                "lead_time_days": lead_time_days,
                "availability_score": availability_score,
                "cost_per_mile": cost_per_mile,
                "fuel_impact_score": float(compliance["fuel_impact"]),
                "warranty_quality_score": float(compliance["warranty_quality"]),
                "fulfillment_score": fulfillment_score,
                "fulfillment_rationale": fulfillment_rationale,
            }
        )

    max_valid_cost = max(valid_costs) if valid_costs else 1.0

    scored_candidates: list[ScoredCandidate] = []
    for candidate in raw_scored:
        cost_per_mile = float(candidate["cost_per_mile"])
        lifecycle_cost_score = 0.0 if cost_per_mile == float("inf") else max(0.0, 1.0 - (cost_per_mile / max_valid_cost))

        component_scores = ScoreComponents(
            availability=float(candidate["availability_score"]),
            lifecycle_cost=lifecycle_cost_score,
            fuel_impact=float(candidate["fuel_impact_score"]),
            warranty_quality=float(candidate["warranty_quality_score"]),
        )

        weighted_score = sum(
            getattr(component_scores, name) * weight for name, weight in weights.items()
        )

        # Fulfillment preference is applied as an additive preference term
        # after weighted objective scoring.
        total_score = weighted_score + (float(candidate["fulfillment_score"]) * 0.20)

        scored_candidates.append(
            ScoredCandidate(
                sku=str(candidate["sku"]),
                total_score=round(total_score, 8),
                component_scores=component_scores,
                fulfillment_score=float(candidate["fulfillment_score"]),
                fulfillment_rationale=str(candidate["fulfillment_rationale"]),
                lead_time_days=int(candidate["lead_time_days"]),
                unit_price=float(candidate["unit_price"]),
                traceability_refs=[
                    TRACEABILITY_RANK_ONLY_COMPLIANT,
                    TRACEABILITY_WEIGHTED_SCORING,
                    TRACEABILITY_FULFILLMENT,
                    TRACEABILITY_TIE_BREAK,
                ],
                evidence=[
                    ScoringEvidence(
                        source="weighted_scoring",
                        detail="candidate score calculated from weighted component objectives",
                        traceability_ref=TRACEABILITY_WEIGHTED_SCORING,
                    ),
                    ScoringEvidence(
                        source="fulfillment_preference",
                        detail=str(candidate["fulfillment_rationale"]),
                        traceability_ref=TRACEABILITY_FULFILLMENT,
                    ),
                ],
            )
        )

    ranked = sorted(scored_candidates, key=_tie_break_key, reverse=True)

    return RankingResult(
        ranked_candidates=ranked,
        excluded_skus=sorted(set(excluded_skus)),
        tie_break_rule="higher fulfillment, then higher availability, then shorter lead time, then lower unit price, then lexical SKU",
    )