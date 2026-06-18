from __future__ import annotations

import argparse
from datetime import date, datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, TypeAdapter, ValidationError
from dotenv import load_dotenv


load_dotenv()


REPO_ROOT = Path(__file__).resolve().parent
TASK3_MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task3_procurement_handoff.py"
SUPPLIER_MODULE_PATH = REPO_ROOT / "subsystem" / "supplier-system" / "supplier_system.py"
DEFAULT_COMPLIANCE_DB = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
DEFAULT_SUPPLIERS_DB = REPO_ROOT / "subsystem" / "supplier-system" / "mock" / "suppliers-db.json"
DEFAULT_AGENT_MODEL = os.getenv("PROCUREMENT_AGENT_MODEL", "openai-chat:gpt-4o-mini")


def _console_log(event: str, **fields: object) -> None:
    timestamp = datetime.now().astimezone().isoformat()
    payload = {"event": event, "ts": timestamp, **fields}
    print(f"[agent-log] {json.dumps(payload, sort_keys=True)}")


def _console_tool_log(
    *,
    event: str,
    source: str,
    run_id: str,
    tool_name: str,
    elapsed_ms: float | None = None,
    **fields: object,
) -> None:
    payload: dict[str, object] = {
        "source": source,
        "run_id": run_id,
        "tool_name": tool_name,
    }
    if elapsed_ms is not None:
        payload["elapsed_ms"] = elapsed_ms
    payload.update(fields)
    _console_log(event, **payload)


class ResolvedRequest(BaseModel):
    sku: str | None = None
    tire_size: str = Field(min_length=3)
    load_index: int = Field(ge=1, le=999)
    speed_rating: str = Field(min_length=1, max_length=1)
    region_code: str = Field(min_length=2, max_length=2)
    quantity_needed: int = Field(ge=1)
    replacement_urgency: Literal["low", "medium", "high"]
    application: str = Field(min_length=1)
    required_certifications: list[str] = Field(min_length=1)
    include_compliance_summary: bool = False


class PromptExtraction(BaseModel):
    sku: str | None = None
    tire_size: str | None = None
    load_index: int | None = None
    speed_rating: str | None = None
    region_code: str | None = None
    quantity_needed: int | None = None
    replacement_urgency: Literal["low", "medium", "high"] | None = None
    application: str | None = None
    required_certifications: list[str] = Field(default_factory=list)
    include_compliance_summary: bool = False


class ToolCallRecord(BaseModel):
    tool_name: str
    args_summary: dict[str, object] = Field(default_factory=dict)
    status: Literal["started", "completed", "failed"]
    started_at: str
    ended_at: str | None = None
    error: str | None = None
    output_summary: dict[str, object] = Field(default_factory=dict)


class TrajectoryLog(BaseModel):
    run_id: str
    records: list[ToolCallRecord] = Field(default_factory=list)


class FinalDecision(BaseModel):
    decision: Literal["approve", "deny", "escalate"]
    rationale: str = Field(min_length=1)
    evidence_refs: list[str] = Field(min_length=1)


class ParseRequestToolInput(BaseModel):
    prompt: str = Field(min_length=1)


class ParseRequestToolOutput(BaseModel):
    resolved_request: ResolvedRequest


class DecisionEvidence(BaseModel):
    source: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    traceability_ref: str | None = None


class MatchRequestPayload(BaseModel):
    tire_size: str = Field(min_length=3)
    load_index: int = Field(ge=1)
    speed_rating: str = Field(min_length=1, max_length=1)
    region_code: str = Field(min_length=2, max_length=2)
    quantity_needed: int = Field(ge=1)


class ComplianceSummaryPayload(BaseModel):
    failed_rules: list[str]
    reasons: list[str]
    policy_version: str = Field(min_length=1)
    evaluated_at_utc: str | None = None
    traceability_refs: list[str]


class MatchResultPayload(BaseModel):
    sku: str = Field(min_length=1)
    score: float = Field(ge=0)
    stock_qty: int = Field(ge=0)
    lead_time_days: int = Field(ge=0)
    unit_price: float = Field(ge=0)
    compliance_status: Literal["compliant"]
    fulfillment_rationale: str = Field(min_length=1)
    traceability_refs: list[str]
    compliance_summary: ComplianceSummaryPayload | None = None


class MatchResponsePayload(BaseModel):
    status: Literal["match"]
    decision: Literal["approve"]
    rationale: str = Field(min_length=1)
    evidence: list[DecisionEvidence] = Field(min_length=1)
    request: MatchRequestPayload
    results: list[MatchResultPayload] = Field(min_length=1)
    ranking_rule: str = Field(min_length=1)
    traceability_refs: list[str]


class NoMatchResponsePayload(BaseModel):
    status: Literal["no_match"]
    decision: Literal["deny", "escalate"]
    rationale: str = Field(min_length=1)
    evidence: list[DecisionEvidence] = Field(min_length=1)
    request: MatchRequestPayload
    reason_codes: list[str] = Field(min_length=1)
    suggested_relaxations: list[str]
    traceability_refs: list[str]


SearchResponsePayload = Annotated[MatchResponsePayload | NoMatchResponsePayload, Field(discriminator="status")]
SEARCH_RESPONSE_ADAPTER = TypeAdapter(SearchResponsePayload)


class RecommendationRankingToolInput(BaseModel):
    request: ResolvedRequest
    policy_version: str = Field(min_length=1)


class RecommendationRankingToolOutput(BaseModel):
    status: Literal["match", "no_match"]
    result_count: int = Field(ge=0)
    top_sku: str | None = None
    traceability_refs: list[str] = Field(default_factory=list)


