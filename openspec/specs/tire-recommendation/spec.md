# Tire Recommendation

## Requirement: Rank only compliant candidates
The system SHALL compute recommendation scores only for compliance-eligible SKUs.

#### Scenario: Exclude ineligible items from scoring
- GIVEN a candidate list with compliant and non-compliant SKUs
- WHEN ranking execution begins
- THEN non-compliant SKUs are excluded from scoring
- AND only compliant SKUs appear in ranked outputs

## Requirement: Weighted objective scoring
The system SHALL calculate a configurable weighted score for each eligible SKU.

#### Scenario: Compute score breakdown
- GIVEN at least one eligible SKU
- WHEN ranking is performed
- THEN each SKU receives a total score and component scores
- AND component scores include availability, lifecycle cost, fuel impact, and warranty quality

## Requirement: Volume fulfillment preference
The system SHALL prefer options that can satisfy required quantity within urgency constraints.

#### Scenario: Prioritize fulfillable options
- GIVEN two eligible SKUs with similar total cost
- WHEN one SKU can satisfy `quantity_needed` within required lead time and the other cannot
- THEN the fulfillable SKU ranks higher
- AND the fulfillment rationale is included in explanation output

## Requirement: Deterministic tie-breaking
The system SHALL apply deterministic tie-breakers for equal total scores.

#### Scenario: Stable ordering for equal scores
- GIVEN multiple SKUs have identical total score
- WHEN final ordering is generated
- THEN ordering is resolved using a documented tie-break rule
- AND repeated runs with unchanged inputs return the same order
