## 1. Budgeting Subsystem Foundations

- [ ] 1.1 Define budgeting request/response models with `total_cost` input and allow/deny decision output
- [ ] 1.2 Implement mock budget data loader and validation for single-cost-center MVP assumptions
- [ ] 1.3 Implement contract-aware budget evaluation entry point in `subsystem/budgeting-system/`

## 2. Decision and Validation Logic

- [ ] 2.1 Implement `total_cost`-only request validation and rejection of unsupported `unit_cost`/`count` payloads
- [ ] 2.2 Implement allow/deny decision rules against available budget
- [ ] 2.3 Implement deny reason codes for `invalid_cost_input` and `insufficient_budget`

## 3. Testing and Integration Readiness

- [ ] 3.1 Add subsystem tests for request validation, including unsupported `unit_cost`/`count` payload rejection
- [ ] 3.2 Add subsystem tests for allow and deny outcomes, including required deny reason coverage
- [ ] 3.3 Validate procurement-handoff contract expectations for budget-gate blocking and pass-through behavior
