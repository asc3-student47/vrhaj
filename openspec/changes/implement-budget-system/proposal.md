## Why

The requisition workflow currently evaluates compliance and supplier eligibility but lacks a budget gate before purchase-order generation. This creates risk of producing purchase orders that exceed available funds and requires late manual intervention.

## What Changes

- Add a budgeting subsystem capability that evaluates whether a purchase order can be approved against available budget.
- Support only `total_cost` as the budgeting input for evaluation.
- Evaluate budget eligibility using a provided supplier `contract_id` so the decision is traceable to the selected supplier contract.
- Return a structured budget decision with response code `allow` or `deny`.
- When decision is `deny`, return explicit machine-readable denial reasons.
- Apply MVP assumptions that one cost center exists for all requests.
- Mark contract lookup failure handling as out of scope for this change.
- Mark procurement handoff integration as out of scope for this change.

## Capabilities

### New Capabilities
- `budget-system-lookup`: Budget decision API behavior for purchase-order eligibility checks using contract ID and `total_cost` input.

### Out of Scope Capabilities
- `procurement-handoff`: Budget-gate integration into handoff behavior is deferred and not included in this change.

## Impact

- Adds new implementation under `subsystem/budgeting-system/` and uses mock data from `subsystem/budgeting-system/mock/budgets-db.json`.
- Adds tests for request validation, allow/deny outcomes, and denial-reason coverage.
- Does not update procurement handoff behavior in this change.
- No external dependencies required for MVP implementation.
