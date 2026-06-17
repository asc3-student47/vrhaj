## ADDED Requirements

### Requirement: Application folder scaffold SHALL be explicit
The repository SHALL define an application-facing folder scaffold with clear ownership of orchestration, shared models, integration helpers, data loading, and tests.

#### Scenario: Core scaffold locations are present
- **WHEN** a contributor inspects the repository root for application code
- **THEN** the scaffold includes `tools/`, `data/`, and `tests/` as the primary folder boundaries for implementation work

### Requirement: Planned orchestration and model responsibilities SHALL be documented
The system SHALL document that orchestration flow logic belongs in planned `agent.py` and reusable shared contracts belong in planned `models.py`.

#### Scenario: Contributor reads ownership guidance
- **WHEN** a contributor reviews repository documentation
- **THEN** ownership guidance clearly identifies planned `agent.py` and `models.py` responsibilities

### Requirement: Missing scaffold files SHALL remain out of scope for this change
This change SHALL NOT create missing application module or scaffold test files.

#### Scenario: File creation scope check
- **WHEN** this scaffolding change is implemented
- **THEN** missing files such as planned `agent.py`, planned `models.py`, and new scaffold placeholder tests are deferred to a future implementation change

### Requirement: Integration concerns SHALL be organized under tools package
The system SHALL establish `tools/` as the integration boundary where concern-specific modules will be added in future implementation work.

#### Scenario: Integration boundary exists
- **WHEN** contributors inspect scaffold folders
- **THEN** `tools/` exists for future concern-specific integration modules

### Requirement: Data-loading helpers SHALL be isolated from orchestration
The system SHALL establish `data/` as the dedicated boundary for future shared data-loading and access helpers.

#### Scenario: Data-loading boundary exists
- **WHEN** contributors inspect scaffold folders
- **THEN** `data/` exists as the future location for reusable loading utilities

### Requirement: Scaffolding documentation SHALL be updated
The system SHALL update repository documentation to reflect the folder scaffold, ownership boundaries, and deferred file creation scope.

#### Scenario: README reflects current scaffold scope
- **WHEN** a contributor reads project documentation
- **THEN** the documentation states that this change adds folder structure and updates guidance, while missing module files remain deferred

### Requirement: Existing process and subsystem directories SHALL remain unchanged
The system SHALL preserve existing directory layouts under `openspec/` and `subsystem/` during this scaffolding change.

#### Scenario: Contributor reviews structural change scope
- **WHEN** the scaffolding update is applied
- **THEN** there are no structural modifications to existing folders inside `openspec/` or `subsystem/`
