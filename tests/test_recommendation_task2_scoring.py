from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK1_MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task1_compliance.py"
TASK2_MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task2_recommendation.py"
COMPLIANCE_DB_PATH = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
SUPPLIERS_DB_PATH = REPO_ROOT / "subsystem" / "supplier-database" / "mock" / "suppliers-db.json"


task1_spec = importlib.util.spec_from_file_location("task1_compliance", TASK1_MODULE_PATH)
task1_compliance = importlib.util.module_from_spec(task1_spec)
assert task1_spec is not None and task1_spec.loader is not None
sys.modules[task1_spec.name] = task1_compliance
task1_spec.loader.exec_module(task1_compliance)

task2_spec = importlib.util.spec_from_file_location("task2_recommendation", TASK2_MODULE_PATH)
task2_recommendation = importlib.util.module_from_spec(task2_spec)
assert task2_spec is not None and task2_spec.loader is not None
sys.modules[task2_spec.name] = task2_recommendation
task2_spec.loader.exec_module(task2_recommendation)

PreprocessRequest = task1_compliance.PreprocessRequest
preprocess_candidates_with_compliance = task1_compliance.preprocess_candidates_with_compliance

ScoringRequest = task2_recommendation.ScoringRequest
rank_compliant_candidates = task2_recommendation.rank_compliant_candidates


def _write_json(path: Path, payload: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f)


def _temp_supplier_payload() -> list[dict]:
    return [
        {
            "id": "supplier-1",
            "name": "Supplier One",
            "preferred": True,
            "contracts": [
                {
                    "contract_id": "c1",
                    "sku": "SKU-FAST",
                    "manufacturer": "Maker",
                    "unit_price": 400.0,
                    "available_quantity": 120,
                    "lead_time_days": 3,
                    "expiration_date": "2026-12-31",
                },
                {
                    "contract_id": "c2",
                    "sku": "SKU-SLOW",
                    "manufacturer": "Maker",
                    "unit_price": 390.0,
                    "available_quantity": 120,
                    "lead_time_days": 20,
                    "expiration_date": "2026-12-31",
                },
            ],
        }
    ]


def _temp_compliance_payload() -> list[dict]:
    return [
        {
            "sku": "SKU-FAST",
            "manufacturer": "Maker",
            "tire_size": "295/75R22.5",
            "load_index": 144,
            "speed_rating": "L",
            "application": "Long-haul",
            "estimated_mileage": 120000,
            "certifications": ["US-DOT", "EPA-SmartWay"],
            "region_codes": ["TX"],
            "warranty_quality": 0.8,
        },
        {
            "sku": "SKU-SLOW",
            "manufacturer": "Maker",
            "tire_size": "295/75R22.5",
            "load_index": 144,
            "speed_rating": "L",
            "application": "Long-haul",
            "estimated_mileage": 120000,
            "certifications": ["US-DOT", "EPA-SmartWay"],
            "region_codes": ["TX"],
            "warranty_quality": 0.8,
        },
    ]


def test_task2_excludes_non_compliant_items_from_scoring() -> None:
    preprocess_result = preprocess_candidates_with_compliance(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        PreprocessRequest(
            tire_size="225/70R19.5",
            min_load_index=120,
            min_speed_rating="K",
            application="Regional delivery",
            region_code="TX",
            required_certifications=["US-DOT"],
        ),
        policy_version="policy-2026.06",
    )

    result = rank_compliant_candidates(
        preprocess_result,
        SUPPLIERS_DB_PATH,
        COMPLIANCE_DB_PATH,
        ScoringRequest(quantity_needed=24, replacement_urgency="medium"),
    )

    ranked_skus = [item.sku for item in result.ranked_candidates]
    assert "MIC-XZE2-225-70R19.5-128" in ranked_skus
    assert "GDL-RHG2-295-75R22.5-144" not in ranked_skus


