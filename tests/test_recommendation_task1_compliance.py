from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task1_compliance.py"
COMPLIANCE_DB_PATH = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
SUPPLIERS_DB_PATH = REPO_ROOT / "subsystem" / "supplier-system" / "mock" / "suppliers-db.json"


spec = importlib.util.spec_from_file_location("task1_compliance", MODULE_PATH)
task1_compliance = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = task1_compliance
spec.loader.exec_module(task1_compliance)

PreprocessRequest = task1_compliance.PreprocessRequest
preprocess_candidates_with_compliance = task1_compliance.preprocess_candidates_with_compliance

TRACEABILITY_SIZE_AND_RATING = task1_compliance.TRACEABILITY_SIZE_AND_RATING
TRACEABILITY_REGIONAL_LEGAL = task1_compliance.TRACEABILITY_REGIONAL_LEGAL
TRACEABILITY_POLICY_TRACE = task1_compliance.TRACEABILITY_POLICY_TRACE
TRACEABILITY_AMBIGUITY = task1_compliance.TRACEABILITY_AMBIGUITY


def _result_by_sku(result: object, sku: str) -> object:
    for item in result.compliance_results:
        if item.sku == sku:
            return item
    raise AssertionError(f"SKU not found in compliance results: {sku}")


def test_task1_includes_eligible_candidates_and_traceability() -> None:
    request = PreprocessRequest(
        tire_size="225/70R19.5",
        min_load_index=120,
        min_speed_rating="K",
        application="Regional delivery",
        region_code="TX",
        required_certifications=["US-DOT"],
    )

    result = preprocess_candidates_with_compliance(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        request,
        policy_version="policy-2026.06",
    )

    assert "MIC-XZE2-225-70R19.5-128" in result.eligible_skus

    mic = _result_by_sku(result, "MIC-XZE2-225-70R19.5-128")
    assert mic.eligible is True
    assert mic.policy_version == "policy-2026.06"
    assert mic.evaluated_at_utc
    assert TRACEABILITY_SIZE_AND_RATING in mic.traceability_refs
    assert TRACEABILITY_REGIONAL_LEGAL in mic.traceability_refs
    assert TRACEABILITY_POLICY_TRACE in mic.traceability_refs


def test_task1_marks_legal_or_certification_failures_as_ineligible() -> None:
    request = PreprocessRequest(
        tire_size="295/75R22.5",
        min_load_index=140,
        min_speed_rating="L",
        application="Long-haul",
        region_code="TX",
        required_certifications=["US-DOT", "NON-EXISTENT-CERT"],
    )

    result = preprocess_candidates_with_compliance(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        request,
        policy_version="policy-2026.06",
    )

    gdl = _result_by_sku(result, "GDL-RHG2-295-75R22.5-144")
    assert gdl.eligible is False
    assert "region_code" in gdl.failed_rules or "certifications" in gdl.failed_rules


def test_task1_escalates_ambiguous_policy_conflict_and_blocks_auto_recommendation() -> None:
    request = PreprocessRequest(
        tire_size="225/70R19.5",
        min_load_index=120,
        min_speed_rating="K",
        application="Regional delivery",
        region_code="TX",
        required_certifications=["US-DOT"],
        company_policy_region_allowlist=["CA"],
    )

    result = preprocess_candidates_with_compliance(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        request,
        policy_version="policy-2026.06",
    )

    mic = _result_by_sku(result, "MIC-XZE2-225-70R19.5-128")
    assert mic.requires_human_review is True
    assert mic.eligible is False
    assert "policy_precedence" in mic.failed_rules
    assert TRACEABILITY_AMBIGUITY in mic.traceability_refs
    assert result.auto_recommendation_blocked is True