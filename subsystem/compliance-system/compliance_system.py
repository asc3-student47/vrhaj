from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any


SPEED_RATING_ORDER = {
    "J": 1,
    "K": 2,
    "L": 3,
    "M": 4,
    "N": 5,
    "P": 6,
    "Q": 7,
    "R": 8,
    "S": 9,
    "T": 10,
    "U": 11,
    "H": 12,
    "V": 13,
    "W": 14,
    "Y": 15,
}

REMOVED_ATTRIBUTES = {"unit_price_usd"}


@dataclass(frozen=True)
class ComplianceRequest:
    sku: str | None = None
    tire_size: str | None = None
    min_load_index: int | None = None
    min_speed_rating: str | None = None
    application: str | None = None
    region_code: str | None = None
    required_certifications: list[str] | None = None


@dataclass(frozen=True)
class RuleResult:
    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class ComplianceResult:
    sku: str | None
    status: str
    reasons: list[str]
    failed_rules: list[str]
    rule_results: list[RuleResult]


def load_tire_specifications(db_path: str | Path) -> list[dict[str, Any]]:
    """Load mock tire records from JSON file and validate basic structure."""
    path = Path(db_path)
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list):
        raise ValueError("Mock compliance database must be a JSON array of records")

    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("Each tire record must be a JSON object")

        normalized = dict(item)
        for attr in REMOVED_ATTRIBUTES:
            normalized.pop(attr, None)

        records.append(normalized)

    return records


def lookup_tire_records(
    records: list[dict[str, Any]], request: ComplianceRequest
) -> list[dict[str, Any]]:
    """Lookup records by SKU when provided, otherwise by fitment attributes."""
    if request.sku:
        matched = [r for r in records if str(r.get("sku", "")).upper() == request.sku.upper()]
        return matched

    matched = records
    if request.tire_size:
        matched = [r for r in matched if str(r.get("tire_size", "")).lower() == request.tire_size.lower()]
    if request.application:
        matched = [r for r in matched if str(r.get("application", "")).lower() == request.application.lower()]

    return matched


def evaluate_tire_record(record: dict[str, Any], request: ComplianceRequest) -> ComplianceResult:
    """Evaluate one tire record against request-fit rules."""
    rule_results: list[RuleResult] = []

    if request.tire_size:
        passed = str(record.get("tire_size", "")).lower() == request.tire_size.lower()
        reason = "tire_size matched" if passed else "tire_size mismatch"
        rule_results.append(RuleResult(name="tire_size", passed=passed, reason=reason))

    if request.min_load_index is not None:
        load_index = int(record.get("load_index", -1))
        passed = load_index >= request.min_load_index
        reason = "load_index meets minimum" if passed else "load_index below minimum"
        rule_results.append(RuleResult(name="load_index", passed=passed, reason=reason))

    if request.min_speed_rating:
        record_rating = str(record.get("speed_rating", "")).upper()
        required_rating = request.min_speed_rating.upper()
        passed = SPEED_RATING_ORDER.get(record_rating, 0) >= SPEED_RATING_ORDER.get(required_rating, 0)
        reason = "speed_rating meets minimum" if passed else "speed_rating below minimum"
        rule_results.append(RuleResult(name="speed_rating", passed=passed, reason=reason))

    if request.application:
        passed = str(record.get("application", "")).lower() == request.application.lower()
        reason = "application matched" if passed else "application mismatch"
        rule_results.append(RuleResult(name="application", passed=passed, reason=reason))

    if request.region_code:
        regions = [str(x).upper() for x in record.get("region_codes", [])]
        passed = request.region_code.upper() in regions
        reason = "region supported" if passed else "region not supported"
        rule_results.append(RuleResult(name="region_code", passed=passed, reason=reason))

    required_certs = request.required_certifications or []
    if required_certs:
        certs = {str(x).upper() for x in record.get("certifications", [])}
        needed = {c.upper() for c in required_certs}
        missing = sorted(needed - certs)
        passed = not missing
        reason = "all required certifications present" if passed else f"missing certifications: {', '.join(missing)}"
        rule_results.append(RuleResult(name="certifications", passed=passed, reason=reason))

    failed_rules = [r.name for r in rule_results if not r.passed]
    status = "compliant" if not failed_rules else "non_compliant"
    reasons = [r.reason for r in rule_results]

    return ComplianceResult(
        sku=str(record.get("sku")) if record.get("sku") is not None else None,
        status=status,
        reasons=reasons,
        failed_rules=failed_rules,
        rule_results=rule_results,
    )


def evaluate_request(
    db_path: str | Path,
    request: ComplianceRequest,
) -> list[ComplianceResult]:
    """Lookup candidate tires and return structured compliance outcomes."""
    records = load_tire_specifications(db_path)
    candidates = lookup_tire_records(records, request)

    if not candidates:
        return [
            ComplianceResult(
                sku=request.sku,
                status="non_compliant",
                reasons=["no tire specification found for lookup keys"],
                failed_rules=["lookup"],
                rule_results=[
                    RuleResult(
                        name="lookup",
                        passed=False,
                        reason="no tire specification found for lookup keys",
                    )
                ],
            )
        ]

    return [evaluate_tire_record(record, request) for record in candidates]
