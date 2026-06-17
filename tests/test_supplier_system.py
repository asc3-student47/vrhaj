from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "subsystem" / "supplier-system" / "supplier_system.py"
DB_PATH = REPO_ROOT / "subsystem" / "supplier-system" / "mock" / "suppliers-db.json"


spec = importlib.util.spec_from_file_location("supplier_system", MODULE_PATH)
supplier_system = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = supplier_system
spec.loader.exec_module(supplier_system)

SupplierLookupRequest = supplier_system.SupplierLookupRequest
evaluate_request = supplier_system.evaluate_request


def test_eligible_matches_preferred_first() -> None:
    request = SupplierLookupRequest(
        sku="MIC-XZE2-225-70R19.5-128",
        requested_quantity=500,
        max_lead_time_days=14,
    )

    results = evaluate_request(DB_PATH, request, evaluation_date=date(2026, 6, 17))

    assert len(results) == 3
    assert results[0].status == "eligible"
    assert results[0].preferred is True
    assert results[0].supplier_name == "Michelin"
    assert results[1].status == "eligible"
    assert results[1].preferred is False
    assert results[1].supplier_name == "NeedForSpeed Tires"
    assert results[2].status == "ineligible"
    assert "contract_active" in results[2].failed_rules


def test_exclusion_paths_expired_quantity_and_lead_time() -> None:
    request = SupplierLookupRequest(
        sku="MIC-XZE2-225-70R19.5-128",
        requested_quantity=900,
        max_lead_time_days=10,
    )

    results = evaluate_request(DB_PATH, request, evaluation_date=date(2026, 6, 17))

    assert len(results) == 3
    # Michelin 2025 contract is expired and also fails quantity and lead-time checks.
    expired = [
        r
        for r in results
        if r.contract_id == "MIC-XZE2-2025"
    ][0]
    assert expired.status == "ineligible"
    assert "contract_active" in expired.failed_rules
    assert "available_quantity" in expired.failed_rules
    assert "lead_time_days" in expired.failed_rules

    # NeedForSpeed contract is active but fails quantity and lead-time checks.
    nfs = [r for r in results if r.supplier_name == "NeedForSpeed Tires"][0]
    assert nfs.status == "ineligible"
    assert "contract_active" not in nfs.failed_rules
    assert "available_quantity" in nfs.failed_rules
    assert "lead_time_days" in nfs.failed_rules


def test_no_match_when_requested_sku_not_found() -> None:
    request = SupplierLookupRequest(
        sku="DOES-NOT-EXIST",
        requested_quantity=100,
        max_lead_time_days=30,
    )

    results = evaluate_request(DB_PATH, request, evaluation_date=date(2026, 6, 17))

    assert len(results) == 1
    assert results[0].status == "ineligible"
    assert results[0].failed_rules == ["lookup"]
