## ADDED Requirements

### Requirement: Preferred supplier ordering in inventory search output
The system SHALL preserve supplier-system preferred-first ranking when returning supplier-backed inventory search results.

#### Scenario: Return preferred suppliers before non-preferred suppliers
- **WHEN** procurement search returns multiple eligible supplier-backed options for the same request
- **THEN** options from preferred suppliers appear before non-preferred suppliers
- **AND** ordering remains deterministic for unchanged input
