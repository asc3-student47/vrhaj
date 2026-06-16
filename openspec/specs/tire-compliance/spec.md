# Tire Compliance

## Requirement: Size and rating eligibility
The system SHALL only consider tires that match required fitment attributes for the request.

#### Scenario: Reject mismatched fitment
- GIVEN a request includes `tire_size`, `load_index`, and `speed_rating`
- WHEN a catalog SKU does not support one or more required fitment attributes
- THEN that SKU is marked ineligible
- AND the ineligibility reason is recorded in compliance results

## Requirement: Regional legal and certification checks
The system SHALL enforce regional regulatory constraints before recommendation ranking.

#### Scenario: Reject uncertified SKU for region
- GIVEN a request includes `region_code`
- WHEN a SKU lacks required regional certification
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
