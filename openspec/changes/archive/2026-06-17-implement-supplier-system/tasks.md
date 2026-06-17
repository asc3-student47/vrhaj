## 1. Supplier Subsystem Foundation

- [x] 1.1 Create supplier subsystem module structure under subsystem/supplier-system.
- [x] 1.2 Define supplier lookup request and structured result contracts.
- [x] 1.3 Implement JSON loading utility for supplier records and contracts from subsystem/supplier-system/mock/suppliers-db.json.

## 2. Supplier Eligibility and Ranking Logic

- [x] 2.1 Implement contract lookup by requested tire SKU.
- [x] 2.2 Implement eligibility checks for active contract date, sufficient quantity, and requested lead-time feasibility.
- [x] 2.3 Implement deterministic preferred-first result ordering and include explicit inclusion/exclusion reasons per evaluated contract.

## 3. Validation

- [x] 3.1 Add tests for eligible supplier matches and preferred-first ordering.
- [x] 3.2 Add tests for exclusion paths: expired contracts, insufficient quantity, and lead-time mismatch.
- [x] 3.3 Add no-match scenario coverage for requests with no eligible supplier contracts.
