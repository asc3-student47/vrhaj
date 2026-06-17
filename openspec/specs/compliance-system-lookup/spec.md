# Compliance System Lookup

Boundary note: this capability defines record retrieval and request-to-record rule evaluation behavior; policy governance and legal ambiguity handling live in `tire-compliance`.

## Requirement: Tire specification lookup from mock database
The compliance subsystem SHALL load tire model records from a JSON mock database and resolve records by SKU and/or fitment attributes.

#### Scenario: Resolve tire record by SKU
- GIVEN a compliance request includes a SKU that exists in the mock database
- WHEN lookup is executed
- THEN the subsystem returns the corresponding tire specification record for evaluation

#### Scenario: No record found for lookup keys
- GIVEN a compliance request references a SKU or fitment combination not present in the mock database
- WHEN lookup is executed
- THEN the subsystem returns a non-compliant outcome with a reason indicating missing tire specification data

## Requirement: Request-fit evaluation rules
The compliance subsystem SHALL evaluate tire records against request constraints for size, minimum load index, minimum speed rating, intended application, and operating region.

#### Scenario: Mark record compliant when all rules pass
- GIVEN a tire record and request constraints
- WHEN the tire record satisfies all requested constraints
- THEN the subsystem marks the tire as compliant

#### Scenario: Mark record non-compliant when one or more rules fail
- GIVEN a tire record and request constraints
- WHEN a tire record fails any requested constraint
- THEN the subsystem marks the tire as non-compliant and lists each failed rule in the result

## Requirement: Structured compliance response
The compliance subsystem SHALL return a structured result containing compliance status and decision reasons for every evaluated tire record.

#### Scenario: Return pass result with traceable reasoning
- GIVEN a compliance evaluation completes with no failed rules
- WHEN the result is generated
- THEN the result includes status compliant and a reason list confirming rule satisfaction

#### Scenario: Return fail result with explicit reasons
- GIVEN a compliance evaluation completes with failed rules
- WHEN the result is generated
- THEN the result includes status non_compliant and a reason list describing each failed requirement
