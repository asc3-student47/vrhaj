# Tire Inventory Search Service

## Requirement: Inventory query filtering
The system SHALL support inventory search using fitment and availability filters.

#### Scenario: Filter inventory by fitment and region
- GIVEN a request includes `tire_size`, `load_index`, `speed_rating`, and `region_code`
- WHEN inventory search is executed
- THEN results include only SKUs matching requested fitment and regional eligibility constraints
- AND each result includes current stock and lead-time fields

## Requirement: Result ranking for search relevance
The system SHALL return a deterministic ranked result set for matching inventory.

#### Scenario: Rank matching inventory results
- GIVEN multiple inventory items satisfy filter criteria
- WHEN search results are returned
- THEN results are ordered by configured relevance priorities including availability and unit cost
- AND repeated runs with unchanged inputs return the same ordering

## Requirement: Conditional compliance detail in search response
The system SHALL include detailed compliance evidence only when explicitly requested.

#### Scenario: Omit verbose compliance detail by default
- GIVEN request omits `include_compliance_summary` or sets it to false
- WHEN search response is generated
- THEN detailed compliance checklist fields are omitted
- AND a minimal compliance status indicator remains available

## Requirement: Explicit no-match response
The system SHALL return structured no-match information when no inventory satisfies required constraints.

#### Scenario: Return no-match outcome
- GIVEN no SKU satisfies fitment, compliance, and availability constraints
- WHEN search response is generated
- THEN response includes a no-match status and machine-readable reason codes
- AND response includes suggested relaxation dimensions such as lead time or preferred brand when allowed by policy