def test_task2_returns_weighted_component_score_breakdown() -> None:
    preprocess_result = preprocess_candidates_with_compliance(
        COMPLIANCE_DB_PATH,
        SUPPLIERS_DB_PATH,
        PreprocessRequest(
            tire_size="225/70R19.5",
            min_load_index=120,
            min_speed_rating="K",
            application="Regional delivery",
            region_code="TX",
            required_certifications=["US-DOT"],
        ),
        policy_version="policy-2026.06",
    )

    result = rank_compliant_candidates(
        preprocess_result,
        SUPPLIERS_DB_PATH,
        COMPLIANCE_DB_PATH,
        ScoringRequest(quantity_needed=24, replacement_urgency="medium"),
    )

    assert result.ranked_candidates
    top = result.ranked_candidates[0]
    assert "availability" in top.component_scores
    assert "lifecycle_cost" in top.component_scores
    assert "fuel_impact" in top.component_scores
    assert "warranty_quality" in top.component_scores
    assert top.total_score >= 0.0


def test_task2_prefers_fulfillable_option_within_urgency_constraints(tmp_path: Path) -> None:
    suppliers_path = tmp_path / "suppliers.json"
    compliance_path = tmp_path / "compliance.json"
    _write_json(suppliers_path, _temp_supplier_payload())
    _write_json(compliance_path, _temp_compliance_payload())

    class _SimpleItem:
        def __init__(self, sku: str, eligible: bool) -> None:
            self.sku = sku
            self.eligible = eligible

    class _SimplePreprocess:
        def __init__(self) -> None:
            self.compliance_results = [
                _SimpleItem("SKU-FAST", True),
                _SimpleItem("SKU-SLOW", True),
            ]

    result = rank_compliant_candidates(
        _SimplePreprocess(),
        suppliers_path,
        compliance_path,
        ScoringRequest(quantity_needed=100, replacement_urgency="high"),
    )

    ranked_skus = [item.sku for item in result.ranked_candidates]
    assert ranked_skus[0] == "SKU-FAST"
    assert "fulfillable" in result.ranked_candidates[0].fulfillment_rationale


def test_task2_tie_breaking_is_deterministic_across_runs(tmp_path: Path) -> None:
    suppliers_path = tmp_path / "suppliers.json"
    compliance_path = tmp_path / "compliance.json"
    _write_json(
        suppliers_path,
        [
            {
                "id": "supplier-1",
                "name": "Supplier One",
                "preferred": True,
                "contracts": [
                    {
                        "contract_id": "c1",
                        "sku": "AAA-SKU",
                        "manufacturer": "Maker",
                        "unit_price": 350.0,
                        "available_quantity": 50,
                        "lead_time_days": 7,
                        "expiration_date": "2026-12-31",
                    },
                    {
                        "contract_id": "c2",
                        "sku": "BBB-SKU",
                        "manufacturer": "Maker",
                        "unit_price": 350.0,
                        "available_quantity": 50,
                        "lead_time_days": 7,
                        "expiration_date": "2026-12-31",
                    },
                ],
            }
        ],
    )
    _write_json(
        compliance_path,
        [
            {
                "sku": "AAA-SKU",
                "tire_size": "295/75R22.5",
                "load_index": 144,
                "speed_rating": "L",
                "application": "Long-haul",
                "estimated_mileage": 100000,
                "certifications": ["US-DOT"],
                "region_codes": ["TX"],
            },
            {
                "sku": "BBB-SKU",
                "tire_size": "295/75R22.5",
                "load_index": 144,
                "speed_rating": "L",
                "application": "Long-haul",
                "estimated_mileage": 100000,
                "certifications": ["US-DOT"],
                "region_codes": ["TX"],
            },
        ],
    )

    class _SimpleItem:
        def __init__(self, sku: str, eligible: bool) -> None:
            self.sku = sku
            self.eligible = eligible

    class _SimplePreprocess:
        def __init__(self) -> None:
            self.compliance_results = [
                _SimpleItem("AAA-SKU", True),
                _SimpleItem("BBB-SKU", True),
            ]

    request = ScoringRequest(quantity_needed=20, replacement_urgency="medium")
    first = rank_compliant_candidates(_SimplePreprocess(), suppliers_path, compliance_path, request)
    second = rank_compliant_candidates(_SimplePreprocess(), suppliers_path, compliance_path, request)

    first_order = [item.sku for item in first.ranked_candidates]
    second_order = [item.sku for item in second.ranked_candidates]

    assert first_order == second_order
    assert first_order == ["AAA-SKU", "BBB-SKU"]