# Fleet Tire Management

## Requirement: Tire inventory tracking
The system SHALL maintain a current list of all fleet tires with unique identifiers and assignment status.

#### Scenario: Register tire
- GIVEN an authorized fleet operator
- WHEN they add a tire record with required metadata
- THEN the tire appears in inventory with an unassigned status

## Requirement: Maintenance visibility
The system SHALL show maintenance status and due dates for each tire.

#### Scenario: View due maintenance
- GIVEN a tire has a scheduled rotation or inspection date
- WHEN a user views the tire details
- THEN the next maintenance date is visible
