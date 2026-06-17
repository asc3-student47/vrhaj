## Context

The fleet tire workflow needs a supplier selection step after compliance checks, but there is no concrete supplier subsystem implementation in the repository today. Supplier data already exists in mock JSON and includes contract expiration, quantity, preferred supplier flags, and lead-time fields, which is enough to support deterministic MVP matching behavior.

The design must support request-time filtering by SKU, required quantity, and requested delivery/lead time while preserving clear explainability of why contracts are included or excluded. The result should be immediately consumable by downstream recommendation and budgeting flow.

## Goals / Non-Goals

**Goals:**

- Define a supplier lookup and evaluation flow over mock supplier contracts.
- Enforce hard inclusion rules: active contract, sufficient quantity, and lead-time feasibility.
- Return deterministic, ranked results with preferred suppliers first.
- Preserve traceable reasoning to support user-facing explanation and debugging.

**Non-Goals:**

- Building production persistence or contract synchronization.
- Solving multi-contract optimization across suppliers beyond simple ranking.
- Automated purchase-order submission or supplier-side API integration.
- Changes to procurement-handoff requirements or response contracts.

## Decisions

1. Use existing JSON supplier data as the source of truth for MVP.
- Rationale: deterministic, local, and already aligned with repository subsystem layout.
- Alternative considered: introducing SQLite-backed supplier store.
- Why not now: additional schema and migration complexity is unnecessary for this stage.

2. Evaluate supplier eligibility as strict request-vs-contract hard filters.
- Rationale: required criteria (active contract, quantity, lead time) are deterministic and should gate inclusion.
- Alternative considered: scoring partially matching contracts.
- Why not now: increases ambiguity and risks returning unusable options.

3. Rank eligible results with preferred-first ordering, then stable tie-breakers.
- Rationale: user requirement explicitly prioritizes preferred suppliers while deterministic ordering avoids flaky behavior.
- Alternative considered: sort solely by price or lead time.
- Why not now: would violate requested business preference ordering.

4. Normalize date comparison around evaluation date (today).
- Rationale: contract activity is a time-bound hard constraint and must be interpreted consistently.
- Alternative considered: treating missing/invalid dates as active.
- Why not now: unsafe default that may surface expired contracts.

## Risks / Trade-offs

- [Mock data inconsistency] -> Validate required contract fields and return explicit exclusion reasons for malformed records.
- [Ranking policy drift] -> Keep ranking policy explicit in spec and tests (preferred first, deterministic tie-breakers).
- [Edge cases around lead time semantics] -> Define lead-time check against requested maximum lead time and document expected units.
- [Date boundary ambiguity] -> Specify contract active rule relative to current date and test boundary scenarios.

## Migration Plan

- Add/extend supplier subsystem lookup logic under subsystem/supplier-system.
- Reuse subsystem/supplier-system/mock/suppliers-db.json as the runtime mock model.
- Add tests for eligibility filters, no-match handling, and preferred-first ordering.
- Rollback strategy: revert supplier subsystem additions and related tests; no persistent migration required.

## Open Questions

- Should contract expiration be strictly greater than today or inclusive of same-day expiration?
- If lead-time and quantity both pass, should secondary ordering prefer lower price or shorter lead time?
- Should expedited lead-time fields participate in eligibility for MVP or remain out of scope until explicitly requested?
