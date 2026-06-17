from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task3_procurement_handoff.py"
COMPLIANCE_DB_PATH = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
SUPPLIERS_DB_PATH = REPO_ROOT / "subsystem" / "supplier-database" / "mock" / "suppliers-db.json"


spec = importlib.util.spec_from_file_location("task3_procurement_handoff", MODULE_PATH)
task3 = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = task3
spec.loader.exec_module(task3)

SearchRequest = task3.SearchRequest
search_inventory = task3.search_inventory


def test_task4_e2e_pipeline_compliance_to_handoff() -> None:
    response = search_inventory(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        SearchRequest(
            tire_size="225/70R19.5",
            load_index=120,
            speed_rating="K",
            region_code="TX",
            quantity_needed=24,
            replacement_urgency="medium",
            include_compliance_summary=True,
            required_certifications=["US-DOT"],
            application="Regional delivery",
        ),
        policy_version="policy-2026.06",
    )

    assert response["status"] == "match"
    assert response["results"]
    ranked_skus = [item["sku"] for item in response["results"]]

    # GDL SKU is non-compliant for this request and must not survive
    # compliance gating into ranked handoff outputs.
    assert "GDL-RHG2-295-75R22.5-144" not in ranked_skus
    assert "MIC-XZE2-225-70R19.5-128" in ranked_skus

    first = response["results"][0]
    assert first["compliance_status"] == "compliant"
    assert "fulfillment_rationale" in first
    assert "compliance_summary" in first
    assert first["compliance_summary"]["failed_rules"] == []


def test_task4_scope_boundaries_no_po_submission_or_route_optimization() -> None:
    response = search_inventory(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        SearchRequest(
            tire_size="225/70R19.5",
            load_index=120,
            speed_rating="K",
            region_code="TX",
            quantity_needed=24,
            replacement_urgency="medium",
            include_compliance_summary=False,
            required_certifications=["US-DOT"],
            application="Regional delivery",
        ),
        policy_version="policy-2026.06",
    )

    assert response["status"] == "match"

    # v1 boundaries: recommendation only, no autonomous procurement action.
    assert "purchase_order" not in response
    assert "po_submission" not in response
    assert "autonomous_execution" not in response

    # v1 boundaries: no route optimization workflow output.
    assert "route_optimization" not in response
    assert "optimized_route" not in response
