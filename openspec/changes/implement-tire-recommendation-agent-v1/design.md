## Context

The spec architecture defines a strict layering model: hard compliance eligibility before soft optimization, followed by stable handoff outputs. The current implementation has compliance primitives but does not yet provide a complete v1 recommendation service aligned across all three capability specs.

## Goals / Non-Goals

Goals:
- Implement a traceable compliance gate that excludes non-compliant SKUs from downstream ranking.
- Implement weighted recommendation scoring with deterministic tie-breaking.
- Implement procurement handoff response contracts with optional compliance detail and explicit no-match semantics.
- Preserve explainability from rule-level outcomes through final ranked recommendation output.

Non-Goals:
- Building optimization across route/network planning.
- Human workflow orchestration for approvals and governance.
- Autonomous external system execution (for example PO placement).

## Architecture

Decision pipeline:
1. Normalize request input (`tire_size`, `load_index`, `speed_rating`, `region_code`, `quantity_needed`, urgency).
2. Build candidate pool from inventory/supplier records.
3. Run compliance evaluation and exclude ineligible SKUs.
4. Score eligible SKUs with weighted components.
5. Apply deterministic tie-breakers for stable order.
6. Build procurement handoff payload with conditional compliance evidence.
7. Return explicit no-match response when no candidate can satisfy required constraints.

## Spec-to-Design Traceability

### tire-compliance

- Size/rating eligibility:
  - Reuse compliance lookup fields and fail per-attribute with explicit failed rules.
- Regional legal and certification checks:
  - Require region support and required certifications before ranking.
- Policy version traceability:
  - Include policy version and evaluation timestamp on each compliance decision.
- Ambiguity escalation:
  - Emit `requires_human_review` and suppress auto-recommendation when precedence conflict is unresolved.

### tire-recommendation

- Rank only compliant candidates:
  - Candidate set for scoring is compliance-pass only.
- Weighted objective scoring:
  - Score components: availability, lifecycle cost, fuel impact, warranty quality.
- Volume fulfillment preference:
  - Prefer SKUs satisfying `quantity_needed` within urgency lead-time constraints.
- Deterministic tie-breaking:
  - Tie-break sequence: higher fulfillment score, shorter lead time, lower unit cost, then SKU lexical ascending.

### procurement-handoff

- Inventory query filtering:
  - Apply fitment/region/availability filters before response construction.
- Result ranking for search relevance:
  - Return deterministic ranked list from recommendation order.
- Conditional compliance detail:
  - Include detailed compliance checklist only when `include_compliance_summary=true`.
- Explicit no-match response:
  - Return no-match status with reason codes and policy-allowed relaxation dimensions.

## Data Contracts (v1)

Input minimums:
- tire_size
- load_index
- speed_rating
- region_code
- quantity_needed
- replacement_urgency
- include_compliance_summary (optional)

Output minimums:
- recommendation_id
- ranked_skus
- score_breakdown per SKU
- compliance_status per SKU (minimal by default)
- compliance_summary (optional detailed)
- no_match (status + reason_codes + suggested_relaxations)

## Risks / Trade-offs

- Overly strict compliance filtering can increase no-match frequency.
  - Mitigation: explicit reason codes and policy-allowed relaxation suggestions.
- Scoring weight tuning can destabilize expected ranking outcomes.
  - Mitigation: versioned weight profiles and deterministic tie-break assertions in tests.
- Data quality gaps in supplier records can degrade fulfillment ranking.
  - Mitigation: input validation and graceful degradation with explanation fields.

## Validation Strategy

- Unit tests for compliance pass/fail exclusion and ambiguity escalation.
- Unit tests for score component math and deterministic tie ordering.
- Contract tests for default/minimal compliance output and verbose compliance output.
- Contract tests for explicit no-match payload including reason codes.
