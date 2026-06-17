# Tire Compliance

Boundary note: this capability defines legal/policy compliance semantics and escalation behavior; low-level record lookup and request-to-record matching live in `compliance-system-lookup`.

## Requirement: Size and rating eligibility
The system SHALL evaluate eligibility using tire specifications returned by the compliance subsystem lookup and only consider tires that satisfy required fitment and intended-use attributes for the request.

#### Scenario: Reject mismatched fitment
- GIVEN a request includes `tire_size`, `load_index`, `speed_rating`, and `application`
- WHEN a lookup result does not satisfy one or more required attributes
- THEN that SKU is marked ineligible
- AND each failing attribute is recorded in compliance results

## Requirement: Regional legal and certification checks
The system SHALL enforce regional regulatory constraints using SKU certifications and supported region codes from compliance lookup data before recommendation ranking.

#### Scenario: Reject uncertified or unsupported SKU for region
- GIVEN a request includes `region_code`
- WHEN a SKU lacks required certification or does not include that region in supported region codes
- THEN that SKU is marked legally non-compliant
- AND it is excluded from recommendation candidates

## Requirement: Policy version traceability
The system SHALL attach policy source metadata to each compliance evaluation.

#### Scenario: Record policy source for decision
- GIVEN compliance evaluation is executed
- WHEN pass/fail outcomes are produced
- THEN each outcome includes policy version and evaluation timestamp
- AND results are retrievable for audit review

## Requirement: Ambiguity escalation
The system SHALL flag ambiguous compliance outcomes for human review.

#### Scenario: Escalate unresolved policy conflict
- GIVEN regional and company rules produce contradictory outcomes
- WHEN the system cannot resolve precedence deterministically
- THEN the request is marked as requiring human review
- AND no auto-recommendation is finalized
