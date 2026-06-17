from __future__ import annotations

import argparse
from datetime import date, datetime
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from typing import Literal

from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv


load_dotenv()


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK3_MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task3_procurement_handoff.py"
SUPPLIER_MODULE_PATH = REPO_ROOT / "subsystem" / "supplier-system" / "supplier_system.py"
DEFAULT_COMPLIANCE_DB = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
DEFAULT_SUPPLIERS_DB = REPO_ROOT / "subsystem" / "supplier-system" / "mock" / "suppliers-db.json"
DEFAULT_AGENT_MODEL = os.getenv("PROCUREMENT_AGENT_MODEL", "openai-chat:gpt-4o-mini")


def _console_log(event: str, **fields: object) -> None:
    timestamp = datetime.now().astimezone().isoformat()
    payload = {"event": event, "ts": timestamp, **fields}
    print(f"[agent-log] {json.dumps(payload, sort_keys=True)}")


class ResolvedRequest(BaseModel):
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
    tire_size: str | None = None
    load_index: int | None = None
    speed_rating: str | None = None
    region_code: str | None = None
    quantity_needed: int | None = None
    replacement_urgency: Literal["low", "medium", "high"] | None = None
    application: str | None = None
    required_certifications: list[str] = Field(default_factory=list)
    include_compliance_summary: bool = False


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
    parser.add_argument("--compliance-db", type=Path, default=DEFAULT_COMPLIANCE_DB)
    parser.add_argument("--suppliers-db", type=Path, default=DEFAULT_SUPPLIERS_DB)
    return parser.parse_args()


def build_runtime_args(
    *,
    prompt: str = "",
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
    compliance_db: Path = DEFAULT_COMPLIANCE_DB,
    suppliers_db: Path = DEFAULT_SUPPLIERS_DB,
) -> argparse.Namespace:
    return argparse.Namespace(
        prompt=prompt,
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
        compliance_db=compliance_db,
        suppliers_db=suppliers_db,
    )


def _merge_with_cli_overrides(args: argparse.Namespace, extracted: PromptExtraction) -> dict[str, object]:
    tire_size = args.tire_size or extracted.tire_size or "225/70R19.5"
    load_index = args.load_index or extracted.load_index or 120
    speed_rating = args.speed_rating or extracted.speed_rating or "K"
    region_code = args.region_code or extracted.region_code or "TX"
    quantity_needed = args.quantity_needed or extracted.quantity_needed or 24
    replacement_urgency = args.replacement_urgency or extracted.replacement_urgency or "medium"
    application = args.application or extracted.application or "Regional delivery"

    cli_certs = [cert.strip() for cert in args.required_certifications.split(",") if cert.strip()]
    required_certifications = cli_certs or extracted.required_certifications or ["US-DOT"]
    include_compliance_summary = args.include_compliance_summary or extracted.include_compliance_summary

    return ResolvedRequest(
        tire_size=str(tire_size),
        load_index=int(load_index),
        speed_rating=str(speed_rating).upper(),
        region_code=str(region_code).upper(),
        quantity_needed=int(quantity_needed),
        replacement_urgency=str(replacement_urgency),
        application=str(application),
        required_certifications=list(required_certifications),
        include_compliance_summary=bool(include_compliance_summary),
    ).model_dump()


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


def _process_prompt(
    args: argparse.Namespace,
    task3: object,
    supplier_module: object,
    prompt: str,
    *,
    source: str = "cli",
) -> tuple[int, dict[str, object] | None]:
    started = time.perf_counter()
    args.prompt = prompt
    _console_log(
        "interaction_started",
        source=source,
        prompt_preview=prompt[:160],
    )

    try:
        resolved = _resolve_with_pydantic_agent(args)
    except ValidationError as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_log("interaction_validation_error", source=source, elapsed_ms=elapsed_ms)
        return 2, {"error": "invalid_request", "details": exc.errors()}
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        _console_log(
            "llm_extract_failed",
            source=source,
            elapsed_ms=elapsed_ms,
            error=str(exc),
        )
        return 3, {
            "error": "llm_extract_failed",
            "details": str(exc),
            "hint": "Verify model credentials and network access, or choose a reachable model.",
        }

    request = task3.SearchRequest(
        tire_size=resolved["tire_size"],
        load_index=resolved["load_index"],
        speed_rating=resolved["speed_rating"],
        region_code=resolved["region_code"],
        quantity_needed=resolved["quantity_needed"],
        replacement_urgency=resolved["replacement_urgency"],
        include_compliance_summary=resolved["include_compliance_summary"],
        required_certifications=resolved["required_certifications"],
        application=resolved["application"],
    )

    response = task3.search_inventory(
        args.compliance_db,
        args.suppliers_db,
        request,
        policy_version=args.policy_version,
    )

    resolved_sku = _resolve_primary_sku(response)
    supplier_lookup: list[dict[str, object]] = []
    if resolved_sku is not None:
        supplier_lookup = _supplier_lookup_summary(
            supplier_module,
            args.suppliers_db,
            resolved_sku,
            int(resolved["quantity_needed"]),
            str(resolved["replacement_urgency"]),
        )

    output = {
        "resolved_request": resolved,
        "response": response,
        "supplier_lookup": supplier_lookup,
    }
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    _console_log(
        "interaction_completed",
        source=source,
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
