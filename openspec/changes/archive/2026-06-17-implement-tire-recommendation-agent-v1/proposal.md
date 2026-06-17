## Why

The repository already defines modular specs for compliance gating, ranking, and inventory/procurement handoff, but implementation coverage is incomplete and fragmented. This change delivers a cohesive v1 tire recommendation agent flow that enforces compliance first, ranks only eligible SKUs, and returns deterministic search/recommendation outputs.

## What Changes

- Implement an end-to-end recommendation pipeline that follows the layered architecture:
  1) compliance eligibility gate,
  2) recommendation scoring,
  3) procurement handoff response shaping.
- Extend contracts to support v1 request and output fields needed by ranking and fulfillment preference.
- Add deterministic behavior and explainability outputs required by specs.
- Add tests for compliant/non-compliant filtering, score ordering, tie-breaking, and explicit no-match responses.

## Capability Mapping

### Modified Capabilities

- `tire-compliance`
  - Enforce fitment, legal/certification, policy traceability, and ambiguity escalation in recommendation pre-filtering.
- `tire-recommendation`
  - Score only eligible candidates with weighted components and deterministic tie-break behavior.
- `procurement-handoff`
  - Provide deterministic ranked inventory response contracts, conditional compliance detail, and explicit no-match payloads.

## Scope Boundaries (v1)

In scope:
- Compliance-first recommendation decision flow.
- Weighted ranking with availability, lifecycle cost, fuel impact, warranty, and fulfillment-aware preference.
- Deterministic response ordering and machine-readable no-match reasons.

Out of scope:
- Dynamic route optimization.
- Predictive maintenance model training beyond existing thresholds.
- Autonomous PO submission without human approval.
- Persona-specific dedicated workflows beyond Fleet Manager.
- Expanded cross-functional governance workflow automation.

## Impact

- Affected subsystems: compliance-system and supplier-database data/lookup usage.
- Affected specs: tire-compliance, tire-recommendation, procurement-handoff.
- Test surface: compliance filtering, scoring determinism, no-match semantics, conditional response verbosity.
