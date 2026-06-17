## Context

The codebase currently emphasizes subsystem mocks and OpenSpec artifacts, but application-facing Python modules do not yet follow a shared scaffold. Contributors can identify runtime behavior from specs, but it is less obvious where to place orchestration logic, reusable models, integration wrappers, data loaders, and targeted tests.

This change defines a lightweight, module-first structure to improve discoverability and ownership while preserving existing `openspec/` and `subsystem/` layouts.

## Goals / Non-Goals

**Goals:**
- Establish a clear top-level Python scaffold centered on `agent.py` and `models.py`.
- Define responsibility boundaries for `tools/`, `data/`, and `tests/`.
- Keep the structure simple enough for MVP iteration while reducing ambiguity for future implementation work.
- Preserve current OpenSpec and subsystem directory structures.

**Non-Goals:**
- Changing compliance, budgeting, vendor lookup, recommendation, or procurement runtime behavior.
- Introducing deployment, packaging, or production infrastructure changes.
- Refactoring existing subsystem mock data locations.
- Defining detailed internal APIs for every module beyond ownership and placement expectations.

## Decisions

1. Decision: Keep orchestration and shared contracts as explicit top-level modules (`agent.py`, `models.py`).
Rationale: New contributors can quickly locate the interaction entrypoint and shared model definitions without traversing nested packages.
Alternatives considered:
- Move all code into a deep package tree (rejected: unnecessary complexity for MVP).
- Keep only package modules without explicit top-level anchors (rejected: weak discoverability).

2. Decision: Group integration-facing helpers by concern under `tools/` (`budget.py`, `compliance.py`, `vendor.py`).
Rationale: Encapsulates external-system interaction surfaces and limits coupling with orchestration code.
Alternatives considered:
- Put integration logic directly in `agent.py` (rejected: orchestration bloat and poor testability).
- Create one monolithic `tools.py` (rejected: concern mixing and growth risk).

3. Decision: Isolate data loading and access helpers under `data/`.
Rationale: Separates data-source handling from decision orchestration and integration adapters.
Alternatives considered:
- Keep loader helpers inside each tool module (rejected: duplication and inconsistent data access patterns).

4. Decision: Preserve `openspec/` and `subsystem/` trees as stable anchors.
Rationale: These directories already hold active process artifacts and subsystem mocks used by current workflows.
Alternatives considered:
- Restructure existing trees to mirror the new app scaffold (rejected: unnecessary migration overhead and risk).

## Risks / Trade-offs

- [Top-level growth can become crowded] -> Mitigation: Document ownership boundaries and move only when a clear threshold is reached.
- [Module boundaries may still drift over time] -> Mitigation: Enforce responsibility checks in PR review and maintain corresponding tests.
- [Naming ambiguity in simple folder names] -> Mitigation: Keep concern-based naming conventions explicit in follow-on docs and task acceptance criteria.
- [Scaffolding work may trigger accidental behavior changes] -> Mitigation: Keep this change strictly structural and verify no business logic deltas.

## Migration Plan

1. Introduce scaffold files and package directories without altering existing subsystem or OpenSpec trees.
2. Add baseline tests mapped to scaffold ownership boundaries.
3. Confirm existing tests still pass and no runtime behavior changed.
4. Rollback strategy: remove new scaffold files/directories and restore prior layout if tooling or team workflow regressions occur.

## Open Questions

- Should naming conventions for future tool modules be documented in a dedicated contributor guide or in the main README?
- When should the project transition from top-level module anchors to a deeper package structure as complexity grows?
