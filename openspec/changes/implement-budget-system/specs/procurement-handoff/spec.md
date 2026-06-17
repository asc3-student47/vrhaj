## MODIFIED Requirements

### Requirement: Explicit no-match response
The system SHALL return structured no-match information when no inventory satisfies required constraints, including explicit budget-gate outcomes.

#### Scenario: Return no-match outcome
- GIVEN no SKU satisfies fitment, compliance, availability, and budget constraints
- WHEN search response is generated
- THEN response includes a no-match status and machine-readable reason codes
- AND response includes suggested relaxation dimensions such as lead time or preferred brand when allowed by policy
- AND response includes budget denial reason codes when budget gate returns `deny`

## ADDED Requirements

### Requirement: Budget gate in procurement handoff
The system SHALL include budget eligibility in procurement handoff before a purchase order can be generated.

#### Scenario: Block handoff on budget deny
- GIVEN compliance and supplier checks are otherwise eligible
- WHEN budget system returns response code `deny`
- THEN procurement handoff marks the request as blocked
- AND no purchase-order draft is generated
- AND budget denial reason codes are included in handoff output

#### Scenario: Permit handoff on budget allow
- GIVEN compliance and supplier checks are eligible
- WHEN budget system returns response code `allow`
- THEN procurement handoff remains eligible for purchase-order draft generation
