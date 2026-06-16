# Delta for Process

## ADDED Requirements

### Requirement: Spec-first change management
The project SHALL require each non-trivial feature or behavior change to start with an OpenSpec proposal artifact.

#### Scenario: Start new feature work
- GIVEN a contributor wants to add or modify behavior
- WHEN they begin work
- THEN they create a change in `openspec/changes/<change-name>/`
- AND they document intent and scope in `proposal.md` before implementation

### Requirement: Standard implementation flow
The project SHALL use the default OpenSpec flow commands for delivery.

#### Scenario: Deliver approved change
- GIVEN a change proposal and tasks exist
- WHEN implementation starts
- THEN contributors follow `/opsx:apply`, `/opsx:sync`, and `/opsx:archive`
- AND update artifacts as implementation details evolve