class CompliancePrecheckToolInput(BaseModel):
    response_status: Literal["match", "no_match"]
    reason_codes: list[str] = Field(default_factory=list)


class CompliancePrecheckToolOutput(BaseModel):
    compliant_path: bool
    escalation_required: bool
    summary: str


class SupplierMatchToolInput(BaseModel):
    sku: str = Field(min_length=1)
    quantity_needed: int = Field(ge=1)
    replacement_urgency: Literal["low", "medium", "high"]


class SupplierMatchToolOutput(BaseModel):
    total_rows: int = Field(ge=0)
    eligible_rows: int = Field(ge=0)
    ineligible_rows: int = Field(ge=0)


class FinalizeDecisionToolInput(BaseModel):
    response_status: Literal["match", "no_match"]
    reason_codes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(min_length=1)


class FinalizeDecisionToolOutput(BaseModel):
    final_decision: FinalDecision


class InvalidRequestError(Exception):
    def __init__(self, payload: dict[str, object]) -> None:
        super().__init__(str(payload.get("reason", "invalid_request")))
        self.payload = payload


class SchemaValidationError(Exception):
    def __init__(self, source: str, details: object) -> None:
        super().__init__(source)
        self.source = source
        self.details = details


def load_task3_module() -> object:
    spec = importlib.util.spec_from_file_location("task3_procurement_handoff", TASK3_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module at {TASK3_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_supplier_module() -> object:
    spec = importlib.util.spec_from_file_location("supplier_system", SUPPLIER_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module at {SUPPLIER_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the tire recommendation pipeline end-to-end through task3 handoff.",
    )
    parser.add_argument(
        "--prompt",
        default="",
        help="Free-text request. Example: 'Need 24 tires size 225/70R19.5 load index 120 speed rating K in TX urgency medium'",
    )
    parser.add_argument("--sku", default="")
    parser.add_argument("--tire-size", default="")
    parser.add_argument("--load-index", type=int, default=0)
    parser.add_argument("--speed-rating", default="")
    parser.add_argument("--region-code", default="")
    parser.add_argument("--quantity-needed", type=int, default=0)
    parser.add_argument("--replacement-urgency", choices=["low", "medium", "high"], default="")
    parser.add_argument("--application", default="")
    parser.add_argument(
        "--required-certifications",
        default="US-DOT",
        help="Comma-separated list of required certifications.",
    )
    parser.add_argument("--include-compliance-summary", action="store_true")
    parser.add_argument(
        "--agent-model",
        default=DEFAULT_AGENT_MODEL,
        help="Pydantic-AI model identifier used for free-text extraction.",
    )
    parser.add_argument("--policy-version", default="policy-2026.06")
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Run in interactive multi-turn mode until user exits.",
    )
    parser.add_argument(
        "--show-trajectory",
        action="store_true",
        help="Include detailed tool-call trajectory in response payloads.",
    )
    parser.add_argument("--compliance-db", type=Path, default=DEFAULT_COMPLIANCE_DB)
    parser.add_argument("--suppliers-db", type=Path, default=DEFAULT_SUPPLIERS_DB)
    return parser.parse_args()


def build_runtime_args(
    *,
    prompt: str = "",
    sku: str = "",
    tire_size: str = "",
    load_index: int = 0,
    speed_rating: str = "",
    region_code: str = "",
    quantity_needed: int = 0,
    replacement_urgency: str = "",
    application: str = "",
    required_certifications: str = "US-DOT",
    include_compliance_summary: bool = False,
    agent_model: str = DEFAULT_AGENT_MODEL,
    policy_version: str = "policy-2026.06",
    chat: bool = False,
    show_trajectory: bool = False,
    compliance_db: Path = DEFAULT_COMPLIANCE_DB,
    suppliers_db: Path = DEFAULT_SUPPLIERS_DB,
) -> argparse.Namespace:
    return argparse.Namespace(
        prompt=prompt,
        sku=sku,
        tire_size=tire_size,
        load_index=load_index,
        speed_rating=speed_rating,
        region_code=region_code,
        quantity_needed=quantity_needed,
        replacement_urgency=replacement_urgency,
        application=application,
        required_certifications=required_certifications,
        include_compliance_summary=include_compliance_summary,
        agent_model=agent_model,
        policy_version=policy_version,
        chat=chat,
        show_trajectory=show_trajectory,
        compliance_db=compliance_db,
        suppliers_db=suppliers_db,
    )


def _merge_with_cli_overrides(args: argparse.Namespace, extracted: PromptExtraction) -> dict[str, object]:
    sku = args.sku or extracted.sku
    tire_size = args.tire_size or extracted.tire_size
    load_index = args.load_index or extracted.load_index
    speed_rating = args.speed_rating or extracted.speed_rating
    region_code = args.region_code or extracted.region_code
    quantity_needed = args.quantity_needed or extracted.quantity_needed
    replacement_urgency = args.replacement_urgency or extracted.replacement_urgency or "medium"
    application = args.application or extracted.application or "Regional delivery"

    cli_certs = [cert.strip() for cert in args.required_certifications.split(",") if cert.strip()]
    required_certifications = cli_certs or extracted.required_certifications or ["US-DOT"]
    include_compliance_summary = args.include_compliance_summary or extracted.include_compliance_summary

    return {
        "sku": str(sku).strip().upper() if sku else None,
        "tire_size": str(tire_size).strip() if tire_size else None,
        "load_index": int(load_index) if load_index is not None else None,
        "speed_rating": str(speed_rating).strip().upper() if speed_rating else None,
        "region_code": str(region_code).strip().upper() if region_code else None,
        "quantity_needed": int(quantity_needed) if quantity_needed is not None else None,
        "replacement_urgency": str(replacement_urgency),
        "application": str(application),
        "required_certifications": list(required_certifications),
        "include_compliance_summary": bool(include_compliance_summary),
    }


def _resolve_with_pydantic_agent(args: argparse.Namespace) -> dict[str, object]:
    from pydantic_ai import Agent

    extraction_agent = Agent(
        args.agent_model,
        output_type=PromptExtraction,
        system_prompt=(
            "You extract fleet tire procurement fields from user prompts. "
            "Return only the structured output schema. "
            "If values are missing, keep them null."
        ),
    )
    run_result = extraction_agent.run_sync(args.prompt)
    extracted = getattr(run_result, "data", None)
    if extracted is None:
        extracted = getattr(run_result, "output", None)
    if extracted is None:
        raise RuntimeError("Pydantic-AI run result did not include structured output")
    return _merge_with_cli_overrides(args, extracted)


def _invalid_request_payload(*, reason: str, details: dict[str, object]) -> dict[str, object]:
    return {
        "error": "invalid_request",
        "source": "prompt_extraction_sufficiency",
        "reason": reason,
        "details": details,
    }


def _lookup_sku_record(
    sku: str,
    compliance_db_path: Path,
    suppliers_db_path: Path,
) -> dict[str, object] | None:
    if not sku:
        return None

    normalized_sku = sku.strip().upper()
    with compliance_db_path.open("r", encoding="utf-8") as f:
        compliance_payload = json.load(f)
    if isinstance(compliance_payload, list):
        for record in compliance_payload:
            if not isinstance(record, dict):
                continue
            record_sku = str(record.get("sku", "")).strip().upper()
            if record_sku == normalized_sku:
                return record

    with suppliers_db_path.open("r", encoding="utf-8") as f:
        supplier_payload = json.load(f)
    if isinstance(supplier_payload, list):
        for supplier in supplier_payload:
            if not isinstance(supplier, dict):
                continue
            contracts = supplier.get("contracts", [])
            if not isinstance(contracts, list):
                continue
            for contract in contracts:
                if not isinstance(contract, dict):
                    continue
                contract_sku = str(contract.get("sku", "")).strip().upper()
                if contract_sku == normalized_sku:
                    return {"sku": contract_sku, "tire_size": None}

    return None


def _resolve_request_or_error(
    resolved_raw: dict[str, object],
    args: argparse.Namespace,
) -> tuple[ResolvedRequest | None, dict[str, object] | None]:
    missing_critical_fields = [
        field
        for field in ["load_index", "speed_rating", "region_code"]
        if resolved_raw.get(field) in (None, "")
    ]
    if missing_critical_fields:
        return None, _invalid_request_payload(
            reason="missing_critical_fields",
            details={"missing_fields": missing_critical_fields},
        )

    sku = str(resolved_raw.get("sku") or "").strip().upper() or None
    tire_size = str(resolved_raw.get("tire_size") or "").strip() or None
    quantity_needed_raw = resolved_raw.get("quantity_needed")
    quantity_needed = int(quantity_needed_raw) if quantity_needed_raw is not None else None

    has_tire_and_quantity = bool(tire_size) and quantity_needed is not None
    has_sku = bool(sku)

    if not has_tire_and_quantity and not has_sku:
        return None, _invalid_request_payload(
            reason="missing_conditional_fields",
            details={
                "missing_fields": ["tire_size", "quantity_needed", "sku"],
                "requirement": "provide tire_size and quantity_needed or provide sku",
            },
        )

    sku_record = None
    if has_sku:
        sku_record = _lookup_sku_record(sku, args.compliance_db, args.suppliers_db)
        if sku_record is None:
            reason = "invalid_sku"
            if not has_tire_and_quantity:
                reason = "search_cannot_take_place_since_input_could_not_be_validated"
            return None, _invalid_request_payload(
                reason=reason,
                details={
                    "invalid_sku": sku,
                    "missing_fields": [] if has_tire_and_quantity else ["tire_size", "quantity_needed"],
                },
            )

    if not tire_size and sku_record is not None:
        derived_tire_size = str(sku_record.get("tire_size") or "").strip() if isinstance(sku_record, dict) else ""
        if derived_tire_size:
            tire_size = derived_tire_size

    if quantity_needed is None and has_sku:
        # For explicit SKU lookups without quantity, use a minimal quantity probe.
        quantity_needed = 1

    if not tire_size or quantity_needed is None:
        return None, _invalid_request_payload(
            reason="search_cannot_take_place_since_input_could_not_be_validated",
            details={
                "missing_fields": [
                    field
                    for field, value in [("tire_size", tire_size), ("quantity_needed", quantity_needed)]
                    if not value
                ],
            },
        )

    resolved = ResolvedRequest(
        sku=sku,
        tire_size=tire_size,
        load_index=int(resolved_raw["load_index"]),
        speed_rating=str(resolved_raw["speed_rating"]),
        region_code=str(resolved_raw["region_code"]),
        quantity_needed=quantity_needed,
        replacement_urgency=str(resolved_raw.get("replacement_urgency") or "medium"),
        application=str(resolved_raw.get("application") or "Regional delivery"),
        required_certifications=list(resolved_raw.get("required_certifications") or ["US-DOT"]),
        include_compliance_summary=bool(resolved_raw.get("include_compliance_summary", False)),
    )
    return resolved, None


def _lead_time_for_urgency(urgency: str) -> int:
    if urgency.lower() == "high":
        return 5
    if urgency.lower() == "low":
        return 30
    return 14


def _resolve_primary_sku(response: dict[str, object]) -> str | None:
    if response.get("status") != "match":
        return None
    results = response.get("results")
    if not isinstance(results, list) or not results:
        return None
    first = results[0]
    if not isinstance(first, dict):
        return None
    sku = first.get("sku")
    return str(sku) if sku else None


def _supplier_lookup_summary(
    supplier_module: object,
    db_path: Path,
    sku: str,
    quantity_needed: int,
    replacement_urgency: str,
) -> list[dict[str, object]]:
    request = supplier_module.SupplierLookupRequest(
        sku=sku,
        requested_quantity=quantity_needed,
        max_lead_time_days=_lead_time_for_urgency(replacement_urgency),
    )
    evaluations = supplier_module.evaluate_request(db_path, request, evaluation_date=date.today())

    return [
        {
            "supplier_id": item.supplier_id,
            "supplier_name": item.supplier_name,
            "preferred": item.preferred,
            "contract_id": item.contract_id,
            "sku": item.sku,
            "status": item.status,
            "failed_rules": item.failed_rules,
            "reasons": item.reasons,
        }
        for item in evaluations
    ]


def _print_greeting() -> None:
    print("Welcome to Fleet Tire Recommendation Agent.")
    print(
        "Example prompt: Need 24 tires size 225/70R19.5 load index 120 speed rating K in TX "
        "urgency medium for regional delivery and include compliance summary."
    )


def _is_exit_command(text: str) -> bool:
    return text.strip().lower() in {"exit", "quit", "q"}


def _new_record(tool_name: str, args_summary: dict[str, object]) -> ToolCallRecord:
    return ToolCallRecord(
        tool_name=tool_name,
        args_summary=args_summary,
        status="started",
        started_at=datetime.now().astimezone().isoformat(),
    )


def _finish_record(
    record: ToolCallRecord,
    *,
    status: Literal["completed", "failed"],
    output_summary: dict[str, object] | None = None,
    error: str | None = None,
) -> ToolCallRecord:
    return record.model_copy(
        update={
            "status": status,
            "ended_at": datetime.now().astimezone().isoformat(),
            "output_summary": output_summary or {},
            "error": error,
        }
    )


def parse_request_tool(args: argparse.Namespace, prompt: str) -> ParseRequestToolOutput:
    """Purpose:
    Parse natural language procurement requests into a validated structured request.

    When to use:
    Use at the start of each agent run to transform user prompt text into typed fields.

    When NOT to use:
    Do not use after request parsing is already complete, and do not use for ranking or supplier matching.

    Args:
    - args: Runtime options including model selection and override flags.
    - prompt: Raw user prompt text.

    Returns:
    - ParseRequestToolOutput containing a validated ResolvedRequest.

    Raises:
    - ValidationError: if parsed values fail request schema checks.
    - RuntimeError: if model output is unavailable or malformed.

    Example:
    parse_request_tool(args, "Need 24 tires size 225/70R19.5 in TX")
    """
    args.prompt = prompt
    resolved_raw = _resolve_with_pydantic_agent(args)
    resolved, invalid_payload = _resolve_request_or_error(resolved_raw, args)
    if invalid_payload is not None:
        raise InvalidRequestError(invalid_payload)
    assert resolved is not None
    return ParseRequestToolOutput(resolved_request=resolved)


def recommendation_ranking_tool(
    task3: object,
    args: argparse.Namespace,
    request: ResolvedRequest,
) -> tuple[dict[str, object], RecommendationRankingToolOutput]:
    """Purpose:
    Execute compliance-gated recommendation ranking and produce ranked inventory response.

    When to use:
    Use after request parsing to generate match/no-match results with ranking metadata.

    When NOT to use:
    Do not use before request parsing, and do not use for direct supplier contract evaluation.

    Args:
    - task3: Loaded task3 recommendation/procurement handoff module.
    - args: Runtime options containing DB paths and policy version.
    - request: Validated structured procurement request.

    Returns:
    - Tuple of raw task3 response and RecommendationRankingToolOutput summary.

    Raises:
    - RuntimeError / ValueError from downstream subsystem failures.

    Example:
    recommendation_ranking_tool(task3, args, request)
    """
    search_request = task3.SearchRequest(
        tire_size=request.tire_size,
        load_index=request.load_index,
        speed_rating=request.speed_rating,
        region_code=request.region_code,
        quantity_needed=request.quantity_needed,
        replacement_urgency=request.replacement_urgency,
        include_compliance_summary=request.include_compliance_summary,
        required_certifications=request.required_certifications,
        application=request.application,
    )

    try:
        response = task3.search_inventory(
            args.compliance_db,
            args.suppliers_db,
            search_request,
            policy_version=args.policy_version,
        )
    except ValidationError as exc:
        raise SchemaValidationError("task3_processing", exc.errors()) from exc

    try:
        validated_response = SEARCH_RESPONSE_ADAPTER.validate_python(response).model_dump(exclude_none=True)
    except ValidationError as exc:
        raise SchemaValidationError("task3_response_schema", exc.errors()) from exc

    ranking_output = RecommendationRankingToolOutput(
        status=str(validated_response.get("status", "no_match")),
        result_count=len(validated_response.get("results", [])) if isinstance(validated_response.get("results"), list) else 0,
        top_sku=(validated_response.get("results", [{}])[0].get("sku") if validated_response.get("results") else None),
        traceability_refs=[str(item) for item in validated_response.get("traceability_refs", [])],
    )
    return validated_response, ranking_output


def compliance_precheck_tool(input_model: CompliancePrecheckToolInput) -> CompliancePrecheckToolOutput:
    """Purpose:
    Derive compliance path state (compliant, deny, or escalate) from ranking response status and reason codes.

    When to use:
    Use after recommendation ranking to drive downstream decision policy and escalation handling.

    When NOT to use:
    Do not use as a substitute for full compliance evaluation; this is a trajectory/state summary tool.

    Args:
    - input_model: CompliancePrecheckToolInput containing response status and reason codes.

    Returns:
    - CompliancePrecheckToolOutput summary for trajectory and decision routing.

    Raises:
    - ValidationError if input does not satisfy schema constraints.

    Example:
    compliance_precheck_tool(CompliancePrecheckToolInput(response_status="no_match", reason_codes=["REQUIRES_HUMAN_REVIEW"]))
    """
    escalation_required = "REQUIRES_HUMAN_REVIEW" in input_model.reason_codes
    compliant_path = input_model.response_status == "match"
    if compliant_path:
        summary = "compliant recommendation path"
    elif escalation_required:
        summary = "compliance path requires escalation"
    else:
        summary = "no compliant recommendation path"

    return CompliancePrecheckToolOutput(
        compliant_path=compliant_path,
        escalation_required=escalation_required,
        summary=summary,
    )


def supplier_match_tool(
    supplier_module: object,
    args: argparse.Namespace,
    input_model: SupplierMatchToolInput,
) -> tuple[list[dict[str, object]], SupplierMatchToolOutput]:
    """Purpose:
    Evaluate supplier contracts for a chosen SKU and summarize eligibility outcomes.

    When to use:
    Use after a ranked SKU exists and supplier contract viability must be surfaced.

    When NOT to use:
    Do not use if no ranked SKU is available (no-match path), and do not use for parsing or ranking.

    Args:
    - supplier_module: Loaded supplier subsystem module.
    - args: Runtime options containing supplier DB path.
    - input_model: SupplierMatchToolInput with SKU, quantity, and urgency.

    Returns:
    - Tuple of supplier rows and SupplierMatchToolOutput summary metrics.

    Raises:
    - RuntimeError / ValueError from supplier subsystem or data shape errors.

    Example:
    supplier_match_tool(supplier_module, args, SupplierMatchToolInput(sku="MIC-...", quantity_needed=24, replacement_urgency="medium"))
    """
    rows = _supplier_lookup_summary(
        supplier_module,
        args.suppliers_db,
        input_model.sku,
        input_model.quantity_needed,
        input_model.replacement_urgency,
    )
    summary = SupplierMatchToolOutput(
        total_rows=len(rows),
        eligible_rows=len([row for row in rows if row.get("status") == "eligible"]),
        ineligible_rows=len([row for row in rows if row.get("status") != "eligible"]),
    )
    return rows, summary


def finalize_decision_tool(input_model: FinalizeDecisionToolInput) -> FinalizeDecisionToolOutput:
    """Purpose:
    Produce final approve/deny/escalate decision with rationale and evidence references.

    When to use:
    Use as the terminal step after ranking/compliance state and supplier context are known.

    When NOT to use:
    Do not use before upstream evidence exists; evidence_refs must already be populated.

    Args:
    - input_model: FinalizeDecisionToolInput containing response status, reason codes, and evidence references.

    Returns:
    - FinalizeDecisionToolOutput containing typed final decision artifact.

    Raises:
    - ValidationError if input schema constraints are violated.

    Example:
    finalize_decision_tool(FinalizeDecisionToolInput(response_status="match", evidence_refs=["tool:recommendation_ranking_tool"]))
    """
    return _finalize_decision(input_model)


def _finalize_decision(
    input_model: FinalizeDecisionToolInput,
) -> FinalizeDecisionToolOutput:
    if input_model.response_status == "match":
        decision = FinalDecision(
            decision="approve",
            rationale="Compliant inventory match found with ranked supplier-backed option(s).",
            evidence_refs=input_model.evidence_refs,
        )
        return FinalizeDecisionToolOutput(final_decision=decision)

    if "REQUIRES_HUMAN_REVIEW" in input_model.reason_codes:
        decision = FinalDecision(
            decision="escalate",
            rationale="No auto-resolvable match; policy precedence or review condition requires human decision.",
            evidence_refs=input_model.evidence_refs,
        )
        return FinalizeDecisionToolOutput(final_decision=decision)

    decision = FinalDecision(
        decision="deny",
        rationale="No qualifying inventory match found for the current constraints.",
        evidence_refs=input_model.evidence_refs,
    )
    return FinalizeDecisionToolOutput(final_decision=decision)


def _build_error_response(
    *,
    run_id: str,
    records: list[ToolCallRecord],
    error: str,
    details: object,
    tool_name: str | None = None,
    hint: str | None = None,
    include_trajectory: bool = False,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "error": error,
        "details": details,
        "run_id": run_id,
    }
    if include_trajectory:
        payload["trajectory"] = TrajectoryLog(run_id=run_id, records=records).model_dump()
    if tool_name is not None:
        payload["tool"] = tool_name
    if hint is not None:
        payload["hint"] = hint
    return payload


def _build_invalid_request_response(
    *,
    run_id: str,
    records: list[ToolCallRecord],
    payload: dict[str, object],
    include_trajectory: bool = False,
) -> dict[str, object]:
    response = {
        **payload,
        "run_id": run_id,
    }
    if include_trajectory:
        response["trajectory"] = TrajectoryLog(run_id=run_id, records=records).model_dump()
    return response


def _build_schema_validation_error_response(
    *,
    run_id: str,
    records: list[ToolCallRecord],
    source: str,
    details: object,
    include_trajectory: bool = False,
) -> dict[str, object]:
    response: dict[str, object] = {
        "error": "schema_validation_error",
        "source": source,
        "details": details,
        "run_id": run_id,
    }
    if include_trajectory:
        response["trajectory"] = TrajectoryLog(run_id=run_id, records=records).model_dump()
    return response


def _process_prompt(
    args: argparse.Namespace,
    task3: object,
    supplier_module: object,
    prompt: str,
    *,
    source: str = "cli",
) -> tuple[int, dict[str, object] | None]:
    started = time.perf_counter()
    run_id = str(uuid4())
    include_trajectory = bool(getattr(args, "show_trajectory", False))
    records: list[ToolCallRecord] = []
    args.prompt = prompt
    _console_log(
        "interaction_started",
        source=source,
        run_id=run_id,
        prompt_preview=prompt[:160],
    )

    try:
        parse_args_model = ParseRequestToolInput(prompt=prompt)
    except ValidationError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="parse_request_tool",
            error="invalid prompt",
        )
        return 2, _build_error_response(
            run_id=run_id,
            records=records,
            error="invalid_request",
            details=exc.errors(),
            tool_name="parse_request_tool",
            include_trajectory=include_trajectory,
        )

    parse_record = _new_record("parse_request_tool", parse_args_model.model_dump())
    records.append(parse_record)
    parse_started = time.perf_counter()
    _console_tool_log(event="tool_started", source=source, run_id=run_id, tool_name="parse_request_tool")
    try:
        parse_output = parse_request_tool(args, prompt)
        resolved = parse_output.resolved_request.model_dump()
        records[-1] = _finish_record(
            records[-1],
            status="completed",
            output_summary={
                "region_code": parse_output.resolved_request.region_code,
                "quantity_needed": parse_output.resolved_request.quantity_needed,
            },
        )
        _console_tool_log(
            event="tool_completed",
            source=source,
            run_id=run_id,
            tool_name="parse_request_tool",
            elapsed_ms=round((time.perf_counter() - parse_started) * 1000, 2),
            region_code=parse_output.resolved_request.region_code,
            quantity_needed=parse_output.resolved_request.quantity_needed,
        )
    except InvalidRequestError as exc:
        records[-1] = _finish_record(records[-1], status="failed", error=str(exc.payload.get("reason", "invalid_request")))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="parse_request_tool",
            elapsed_ms=round((time.perf_counter() - parse_started) * 1000, 2),
            error="invalid_request",
            reason=exc.payload.get("reason"),
        )
        _console_log(
            "interaction_validation_error",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            phase="prompt_extraction_sufficiency",
            reason=exc.payload.get("reason"),
        )
        return 2, _build_invalid_request_response(
            run_id=run_id,
            records=records,
            payload=exc.payload,
            include_trajectory=include_trajectory,
        )
    except ValidationError as exc:
        records[-1] = _finish_record(records[-1], status="failed", error="request validation failed")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="parse_request_tool",
            elapsed_ms=round((time.perf_counter() - parse_started) * 1000, 2),
            error="validation",
        )
        _console_log("interaction_validation_error", source=source, run_id=run_id, elapsed_ms=elapsed_ms)
        return 2, _build_error_response(
            run_id=run_id,
            records=records,
            error="invalid_request",
            details=exc.errors(),
            tool_name="parse_request_tool",
            include_trajectory=include_trajectory,
        )
    except Exception as exc:
        records[-1] = _finish_record(records[-1], status="failed", error=str(exc))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="parse_request_tool",
            elapsed_ms=round((time.perf_counter() - parse_started) * 1000, 2),
            error=str(exc),
        )
        _console_log(
            "llm_extract_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            error=str(exc),
        )
        return 3, _build_error_response(
            run_id=run_id,
            records=records,
            error="llm_extract_failed",
            details=str(exc),
            tool_name="parse_request_tool",
            hint="Verify model credentials and network access, or choose a reachable model.",
            include_trajectory=include_trajectory,
        )

    ranking_input = RecommendationRankingToolInput(request=parse_output.resolved_request, policy_version=args.policy_version)
    ranking_record = _new_record("recommendation_ranking_tool", ranking_input.model_dump())
    records.append(ranking_record)
    ranking_started = time.perf_counter()
    _console_tool_log(event="tool_started", source=source, run_id=run_id, tool_name="recommendation_ranking_tool")
    try:
        response, ranking_output = recommendation_ranking_tool(task3, args, parse_output.resolved_request)
    except SchemaValidationError as exc:
        records[-1] = _finish_record(records[-1], status="failed", error="schema validation")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="recommendation_ranking_tool",
            elapsed_ms=round((time.perf_counter() - ranking_started) * 1000, 2),
            error="schema_validation_error",
            schema_source=exc.source,
        )
        _console_log(
            "interaction_schema_validation_error",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            phase=exc.source,
        )
        return 2, _build_schema_validation_error_response(
            run_id=run_id,
            records=records,
            source=exc.source,
            details=exc.details,
            include_trajectory=include_trajectory,
        )
    except ValidationError as exc:
        records[-1] = _finish_record(records[-1], status="failed", error="ranking validation failed")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="recommendation_ranking_tool",
            elapsed_ms=round((time.perf_counter() - ranking_started) * 1000, 2),
            error="validation",
        )
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="recommendation_ranking_tool",
            error="validation",
        )
        return 2, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_validation_failed",
            details=exc.errors(),
            tool_name="recommendation_ranking_tool",
            include_trajectory=include_trajectory,
        )
    except Exception as exc:
        records[-1] = _finish_record(records[-1], status="failed", error=str(exc))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="recommendation_ranking_tool",
            elapsed_ms=round((time.perf_counter() - ranking_started) * 1000, 2),
            error=str(exc),
        )
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="recommendation_ranking_tool",
            error=str(exc),
        )
        return 4, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_execution_failed",
            details=str(exc),
            tool_name="recommendation_ranking_tool",
            include_trajectory=include_trajectory,
        )
    records[-1] = _finish_record(
        records[-1],
        status="completed",
        output_summary={
            "status": ranking_output.status,
            "result_count": ranking_output.result_count,
            "top_sku": ranking_output.top_sku,
        },
    )
    _console_tool_log(
        event="tool_completed",
        source=source,
        run_id=run_id,
        tool_name="recommendation_ranking_tool",
        elapsed_ms=round((time.perf_counter() - ranking_started) * 1000, 2),
        status=ranking_output.status,
        result_count=ranking_output.result_count,
        top_sku=ranking_output.top_sku,
    )

    compliance_input = CompliancePrecheckToolInput(
        response_status=ranking_output.status,
        reason_codes=[str(code) for code in response.get("reason_codes", [])],
    )
    compliance_record = _new_record("compliance_precheck_tool", compliance_input.model_dump())
    records.append(compliance_record)
    compliance_started = time.perf_counter()
    _console_tool_log(event="tool_started", source=source, run_id=run_id, tool_name="compliance_precheck_tool")
    try:
        compliance_output = compliance_precheck_tool(compliance_input)
    except ValidationError as exc:
        records[-1] = _finish_record(records[-1], status="failed", error="precheck validation failed")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="compliance_precheck_tool",
            elapsed_ms=round((time.perf_counter() - compliance_started) * 1000, 2),
            error="validation",
        )
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="compliance_precheck_tool",
            error="validation",
        )
        return 2, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_validation_failed",
            details=exc.errors(),
            tool_name="compliance_precheck_tool",
            include_trajectory=include_trajectory,
        )
    except Exception as exc:
        records[-1] = _finish_record(records[-1], status="failed", error=str(exc))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="compliance_precheck_tool",
            elapsed_ms=round((time.perf_counter() - compliance_started) * 1000, 2),
            error=str(exc),
        )
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="compliance_precheck_tool",
            error=str(exc),
        )
        return 4, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_execution_failed",
            details=str(exc),
            tool_name="compliance_precheck_tool",
            include_trajectory=include_trajectory,
        )
    records[-1] = _finish_record(
        records[-1],
        status="completed",
        output_summary=compliance_output.model_dump(),
    )
    _console_tool_log(
        event="tool_completed",
        source=source,
        run_id=run_id,
        tool_name="compliance_precheck_tool",
        elapsed_ms=round((time.perf_counter() - compliance_started) * 1000, 2),
        compliant_path=compliance_output.compliant_path,
        escalation_required=compliance_output.escalation_required,
    )

    resolved_sku = _resolve_primary_sku(response)
    supplier_lookup: list[dict[str, object]] = []
    if resolved_sku is not None:
        try:
            supplier_input = SupplierMatchToolInput(
                sku=resolved_sku,
                quantity_needed=int(resolved["quantity_needed"]),
                replacement_urgency=str(resolved["replacement_urgency"]),
            )
        except ValidationError as exc:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            _console_log(
                "interaction_failed",
                source=source,
                run_id=run_id,
                elapsed_ms=elapsed_ms,
                failed_tool="supplier_match_tool",
                error="validation",
            )
            return 2, _build_error_response(
                run_id=run_id,
                records=records,
                error="tool_validation_failed",
                details=exc.errors(),
                tool_name="supplier_match_tool",
                include_trajectory=include_trajectory,
            )
        supplier_record = _new_record("supplier_match_tool", supplier_input.model_dump())
        records.append(supplier_record)
        supplier_started = time.perf_counter()
        _console_tool_log(event="tool_started", source=source, run_id=run_id, tool_name="supplier_match_tool")
        try:
            supplier_lookup, supplier_output = supplier_match_tool(supplier_module, args, supplier_input)
        except ValidationError as exc:
            records[-1] = _finish_record(records[-1], status="failed", error="supplier validation failed")
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            _console_tool_log(
                event="tool_failed",
                source=source,
                run_id=run_id,
                tool_name="supplier_match_tool",
                elapsed_ms=round((time.perf_counter() - supplier_started) * 1000, 2),
                error="validation",
            )
            _console_log(
                "interaction_failed",
                source=source,
                run_id=run_id,
                elapsed_ms=elapsed_ms,
                failed_tool="supplier_match_tool",
                error="validation",
            )
            return 2, _build_error_response(
                run_id=run_id,
                records=records,
                error="tool_validation_failed",
                details=exc.errors(),
                tool_name="supplier_match_tool",
                include_trajectory=include_trajectory,
            )
        except Exception as exc:
            records[-1] = _finish_record(records[-1], status="failed", error=str(exc))
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            _console_tool_log(
                event="tool_failed",
                source=source,
                run_id=run_id,
                tool_name="supplier_match_tool",
                elapsed_ms=round((time.perf_counter() - supplier_started) * 1000, 2),
                error=str(exc),
            )
            _console_log(
                "interaction_failed",
                source=source,
                run_id=run_id,
                elapsed_ms=elapsed_ms,
                failed_tool="supplier_match_tool",
                error=str(exc),
            )
            return 4, _build_error_response(
                run_id=run_id,
                records=records,
                error="tool_execution_failed",
                details=str(exc),
                tool_name="supplier_match_tool",
                include_trajectory=include_trajectory,
            )
        records[-1] = _finish_record(
            records[-1],
            status="completed",
            output_summary=supplier_output.model_dump(),
        )
        _console_tool_log(
            event="tool_completed",
            source=source,
            run_id=run_id,
            tool_name="supplier_match_tool",
            elapsed_ms=round((time.perf_counter() - supplier_started) * 1000, 2),
            total_rows=supplier_output.total_rows,
            eligible_rows=supplier_output.eligible_rows,
            ineligible_rows=supplier_output.ineligible_rows,
        )

    try:
        decision_input = FinalizeDecisionToolInput(
            response_status=ranking_output.status,
            reason_codes=[str(code) for code in response.get("reason_codes", [])],
            evidence_refs=[f"tool:{record.tool_name}" for record in records if record.status == "completed"],
        )
    except ValidationError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="finalize_decision_tool",
            error="validation",
        )
        return 2, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_validation_failed",
            details=exc.errors(),
            tool_name="finalize_decision_tool",
            include_trajectory=include_trajectory,
        )
    decision_record = _new_record("finalize_decision_tool", decision_input.model_dump())
    records.append(decision_record)
    decision_started = time.perf_counter()
    _console_tool_log(event="tool_started", source=source, run_id=run_id, tool_name="finalize_decision_tool")
    try:
        decision_output = finalize_decision_tool(decision_input)
    except ValidationError as exc:
        records[-1] = _finish_record(records[-1], status="failed", error="decision validation failed")
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="finalize_decision_tool",
            elapsed_ms=round((time.perf_counter() - decision_started) * 1000, 2),
            error="validation",
        )
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="finalize_decision_tool",
            error="validation",
        )
        return 2, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_validation_failed",
            details=exc.errors(),
            tool_name="finalize_decision_tool",
            include_trajectory=include_trajectory,
        )
    except Exception as exc:
        records[-1] = _finish_record(records[-1], status="failed", error=str(exc))
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_tool_log(
            event="tool_failed",
            source=source,
            run_id=run_id,
            tool_name="finalize_decision_tool",
            elapsed_ms=round((time.perf_counter() - decision_started) * 1000, 2),
            error=str(exc),
        )
        _console_log(
            "interaction_failed",
            source=source,
            run_id=run_id,
            elapsed_ms=elapsed_ms,
            failed_tool="finalize_decision_tool",
            error=str(exc),
        )
        return 4, _build_error_response(
            run_id=run_id,
            records=records,
            error="tool_execution_failed",
            details=str(exc),
            tool_name="finalize_decision_tool",
            include_trajectory=include_trajectory,
        )
    records[-1] = _finish_record(
        records[-1],
        status="completed",
        output_summary=decision_output.final_decision.model_dump(),
    )
    _console_tool_log(
        event="tool_completed",
        source=source,
        run_id=run_id,
        tool_name="finalize_decision_tool",
        elapsed_ms=round((time.perf_counter() - decision_started) * 1000, 2),
        decision=decision_output.final_decision.decision,
    )

    output = {
        "run_id": run_id,
        "resolved_request": resolved,
        "response": response,
        "supplier_lookup": supplier_lookup,
        "final_decision": decision_output.final_decision.model_dump(),
    }
    if include_trajectory:
        output["trajectory"] = TrajectoryLog(run_id=run_id, records=records).model_dump()
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    _console_log(
        "interaction_completed",
        source=source,
        run_id=run_id,
        elapsed_ms=elapsed_ms,
        status=response.get("status"),
        supplier_rows=len(supplier_lookup),
    )
    return 0, output


