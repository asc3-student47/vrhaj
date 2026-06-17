from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import importlib.util
import json
import sys


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


@dataclass(frozen=True)
class PreprocessRequest:
    tire_size: str | None = None
    min_load_index: int | None = None
    min_speed_rating: str | None = None
    application: str | None = None
    region_code: str | None = None
    required_certifications: list[str] | None = None
    # Optional allowlist from internal policy. Conflicts with legal region support
    # are treated as unresolved precedence and escalated for human review.
    company_policy_region_allowlist: list[str] | None = None


@dataclass(frozen=True)
class CandidateCompliance:
    sku: str
    eligible: bool
    requires_human_review: bool
    failed_rules: list[str]
    reasons: list[str]
    policy_version: str
    evaluated_at_utc: str
    traceability_refs: list[str]


@dataclass(frozen=True)
class PreprocessResult:
    eligible_skus: list[str]
    compliance_results: list[CandidateCompliance]
    auto_recommendation_blocked: bool


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

        results.append(
            CandidateCompliance(
                sku=sku,
                eligible=eligible,
                requires_human_review=requires_human_review,
                failed_rules=failed_rules,
                reasons=reasons,
                policy_version=policy_version,
                evaluated_at_utc=evaluated_at,
                traceability_refs=_build_traceability_refs(has_ambiguity),
            )
        )

    return PreprocessResult(
        eligible_skus=eligible_skus,
        compliance_results=results,
        auto_recommendation_blocked=auto_recommendation_blocked,
    )