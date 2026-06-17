from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "subsystem" / "compliance-system" / "compliance_system.py"
DB_PATH = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"


spec = importlib.util.spec_from_file_location("compliance_system", MODULE_PATH)
compliance_system = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = compliance_system
spec.loader.exec_module(compliance_system)

ComplianceRequest = compliance_system.ComplianceRequest
evaluate_request = compliance_system.evaluate_request


def test_compliant_by_sku_and_rules() -> None:
    request = ComplianceRequest(
        sku="MIC-XZE2-225-70R19.5-128",
        tire_size="225/70R19.5",
        min_load_index=120,
        min_speed_rating="K",
        application="Regional delivery",
        region_code="TX",
        required_certifications=["US-DOT"],
    )

    results = evaluate_request(DB_PATH, request)

    assert len(results) == 1
    assert results[0].status == "compliant"
    assert results[0].failed_rules == []


def test_non_compliant_for_region_and_application() -> None:
    request = ComplianceRequest(
        sku="GDL-RHG2-295-75R22.5-144",
        application="Regional delivery",
        region_code="TX",
    )

    results = evaluate_request(DB_PATH, request)

    assert len(results) == 1
    assert results[0].status == "non_compliant"
    assert "application" in results[0].failed_rules
    assert "region_code" in results[0].failed_rules


def test_non_compliant_when_lookup_not_found() -> None:
    request = ComplianceRequest(sku="DOES-NOT-EXIST")

    results = evaluate_request(DB_PATH, request)

    assert len(results) == 1
    assert results[0].status == "non_compliant"
    assert results[0].failed_rules == ["lookup"]
