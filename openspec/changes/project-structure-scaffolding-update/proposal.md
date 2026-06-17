## Why

The repository has grown around subsystem mocks and OpenSpec artifacts, but the application-facing Python layout is still implicit and inconsistent. Standardizing a lightweight scaffold now will reduce onboarding friction and make future implementation changes easier to locate, review, and test.

## What Changes

- Define a top-level Python scaffolding layout with explicit ownership boundaries for orchestration, shared models, tool integrations, data loading, and tests.
- Add folder scaffolding for `tools/`, `data/`, and maintain `tests/` as the test location.
- Update repository documentation to describe responsibilities, naming conventions, and deferred file creation.
- Defer creation of missing module and test files (for example `agent.py`, `models.py`, and new scaffold test files) to a later implementation-focused change.
- Preserve existing `openspec/` and `subsystem/` directory layouts without restructuring.

## Capabilities

### New Capabilities
- `python-project-scaffolding`: Defines the baseline module structure and file ownership conventions for application-facing development.

### Modified Capabilities
- None.

## Impact

- Affects project layout expectations and contributor guidance for future implementation work.
- Influences contributor workflow, code discovery, and future test placement.
- No runtime business behavior changes to compliance, supplier selection, budgeting, or purchase-order handoff.
- No creation of new application module files in this change.
- No changes to `openspec/` or `subsystem/` directory structures.
