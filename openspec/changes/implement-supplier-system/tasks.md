## 1. Supplier Subsystem Foundation

- [ ] 1.1 Create supplier subsystem module structure under subsystem/supplier-system.
- [ ] 1.2 Define supplier lookup request and structured result contracts.
- [ ] 1.3 Implement JSON loading utility for supplier records and contracts from subsystem/supplier-system/mock/suppliers-db.json.

## 2. Supplier Eligibility and Ranking Logic

- [ ] 2.1 Implement contract lookup by requested tire SKU.
- [ ] 2.2 Implement eligibility checks for active contract date, sufficient quantity, and requested lead-time feasibility.
- [ ] 2.3 Implement deterministic preferred-first result ordering and include explicit inclusion/exclusion reasons per evaluated contract.

## 3. Integration and Validation

- [ ] 3.1 Add tests for eligible supplier matches and preferred-first ordering.
- [ ] 3.2 Add tests for exclusion paths: expired contracts, insufficient quantity, and lead-time mismatch.
- [ ] 3.3 Add no-match scenario coverage for requests with no eligible supplier contracts.
