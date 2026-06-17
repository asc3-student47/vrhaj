from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "run_recommendation_pipeline.py"


spec = importlib.util.spec_from_file_location("run_recommendation_pipeline", MODULE_PATH)
pipeline = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
sys.modules[spec.name] = pipeline
spec.loader.exec_module(pipeline)


@dataclass(frozen=True)
class _FakeSearchRequest:
    tire_size: str
    load_index: int
    speed_rating: str
    region_code: str
    quantity_needed: int
    replacement_urgency: str
    include_compliance_summary: bool = False
    required_certifications: list[str] | None = None
    application: str | None = None


class _FakeTask3ValidationError:
    SearchRequest = _FakeSearchRequest

    @staticmethod
    def search_inventory(*args: object, **kwargs: object) -> dict[str, object]:
        from pydantic import BaseModel

        class _InvalidModel(BaseModel):
            quantity: int

        _InvalidModel.model_validate({"quantity": "not-an-int"})
        return {}


class _FakeTask3BadResponse:
    SearchRequest = _FakeSearchRequest

    @staticmethod
    def search_inventory(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "status": "no_match",
            "decision": "deny",
            # Missing required fields by design to trigger schema validation.
        }


class _FakeSupplier:
    class SupplierLookupRequest:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    @staticmethod
    def evaluate_request(*args: object, **kwargs: object) -> list[object]:
        return []


class _FakeTask3Counter:
    SearchRequest = _FakeSearchRequest
    call_count = 0

    @classmethod
    def search_inventory(cls, *args: object, **kwargs: object) -> dict[str, object]:
        cls.call_count += 1
        raise AssertionError("task3.search_inventory should not be called when validation fails")


class _FakeTask3NoMatch:
    SearchRequest = _FakeSearchRequest
    last_request: _FakeSearchRequest | None = None

    @classmethod
    def search_inventory(cls, *args: object, **kwargs: object) -> dict[str, object]:
        cls.last_request = args[2]
        request = args[2]
        return {
            "status": "no_match",
            "decision": "deny",
            "rationale": "no candidates",
            "evidence": [
                {
                    "source": "validation",
                    "detail": "test payload",
                }
            ],
            "request": {
                "tire_size": request.tire_size,
                "load_index": request.load_index,
                "speed_rating": request.speed_rating,
                "region_code": request.region_code,
                "quantity_needed": request.quantity_needed,
            },
            "reason_codes": ["NO_COMPLIANT_CANDIDATES"],
            "suggested_relaxations": [],
            "traceability_refs": ["test"],
        }


def _resolved_request() -> dict[str, object]:
    return {
        "sku": None,
        "tire_size": "225/70R19.5",
        "load_index": 120,
        "speed_rating": "K",
        "region_code": "TX",
        "quantity_needed": 24,
        "replacement_urgency": "medium",
        "application": "Regional delivery",
        "required_certifications": ["US-DOT"],
        "include_compliance_summary": False,
    }


def test_pipeline_catches_task3_validation_error_and_returns_structured_payload(monkeypatch: object) -> None:
    args = pipeline.build_runtime_args(prompt="dummy")
    monkeypatch.setattr(pipeline, "_resolve_with_pydantic_agent", lambda _args: _resolved_request())

    code, payload = pipeline.process_prompt_with_runtime(
        "dummy",
        args=args,
        task3_module=_FakeTask3ValidationError(),
        supplier_module=_FakeSupplier(),
        source="test",
    )

    assert code != 0
    assert payload is not None
    assert payload["error"] == "schema_validation_error"
    assert payload["source"] == "task3_processing"
    assert payload["details"]


def test_pipeline_catches_response_schema_validation_error_and_returns_structured_payload(monkeypatch: object) -> None:
    args = pipeline.build_runtime_args(prompt="dummy")
    monkeypatch.setattr(pipeline, "_resolve_with_pydantic_agent", lambda _args: _resolved_request())

    code, payload = pipeline.process_prompt_with_runtime(
        "dummy",
        args=args,
        task3_module=_FakeTask3BadResponse(),
        supplier_module=_FakeSupplier(),
        source="test",
    )

    assert code != 0
    assert payload is not None
    assert payload["error"] == "schema_validation_error"
    assert payload["source"] == "task3_response_schema"
    assert payload["details"]


