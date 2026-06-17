from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task3_procurement_handoff.py"
COMPLIANCE_DB_PATH = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
SUPPLIERS_DB_PATH = REPO_ROOT / "subsystem" / "supplier-system" / "mock" / "suppliers-db.json"


spec = importlib.util.spec_from_file_location("task3_procurement_handoff", MODULE_PATH)
task3 = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = task3
spec.loader.exec_module(task3)

SearchRequest = task3.SearchRequest
search_inventory = task3.search_inventory


def _write_json(path: Path, payload: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)


def test_task3_default_response_omits_verbose_compliance_details() -> None:
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
    assert response["results"]
    first = response["results"][0]
    assert "compliance_status" in first
    assert "compliance_summary" not in first
    assert "stock_qty" in first
    assert "lead_time_days" in first


def test_task3_verbose_response_includes_compliance_summary() -> None:
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
    first = response["results"][0]
    assert "compliance_summary" in first
    assert "policy_version" in first["compliance_summary"]
    assert "evaluated_at_utc" in first["compliance_summary"]


def test_task3_deterministic_ranking_order_on_repeated_runs() -> None:
    request = SearchRequest(
        tire_size="225/70R19.5",
        load_index=120,
        speed_rating="K",
        region_code="TX",
        quantity_needed=24,
        replacement_urgency="medium",
        include_compliance_summary=False,
        required_certifications=["US-DOT"],
        application="Regional delivery",
    )

    first = search_inventory(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        request,
        policy_version="policy-2026.06",
    )
    second = search_inventory(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        request,
        policy_version="policy-2026.06",
    )

    assert first["status"] == "match"
    assert second["status"] == "match"

    first_order = [item["sku"] for item in first["results"]]
    second_order = [item["sku"] for item in second["results"]]
    assert first_order == second_order


def test_task3_returns_explicit_no_match_with_reason_codes(tmp_path: Path) -> None:
    suppliers_path = tmp_path / "suppliers.json"
    compliance_path = tmp_path / "compliance.json"

    _write_json(
        suppliers_path,
        [
            {
                "id": "s1",
                "name": "Supplier One",
                "contracts": [
                    {
                        "contract_id": "c1",
                        "sku": "SKU-A",
                        "unit_price": 320.0,
                        "available_quantity": 10,
                        "lead_time_days": 14,
                    }
                ],
            }
        ],
    )

    _write_json(
        compliance_path,
        [
            {
                "sku": "SKU-A",
                "tire_size": "225/70R19.5",
                "load_index": 128,
                "speed_rating": "L",
                "application": "Regional delivery",
                "estimated_mileage": 100000,
                "certifications": ["US-DOT"],
                "region_codes": ["TX"],
            }
        ],
    )

    response = search_inventory(
        compliance_path,
        suppliers_path,
        SearchRequest(
            tire_size="225/70R19.5",
            load_index=120,
            speed_rating="K",
            region_code="TX",
            quantity_needed=500,
            replacement_urgency="high",
            include_compliance_summary=False,
            required_certifications=["US-DOT"],
            application="Regional delivery",
        ),
        policy_version="policy-2026.06",
    )

    assert response["status"] == "no_match"
    assert "reason_codes" in response
    assert "INSUFFICIENT_AVAILABILITY" in response["reason_codes"]
    assert "suggested_relaxations" in response


def test_task3_fast_path_refusal_returns_structured_out_of_policy_payload() -> None:
    response = search_inventory(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        SearchRequest(
            tire_size="225/70R19.5",
            load_index=120,
            speed_rating="K",
            region_code="TX",
            quantity_needed=2501,
            replacement_urgency="medium",
            include_compliance_summary=False,
            required_certifications=["US-DOT"],
            application="Regional delivery",
        ),
        policy_version="policy-2026.06",
    )

    assert response["status"] == "no_match"
    assert response["decision"] == "deny"
    assert "OUT_OF_POLICY_REFUSAL" in response["reason_codes"]
    assert "results" not in response
    assert response["evidence"]
    assert response["traceability_refs"]


def test_task3_fast_path_refusal_skips_preprocess_and_ranking(monkeypatch: object) -> None:
    def _fail_preprocess(*args: object, **kwargs: object) -> object:
        raise AssertionError("preprocess should not run for out-of-policy refusal")

    def _fail_rank(*args: object, **kwargs: object) -> object:
        raise AssertionError("ranking should not run for out-of-policy refusal")

    monkeypatch.setattr(task3, "preprocess_candidates_with_compliance", _fail_preprocess)
    monkeypatch.setattr(task3, "rank_compliant_candidates", _fail_rank)

    response = search_inventory(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        SearchRequest(
            tire_size="225/70R19.5",
            load_index=120,
            speed_rating="K",
            region_code="TX",
            quantity_needed=2501,
            replacement_urgency="medium",
            include_compliance_summary=False,
            required_certifications=["US-DOT"],
            application="Regional delivery",
        ),
        policy_version="policy-2026.06",
    )

    assert response["status"] == "no_match"
    assert "OUT_OF_POLICY_REFUSAL" in response["reason_codes"]