## ADDED Requirements

### Requirement: Application module scaffold SHALL be explicit
The repository SHALL define an application-facing scaffold with clear ownership of orchestration, shared models, integration helpers, data loading, and tests.

#### Scenario: Core scaffold locations are present
- **WHEN** a contributor inspects the repository root for application code
- **THEN** the scaffold includes `agent.py`, `models.py`, `tools/`, `data/`, and `tests/` as the primary implementation locations

### Requirement: Orchestration and model responsibilities SHALL be separated
The system SHALL keep orchestration flow logic in `agent.py` and reusable shared contracts in `models.py`.

#### Scenario: New orchestration behavior is added
- **WHEN** a change adds or updates request flow orchestration
- **THEN** the behavior is implemented in `agent.py` and not in integration helper modules

#### Scenario: Shared data contracts are introduced
- **WHEN** a change introduces reusable domain structures used by multiple modules
- **THEN** the structures are defined in `models.py`

### Requirement: Integration concerns SHALL be organized under tools package
The system SHALL place external system helper modules under `tools/` and separate them by concern (`budget`, `compliance`, `vendor`).

#### Scenario: A compliance helper is implemented
- **WHEN** a contributor adds compliance-system integration behavior
- **THEN** the implementation is added under `tools/compliance.py`

#### Scenario: A supplier helper is implemented
- **WHEN** a contributor adds supplier database integration behavior
- **THEN** the implementation is added under `tools/vendor.py`

### Requirement: Data-loading helpers SHALL be isolated from orchestration
The system SHALL place shared data-loading and access helper logic under `data/`.

#### Scenario: Data-loading utilities are required by multiple modules
- **WHEN** the project needs reusable data loading behavior
- **THEN** the reusable logic is implemented in `data/loader.py` and consumed by orchestration or tool modules as needed

### Requirement: Existing process and subsystem directories SHALL remain unchanged
The system SHALL preserve existing directory layouts under `openspec/` and `subsystem/` during this scaffolding change.

#### Scenario: Contributor reviews structural change scope
- **WHEN** the scaffolding update is applied
- **THEN** there are no structural modifications to existing folders inside `openspec/` or `subsystem/`