def test_pipeline_rejects_missing_tire_quantity_and_sku_without_calling_task3(monkeypatch: object) -> None:
    args = pipeline.build_runtime_args(prompt="dummy")
    _FakeTask3Counter.call_count = 0

    monkeypatch.setattr(
        pipeline,
        "_resolve_with_pydantic_agent",
        lambda _args: {
            "sku": None,
            "tire_size": None,
            "load_index": 120,
            "speed_rating": "K",
            "region_code": "TX",
            "quantity_needed": None,
            "replacement_urgency": "medium",
            "application": "Regional delivery",
            "required_certifications": ["US-DOT"],
            "include_compliance_summary": False,
        },
    )

    code, payload = pipeline.process_prompt_with_runtime(
        "dummy",
        args=args,
        task3_module=_FakeTask3Counter,
        supplier_module=_FakeSupplier(),
        source="test",
    )

    assert code != 0
    assert payload is not None
    assert payload["error"] == "invalid_request"
    assert payload["reason"] == "missing_conditional_fields"
    assert _FakeTask3Counter.call_count == 0


def test_pipeline_rejects_invalid_sku_when_size_quantity_missing(monkeypatch: object) -> None:
    args = pipeline.build_runtime_args(prompt="dummy")

    monkeypatch.setattr(
        pipeline,
        "_resolve_with_pydantic_agent",
        lambda _args: {
            "sku": "NOT-A-SKU",
            "tire_size": None,
            "load_index": 120,
            "speed_rating": "K",
            "region_code": "TX",
            "quantity_needed": None,
            "replacement_urgency": "medium",
            "application": "Regional delivery",
            "required_certifications": ["US-DOT"],
            "include_compliance_summary": False,
        },
    )

    code, payload = pipeline.process_prompt_with_runtime(
        "dummy",
        args=args,
        task3_module=_FakeTask3Counter,
        supplier_module=_FakeSupplier(),
        source="test",
    )

    assert code != 0
    assert payload is not None
    assert payload["error"] == "invalid_request"
    assert payload["reason"] == "search_cannot_take_place_since_input_could_not_be_validated"
    assert payload["details"]["invalid_sku"] == "NOT-A-SKU"


def test_pipeline_rejects_invalid_sku_even_with_tire_quantity(monkeypatch: object) -> None:
    args = pipeline.build_runtime_args(prompt="dummy")

    monkeypatch.setattr(
        pipeline,
        "_resolve_with_pydantic_agent",
        lambda _args: {
            "sku": "NOT-A-SKU",
            "tire_size": "225/70R19.5",
            "load_index": 120,
            "speed_rating": "K",
            "region_code": "TX",
            "quantity_needed": 24,
            "replacement_urgency": "medium",
            "application": "Regional delivery",
            "required_certifications": ["US-DOT"],
            "include_compliance_summary": False,
        },
    )

    code, payload = pipeline.process_prompt_with_runtime(
        "dummy",
        args=args,
        task3_module=_FakeTask3Counter,
        supplier_module=_FakeSupplier(),
        source="test",
    )

    assert code != 0
    assert payload is not None
    assert payload["error"] == "invalid_request"
    assert payload["reason"] == "invalid_sku"


def test_pipeline_allows_valid_sku_without_tire_size_and_quantity(monkeypatch: object) -> None:
    args = pipeline.build_runtime_args(prompt="dummy")
    _FakeTask3NoMatch.last_request = None

    monkeypatch.setattr(
        pipeline,
        "_resolve_with_pydantic_agent",
        lambda _args: {
            "sku": "MIC-XZE2-225-70R19.5-128",
            "tire_size": None,
            "load_index": 120,
            "speed_rating": "K",
            "region_code": "TX",
            "quantity_needed": None,
            "replacement_urgency": "medium",
            "application": "Regional delivery",
            "required_certifications": ["US-DOT"],
            "include_compliance_summary": False,
        },
    )

    code, payload = pipeline.process_prompt_with_runtime(
        "dummy",
        args=args,
        task3_module=_FakeTask3NoMatch,
        supplier_module=_FakeSupplier(),
        source="test",
    )

    assert code == 0
    assert payload is not None
    assert payload["response"]["status"] == "no_match"
    assert payload["resolved_request"]["sku"] == "MIC-XZE2-225-70R19.5-128"
    assert payload["resolved_request"]["tire_size"] == "225/70R19.5"
    assert payload["resolved_request"]["quantity_needed"] == 1
