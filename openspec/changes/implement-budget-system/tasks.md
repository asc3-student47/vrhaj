## 1. Budgeting Subsystem Foundations

- [ ] 1.1 Define budgeting request/response models with required `contract_id` and `total_cost`, plus `allow`/`deny` output
- [ ] 1.2 Implement mock budget data loader for `subsystem/budgeting-system/mock/budgets-db.json` and validate single-cost-center shape
- [ ] 1.3 Implement budget evaluation entry point in `subsystem/budgeting-system/` that treats `contract_id` as traceability metadata (not budget-record selector)

## 2. Decision and Validation Logic

- [ ] 2.1 Implement `total_cost`-only request validation and reject unsupported `unit_cost`/`count` payloads with `deny` + `invalid_cost_input`
- [ ] 2.2 Implement deterministic decision boundary: `allow` when `total_cost <= remaining`, else `deny` + `insufficient_budget`
- [ ] 2.3 Include response echo fields (`contract_id`, `total_cost`, `cost_center_id`) to support handoff auditability

## 3. Testing and Integration Readiness

- [ ] 3.1 Add subsystem validation tests for missing, non-numeric, non-positive `total_cost`, and unsupported `unit_cost`/`count` payloads
- [ ] 3.2 Add subsystem decision tests for boundary conditions (`total_cost == remaining`, `< remaining`, `> remaining`) with deny reason coverage
