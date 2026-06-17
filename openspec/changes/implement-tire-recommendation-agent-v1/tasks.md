## 1. tire-compliance implementation

- [x] 1.1 Integrate compliance lookup into recommendation candidate preprocessing.
- [x] 1.2 Enforce fitment and legal/certification checks as hard eligibility gates.
- [x] 1.3 Attach policy version and evaluation timestamp to each compliance outcome.
- [x] 1.4 Add ambiguity escalation output (`requires_human_review`) and block auto-final recommendation on unresolved policy conflict.
- [x] 1.5 Add tests for eligibility failures, legal/cert failures, traceability fields, and escalation behavior.

## 2. tire-recommendation implementation

- [x] 2.1 Build scoring flow that accepts only compliance-eligible candidates.
- [x] 2.2 Implement configurable weighted score components: availability, lifecycle cost, fuel impact, warranty quality.
- [x] 2.3 Implement fulfillment-aware ranking preference using `quantity_needed` and urgency lead-time constraints.
- [x] 2.4 Implement deterministic tie-break rules and document ordering behavior.
- [x] 2.5 Add tests for component score breakdown, fulfillment preference ordering, and stable ties across repeated runs.

## 3. procurement-handoff implementation

- [ ] 3.1 Implement inventory query filtering for fitment, region, and availability constraints.
- [ ] 3.2 Return deterministic ranked response aligned to recommendation order.
- [ ] 3.3 Support conditional compliance detail output (minimal default, verbose when requested).
- [ ] 3.4 Implement explicit no-match response with machine-readable reason codes and suggested relaxation dimensions.
- [ ] 3.5 Add contract tests for default response, verbose response, and no-match payload structure.

## 4. integration and release readiness

- [ ] 4.1 Add end-to-end tests validating compliance gating to ranked recommendations to handoff outputs.
- [ ] 4.2 Verify v1 scope boundaries remain enforced (no autonomous PO submission, no route optimization workflows).
- [ ] 4.3 Document config defaults for scoring weights and tie-break priorities.
- [ ] 4.4 Update implementation notes to show traceability from code paths to the three capability specs.