def process_prompt_with_runtime(
    prompt: str,
    *,
    args: argparse.Namespace | None = None,
    task3_module: object | None = None,
    supplier_module: object | None = None,
    source: str = "api",
) -> tuple[int, dict[str, object] | None]:
    runtime_args = args or build_runtime_args()
    task3 = task3_module or load_task3_module()
    supplier = supplier_module or load_supplier_module()
    return _process_prompt(runtime_args, task3, supplier, prompt, source=source)


def _run_chat_loop(args: argparse.Namespace, task3: object, supplier_module: object) -> int:
    _print_greeting()
    print("Type a prompt, or type 'exit' to quit.")

    while True:
        user_prompt = input("Prompt> ").strip()
        if not user_prompt:
            print("Please enter a prompt or type 'exit'.")
            continue
        if _is_exit_command(user_prompt):
            print("Goodbye.")
            return 0

        code, output = _process_prompt(args, task3, supplier_module, user_prompt, source="cli-chat")
        if output is not None:
            print(json.dumps(output, indent=2, sort_keys=True))
        if code != 0:
            print("Request could not be processed. Please revise your prompt and try again.")


def main() -> int:
    args = parse_args()
    task3 = load_task3_module()
    supplier_module = load_supplier_module()

    if args.chat:
        return _run_chat_loop(args, task3, supplier_module)

    if not args.prompt.strip():
        _print_greeting()
        args.prompt = input("Enter tire request prompt: ").strip()

    if _is_exit_command(args.prompt):
        print("Goodbye.")
        return 0

    code, output = _process_prompt(args, task3, supplier_module, args.prompt, source="cli-single")
    if output is not None:
        print(json.dumps(output, indent=2, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
