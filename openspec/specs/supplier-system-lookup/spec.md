# Supplier System Lookup

## Requirement: Supplier contract lookup by SKU
The system SHALL load supplier records from the supplier mock database and evaluate contracts that match the requested tire SKU.

#### Scenario: Find contracts for requested SKU
- GIVEN a request includes a SKU present in one or more supplier contracts
- WHEN lookup is executed
- THEN the system returns those matching contracts as candidates for eligibility evaluation

## Requirement: Active contract eligibility
The system SHALL include only active contracts in supplier matching results.

#### Scenario: Exclude expired contract
- GIVEN a matching contract is found for the requested SKU
- WHEN contract expiration date is on or before the evaluation date
- THEN that contract is excluded from results with a non-eligibility reason indicating inactive contract

## Requirement: Quantity eligibility
The system SHALL include only supplier contracts with enough available quantity to satisfy the requested tire count.

#### Scenario: Exclude insufficient quantity contract
- GIVEN a matching contract is found for the requested SKU
- WHEN available quantity is less than requested quantity
- THEN that contract is excluded from results with a non-eligibility reason indicating insufficient quantity

## Requirement: Lead-time eligibility
The system SHALL include only supplier contracts that can satisfy the requested delivery lead time.

#### Scenario: Exclude contract with excessive lead time
- GIVEN a matching contract is found for the requested SKU
- WHEN contract lead time is greater than the requested lead time
- THEN that contract is excluded from results with a non-eligibility reason indicating lead-time mismatch

## Requirement: Preferred-first deterministic ranking
The system SHALL rank eligible supplier results with preferred suppliers first and deterministic ordering for ties.

#### Scenario: Order eligible suppliers with preferred first
- GIVEN multiple eligible supplier contracts are returned for a request
- WHEN supplier results are ordered
- THEN preferred suppliers appear before non-preferred suppliers
- AND repeated runs with unchanged input return the same ordering

## Requirement: Structured supplier lookup response
The system SHALL return structured results that include eligibility status and reasons for each evaluated contract.

#### Scenario: Return explicit eligibility reasons
- GIVEN supplier evaluation completes
- WHEN results are generated
- THEN each evaluated contract includes eligibility status and machine-readable reasons for inclusion or exclusion
