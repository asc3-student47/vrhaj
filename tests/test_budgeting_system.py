from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "subsystem" / "budgeting-system" / "budgeting_system.py"
DB_PATH = REPO_ROOT / "subsystem" / "budgeting-system" / "mock" / "budgets-db.json"


spec = importlib.util.spec_from_file_location("budgeting_system", MODULE_PATH)
budgeting_system = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = budgeting_system
spec.loader.exec_module(budgeting_system)

BudgetLookupRequest = budgeting_system.BudgetLookupRequest
evaluate_request = budgeting_system.evaluate_request
load_budget_record = budgeting_system.load_budget_record


def test_deny_when_total_cost_missing() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026")

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes == ["invalid_cost_input"]


def test_deny_when_total_cost_non_numeric() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026", total_cost="abc")

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes == ["invalid_cost_input"]


def test_deny_when_total_cost_non_positive() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026", total_cost=0)

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes == ["invalid_cost_input"]


def test_deny_when_unit_cost_payload_present() -> None:
    request = BudgetLookupRequest(
        contract_id="MIC-XZE2-2026",
        total_cost=100,
        unit_cost=50,
    )

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes == ["invalid_cost_input"]


def test_deny_when_count_payload_present() -> None:
    request = BudgetLookupRequest(
        contract_id="MIC-XZE2-2026",
        total_cost=100,
        count=2,
    )

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes == ["invalid_cost_input"]


def test_allow_when_total_cost_below_remaining() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026", total_cost=500)

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "allow"
    assert result.reason_codes == []
    assert result.contract_id == "MIC-XZE2-2026"
    assert result.total_cost == 500.0
    assert result.cost_center_id == "CC-001"


def test_allow_when_total_cost_equals_remaining() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026", total_cost=312450)

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "allow"
    assert result.reason_codes == []


def test_deny_when_total_cost_exceeds_remaining() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026", total_cost=312450.01)

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes == ["insufficient_budget"]


def test_deny_always_includes_reason_codes() -> None:
    request = BudgetLookupRequest(contract_id="MIC-XZE2-2026", total_cost=-1)

    result = evaluate_request(DB_PATH, request)

    assert result.response_code == "deny"
    assert result.reason_codes


def test_loader_rejects_multiple_cost_centers(tmp_path: Path) -> None:
    db_path = tmp_path / "budgets-db.json"
    db_path.write_text(
        json.dumps(
            [
                {
                    "cost_center_id": "CC-001",
                    "name": "Fleet Maintenance",
                    "allocated": 10,
                    "remaining": 5,
                },
                {
                    "cost_center_id": "CC-002",
                    "name": "Extra",
                    "allocated": 10,
                    "remaining": 5,
                },
            ]
        ),
        encoding="utf-8",
    )

    try:
        load_budget_record(db_path)
        assert False, "Expected ValueError for multiple cost centers"
    except ValueError as exc:
        assert "exactly one cost center" in str(exc)
