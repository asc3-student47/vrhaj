from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


REPO_ROOT = Path(__file__).resolve().parents[1]
TASK3_MODULE_PATH = REPO_ROOT / "subsystem" / "recommendation-agent" / "task3_procurement_handoff.py"
DEFAULT_COMPLIANCE_DB = REPO_ROOT / "subsystem" / "compliance-system" / "mock" / "tire-compliance-db.json"
DEFAULT_SUPPLIERS_DB = REPO_ROOT / "subsystem" / "supplier-database" / "mock" / "suppliers-db.json"


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


def load_task3_module() -> object:
    spec = importlib.util.spec_from_file_location("task3_procurement_handoff", TASK3_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module at {TASK3_MODULE_PATH}")
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
    parser.add_argument("--policy-version", default="policy-2026.06")
    parser.add_argument("--compliance-db", type=Path, default=DEFAULT_COMPLIANCE_DB)
    parser.add_argument("--suppliers-db", type=Path, default=DEFAULT_SUPPLIERS_DB)
    return parser.parse_args()


def _extract_from_prompt(prompt: str) -> dict[str, object]:
    text = prompt.strip()
    lower = text.lower()
    extracted: dict[str, object] = {}

    size_match = re.search(r"\b\d{3}/\d{2}R\d{2}(?:\.\d)?\b", text, re.IGNORECASE)
    if not size_match:
        size_match = re.search(r"\b\d{2}R\d{2}(?:\.\d)?\b", text, re.IGNORECASE)
    if size_match:
        extracted["tire_size"] = size_match.group(0).upper()

    load_match = re.search(r"load\s*index\s*[:=]?\s*(\d{2,3})", lower)
    if load_match:
        extracted["load_index"] = int(load_match.group(1))

    speed_match = re.search(r"speed\s*rating\s*[:=]?\s*([a-z])\b", lower)
    if speed_match:
        extracted["speed_rating"] = speed_match.group(1).upper()

    region_match = re.search(r"(?:region|in)\s*[:=]?\s*([A-Z]{2})\b", text)
    if region_match:
        extracted["region_code"] = region_match.group(1).upper()

    quantity_match = re.search(r"(?:need|needs|quantity|qty|for)\s*[:=]?\s*(\d+)\s*(?:tires|tire)?", lower)
    if quantity_match:
        extracted["quantity_needed"] = int(quantity_match.group(1))

    if " urgency high" in f" {lower}" or "urgent" in lower or "asap" in lower:
        extracted["replacement_urgency"] = "high"
    elif " urgency low" in f" {lower}":
        extracted["replacement_urgency"] = "low"
    elif " urgency medium" in f" {lower}":
        extracted["replacement_urgency"] = "medium"

    if "regional" in lower:
        extracted["application"] = "Regional delivery"
    elif "long-haul" in lower or "long haul" in lower:
        extracted["application"] = "Long-haul"

    include_summary = (
        "compliance summary" in lower
        or "compliance checklist" in lower
        or "include compliance" in lower
    )
    if include_summary:
        extracted["include_compliance_summary"] = True

    certs: list[str] = []
    if "us-dot" in lower or "dot" in lower:
        certs.append("US-DOT")
    if "epa-smartway" in lower or "smartway" in lower:
        certs.append("EPA-SmartWay")
    if certs:
        extracted["required_certifications"] = certs

    return extracted


def _resolve_inputs(args: argparse.Namespace) -> dict[str, object]:
    extracted = _extract_from_prompt(args.prompt) if args.prompt else {}

    tire_size = args.tire_size or extracted.get("tire_size", "225/70R19.5")
    load_index = args.load_index or extracted.get("load_index", 120)
    speed_rating = args.speed_rating or extracted.get("speed_rating", "K")
    region_code = args.region_code or extracted.get("region_code", "TX")
    quantity_needed = args.quantity_needed or extracted.get("quantity_needed", 24)
    replacement_urgency = args.replacement_urgency or extracted.get("replacement_urgency", "medium")
    application = args.application or extracted.get("application", "Regional delivery")

    # CLI certifications override prompt-derived certifications.
    cli_certs = [cert.strip() for cert in args.required_certifications.split(",") if cert.strip()]
    required_certifications = cli_certs if cli_certs else extracted.get("required_certifications", ["US-DOT"])

    include_compliance_summary = args.include_compliance_summary or bool(
        extracted.get("include_compliance_summary", False)
    )

    return ResolvedRequest(
        tire_size=str(tire_size),
        load_index=int(load_index),
        speed_rating=str(speed_rating).upper(),
        region_code=str(region_code).upper(),
        quantity_needed=int(quantity_needed),
        replacement_urgency=str(replacement_urgency),
        application=str(application),
        required_certifications=list(required_certifications),
        include_compliance_summary=include_compliance_summary,
    ).model_dump()


def main() -> int:
    args = parse_args()
    task3 = load_task3_module()

    if not args.prompt.strip():
        args.prompt = input("Enter tire request prompt: ").strip()

    try:
        resolved = _resolve_inputs(args)
    except ValidationError as exc:
        print(json.dumps({"error": "invalid_request", "details": exc.errors()}, indent=2))
        return 2

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

    output = {
        "resolved_request": resolved,
        "response": response,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
