## Context

The current repo has implemented compliance and supplier lookup subsystems, while budgeting currently has only mock data and no executable subsystem module. The agent workflow in OpenSpec context already expects a budgeting check before finalizing purchase-order preparation.

This change introduces a budgeting decision component that requires `contract_id` for traceability and evaluates `total_cost` against the single shared cost center available budget for MVP.

## Goals / Non-Goals

**Goals:**
- Provide a deterministic budget decision endpoint for the agent workflow.
- Accept only `total_cost` as the request cost input for decision logic.
- Require `contract_id` in requests so budget checks are auditable per selected supplier contract.
- Return structured outcomes with response code `allow`/`deny` and explicit denial reasons.
- Implement MVP assumption of a single shared cost center.

**Non-Goals:**
- Mapping requesters to cost centers.
- Multi-cost-center allocation or budget transfer logic.
- Currency conversion or mixed-currency support.
- Persisting purchase-order commitments (this change only evaluates eligibility).
- Contract lookup failure handling (for missing or unresolvable `contract_id`).
- `unit_cost` and `count` input handling.

## Decisions

### Decision 1: Introduce a dedicated `budget-system-lookup` capability
- Rationale: Budget logic is a separate hard gate from compliance and supplier matching, so a dedicated capability keeps ownership and tests clear.
- Alternatives considered:
  - Embed budget logic into supplier subsystem: rejected due to conflating supplier eligibility with financial policy.
  - Embed budget logic into procurement-handoff only: rejected because lookup/evaluation behavior needs its own testable contract.

### Decision 2: Use total_cost-only request contract
- Rationale: Constraining the API to one cost field reduces ambiguity, validation complexity, and implementation risk for MVP.
- Alternatives considered:
  - Support `unit_cost*count` alongside `total_cost`: rejected due to broader API surface and avoidable input-format ambiguity.

### Decision 3: Denial responses return explicit reason codes
- Rationale: Agent decisions must be explainable and actionable (for user messaging and future automation). Machine-readable reasons allow deterministic downstream behavior.
- Alternatives considered:
  - Free-text reason only: rejected due to poor testability and automation reliability.

### Decision 4: Single cost center modeled as configuration/data default
- Rationale: Matches MVP assumption and avoids introducing out-of-scope routing complexity.
- Alternatives considered:
  - Require cost center in every request: rejected as conflicting with stated assumptions.

### Decision 5: Treat `contract_id` as required traceability metadata in MVP
- Rationale: The current budget data model contains cost-center balances only and does not map contracts to distinct budget buckets. Requiring `contract_id` preserves auditability while avoiding unsupported mapping behavior.
- Alternatives considered:
  - Use `contract_id` to select a budget record: rejected for MVP because no mapping data exists in `budgets-db.json`.

### Decision 6: Define deterministic decision boundary and response echoes
- Rationale: Deterministic budget outcomes improve testability and downstream handoff behavior.
- Rules:
  - `allow` when `total_cost <= remaining` for the MVP cost center.
  - `deny` with `insufficient_budget` when `total_cost > remaining`.
  - `deny` with `invalid_cost_input` when `total_cost` is missing, non-numeric, non-positive, or unsupported `unit_cost`/`count` fields are present.
  - Echo `contract_id`, `total_cost`, and selected `cost_center_id` in responses for audit clarity.

## Risks / Trade-offs

- [Risk] Upstream callers may still send `unit_cost`/`count` payloads from earlier assumptions. -> Mitigation: treat non-`total_cost` formats as unsupported input and return deny with validation reason.
- [Risk] Budget data shape drift in mock JSON could break lookup logic. -> Mitigation: strict load-time schema validation and explicit test fixtures.
- [Risk] Lack of reservation/commit means two concurrent checks could both return `allow`. -> Mitigation: document this as MVP limitation; commitment semantics deferred.
- [Risk] `contract_id` may not exist in known supplier contracts. -> Mitigation: explicitly out of scope for this change; enforce as an upstream integration responsibility.

## Migration Plan

1. Add `budget-system-lookup` delta spec and update `procurement-handoff` spec for budget gate behavior.
2. Implement budgeting subsystem module and request/response dataclasses that encode traceability-only `contract_id` semantics.
3. Add tests for validation matrix, allow/deny boundary conditions, and denial reason outcomes.
4. Integrate budget evaluation into agent orchestration path (in apply phase).
5. Rollback plan: disable budgeting gate call path and keep procurement flow at current behavior while retaining artifacts for future re-enable.

## Open Questions

- Should denial reasons be standardized globally across subsystems or remain capability-local initially?
