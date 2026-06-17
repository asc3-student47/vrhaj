from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import importlib.util
import json
import sys

from pydantic import BaseModel, Field, field_validator, model_validator


# Traceability references for task 1 implementation.
TRACEABILITY_SIZE_AND_RATING = "openspec/specs/tire-compliance/spec.md::Requirement: Size and rating eligibility"
TRACEABILITY_REGIONAL_LEGAL = "openspec/specs/tire-compliance/spec.md::Requirement: Regional legal and certification checks"
TRACEABILITY_POLICY_TRACE = "openspec/specs/tire-compliance/spec.md::Requirement: Policy version traceability"
TRACEABILITY_AMBIGUITY = "openspec/specs/tire-compliance/spec.md::Requirement: Ambiguity escalation"


def _load_compliance_module() -> object:
    repo_root = Path(__file__).resolve().parents[2]
    module_path = repo_root / "subsystem" / "compliance-system" / "compliance_system.py"
    spec = importlib.util.spec_from_file_location("compliance_system", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load compliance subsystem module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_compliance_system = _load_compliance_module()
ComplianceRequest = _compliance_system.ComplianceRequest
evaluate_request = _compliance_system.evaluate_request


class PreprocessRequest(BaseModel):
    tire_size: str | None = None
    min_load_index: int | None = None
    min_speed_rating: str | None = None
    application: str | None = None
    region_code: str | None = None
    required_certifications: list[str] | None = None
    # Optional allowlist from internal policy. Conflicts with legal region support
    # are treated as unresolved precedence and escalated for human review.
    company_policy_region_allowlist: list[str] | None = None

    @field_validator("min_speed_rating")
    @classmethod
    def normalize_speed_rating(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("region_code")
    @classmethod
    def normalize_region_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("required_certifications", "company_policy_region_allowlist")
    @classmethod
    def normalize_list_values(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        normalized = [item.strip().upper() for item in value if item and item.strip()]
        return normalized or None


class ComplianceEvidence(BaseModel):
    rule: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    traceability_ref: str | None = None


class CandidateCompliance(BaseModel):
    sku: str = Field(min_length=1)
    eligible: bool
    requires_human_review: bool
    failed_rules: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    policy_version: str = Field(min_length=1)
    evaluated_at_utc: str = Field(min_length=1)
    traceability_refs: list[str] = Field(min_length=1)
    evidence: list[ComplianceEvidence] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_state_consistency(self) -> "CandidateCompliance":
        if self.requires_human_review and self.eligible:
            raise ValueError("requires_human_review=true cannot be eligible")
        if not self.eligible and (not self.failed_rules or not self.reasons):
            raise ValueError("non-eligible candidates must include failed_rules and reasons")
        if self.requires_human_review and "policy_precedence" not in self.failed_rules:
            raise ValueError("human review candidates must include policy_precedence failed rule")
        return self


class PreprocessResult(BaseModel):
    eligible_skus: list[str]
    compliance_results: list[CandidateCompliance] = Field(default_factory=list)
    auto_recommendation_blocked: bool

    @model_validator(mode="after")
    def validate_aggregate_consistency(self) -> "PreprocessResult":
        if self.auto_recommendation_blocked and not any(
            item.requires_human_review for item in self.compliance_results
        ):
            raise ValueError("auto_recommendation_blocked requires at least one human-review candidate")
        return self


def load_supplier_skus(suppliers_db_path: str | Path) -> list[str]:
    path = Path(suppliers_db_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("Supplier database must be a JSON array")

    skus: list[str] = []
    seen: set[str] = set()

    for supplier in payload:
        contracts = supplier.get("contracts", []) if isinstance(supplier, dict) else []
        for contract in contracts:
            if not isinstance(contract, dict):
                continue
            sku = str(contract.get("sku", "")).strip()
            if sku and sku not in seen:
                skus.append(sku)
                seen.add(sku)

    return skus


def _build_traceability_refs(
    include_ambiguity: bool,
) -> list[str]:
    refs = [
        TRACEABILITY_SIZE_AND_RATING,
        TRACEABILITY_REGIONAL_LEGAL,
        TRACEABILITY_POLICY_TRACE,
    ]
    if include_ambiguity:
        refs.append(TRACEABILITY_AMBIGUITY)
    return refs


def _build_candidate_evidence(
    failed_rules: list[str],
    reasons: list[str],
    traceability_refs: list[str],
) -> list[ComplianceEvidence]:
    fallback_ref = traceability_refs[0] if traceability_refs else None
    evidence: list[ComplianceEvidence] = []
    for index, reason in enumerate(reasons):
        rule = failed_rules[index] if index < len(failed_rules) else "compliance_evaluation"
        trace_ref = traceability_refs[min(index, len(traceability_refs) - 1)] if traceability_refs else fallback_ref
        evidence.append(
            ComplianceEvidence(
                rule=rule,
                detail=reason,
                traceability_ref=trace_ref,
            )
        )
    return evidence


def _company_policy_conflicts_with_legal(
    request: PreprocessRequest,
    legal_region_passed: bool,
) -> bool:
    if request.region_code is None or request.company_policy_region_allowlist is None:
        return False
    company_passed = request.region_code.upper() in {
        region.upper() for region in request.company_policy_region_allowlist
    }
    return company_passed != legal_region_passed


def preprocess_candidates_with_compliance(
    compliance_db_path: str | Path,
    suppliers_db_path: str | Path,
    request: PreprocessRequest,
    *,
    policy_version: str,
) -> PreprocessResult:
    """Run task-1 compliance preprocessing over supplier SKUs before ranking."""
    candidate_skus = load_supplier_skus(suppliers_db_path)
    evaluated_at = datetime.now(UTC).isoformat()

    results: list[CandidateCompliance] = []
    eligible_skus: list[str] = []
    auto_recommendation_blocked = False

    for sku in candidate_skus:
        compliance_request = ComplianceRequest(
            sku=sku,
            tire_size=request.tire_size,
            min_load_index=request.min_load_index,
            min_speed_rating=request.min_speed_rating,
            application=request.application,
            region_code=request.region_code,
            required_certifications=request.required_certifications,
        )
        evaluations = evaluate_request(compliance_db_path, compliance_request)
        evaluation = evaluations[0]

        legal_region_passed = "region_code" not in evaluation.failed_rules
        has_ambiguity = _company_policy_conflicts_with_legal(request, legal_region_passed)
        requires_human_review = has_ambiguity

        failed_rules = list(evaluation.failed_rules)
        reasons = list(evaluation.reasons)

        if has_ambiguity:
            failed_rules.append("policy_precedence")
            reasons.append("regional policy precedence conflict; requires human review")
            auto_recommendation_blocked = True

        eligible = evaluation.status == "compliant" and not requires_human_review
        if eligible:
            eligible_skus.append(sku)

        traceability_refs = _build_traceability_refs(has_ambiguity)
        results.append(
            CandidateCompliance(
                sku=sku,
                eligible=eligible,
                requires_human_review=requires_human_review,
                failed_rules=failed_rules,
                reasons=reasons,
                policy_version=policy_version,
                evaluated_at_utc=evaluated_at,
                traceability_refs=traceability_refs,
                evidence=_build_candidate_evidence(failed_rules, reasons, traceability_refs),
            )
        )

    return PreprocessResult(
        eligible_skus=eligible_skus,
        compliance_results=results,
        auto_recommendation_blocked=auto_recommendation_blocked,
    )