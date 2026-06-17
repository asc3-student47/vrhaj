## Why

The requisition workflow requires supplier matching after compliance, but the repository currently has no concrete supplier subsystem. Adding it now enables deterministic supplier selection based on contract validity, inventory sufficiency, and delivery constraints.

## What Changes

- Add a supplier subsystem that loads supplier contracts from mock JSON and matches suppliers by requested tire SKU, quantity, and requested lead time.
- Enforce inclusion criteria for matching: active contract as of evaluation date, sufficient available quantity, and lead time that satisfies the request.
- Return ranked supplier matches with preferred suppliers listed first while preserving deterministic ordering.
- Add structured match results with explicit inclusion/exclusion reasons per evaluated supplier contract.

## Capabilities

### New Capabilities
- `supplier-system-lookup`: Lookup and rank suppliers from mock contract data using SKU, quantity, lead-time, and contract validity constraints.

### Modified Capabilities
- `procurement-handoff`: Add requirement-level behavior that supplier search output is sourced from supplier-system matching and preserves preferred-first ordering semantics.

## Impact

- Affected systems: new supplier subsystem under subsystem assets and its mock database usage.
- Affected specs: new capability spec for supplier-system-lookup and delta updates for procurement-handoff search behavior.
- Affected tests: supplier matching scenarios for inclusion criteria, ordering, and no-match outcomes.
