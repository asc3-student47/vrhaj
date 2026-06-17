## ADDED Requirements

Out-of-scope note: Contract lookup failure handling (for missing or unresolvable `contract_id`) is out of scope for this change.
Out-of-scope note: `unit_cost` and `count` request formats are out of scope for this change.

### Requirement: Budget lookup by contract and total cost
The budgeting subsystem SHALL evaluate purchase-order eligibility using the provided `contract_id` and `total_cost` from the request.

#### Scenario: Evaluate request with total_cost input
- **WHEN** a request includes `contract_id` and `total_cost`
- **THEN** the subsystem uses `total_cost` as the effective total cost for budget evaluation

### Requirement: Input validation for supported cost formats
The budgeting subsystem SHALL enforce a `total_cost`-only payload contract.

#### Scenario: Reject unsupported unit-cost payload
- **WHEN** a request includes `unit_cost` and/or `count`
- **THEN** the subsystem returns response code `deny` with reason code `invalid_cost_input`

#### Scenario: Reject missing cost payload
- **WHEN** a request omits `total_cost`
- **THEN** the subsystem returns response code `deny` with reason code `invalid_cost_input`

### Requirement: Allow/Deny decision contract
The budgeting subsystem SHALL return a structured response with response code `allow` or `deny`.

#### Scenario: Return allow when sufficient budget exists
- **WHEN** effective total cost is less than or equal to available budget for the single MVP cost center
- **THEN** the subsystem returns response code `allow`

#### Scenario: Return deny when budget is insufficient
- **WHEN** effective total cost exceeds available budget for the single MVP cost center
- **THEN** the subsystem returns response code `deny`
- **THEN** the subsystem includes reason code `insufficient_budget`

### Requirement: Denial reason coverage
The budgeting subsystem SHALL include at least one machine-readable reason code whenever response code is `deny`.

#### Scenario: Include reason code for denied evaluation
- **WHEN** response code is `deny`
- **THEN** the response includes one or more machine-readable denial reason codes
