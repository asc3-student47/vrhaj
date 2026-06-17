# Draft Proposal Summary: Project Structure and Scaffolding Update

## Problem
The repository has grown around subsystem and spec artifacts, but the application-facing Python layout is not yet standardized for day-to-day development. This makes navigation harder and slows onboarding when contributors need a clear place for agent logic, tool integrations, shared models, and tests.

## Proposed Solution
Adopt a lightweight, module-first scaffolding structure centered on top-level `agent.py` and `models.py`, with support packages for tools, data loading, and tests.

Scaffolding summary:
1. Keep `agent.py` as the main orchestration entrypoint.
2. Keep `models.py` as the shared contract and model module.
3. Place integration-facing helper logic under `tools/`.
4. Place data access and loading utilities under `data/`.
5. Keep tests organized under `tests/`.
6. Preserve existing `openspec/` and `subsystem/` directories without restructuring.

Key baked-in structural decisions:
- Keep architecture simple and explicit for MVP scaffolding.
- Separate orchestration (`agent.py`) from reusable models (`models.py`).
- Group external system helpers by concern under `tools/` (`budget`, `compliance`, `vendor`).
- Keep data-loading logic isolated from orchestration responsibilities.
- Preserve current OpenSpec and subsystem folder layouts as stable anchors.

## Proposed Directory Tree
```text
fleet-tire-manager/
├── data/
│   ├── __init__.py
│   └── loader.py
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_budget.py
│   ├── test_compliance.py
│   └── test_vendor.py
├── tools/
│   ├── __init__.py
│   ├── budget.py
│   ├── compliance.py
│   └── vendor.py
├── agent.py
├── models.py
├── docs/
│   ├── agent-chat-log.md
│   └── explore-status-lifecycle.md
├── openspec/                      # unchanged
│   ├── config.yaml
│   ├── changes/
│   └── specs/
└── subsystem/                     # unchanged
    ├── budgeting-system/
    ├── compliance-system/
    └── supplier-database/
```

## Scope
In scope for this draft scaffolding update:
- Align the proposal to a simplified top-level Python structure.
- Define ownership for `agent.py`, `models.py`, `tools/`, `data/`, and `tests/`.
- Preserve and reference existing `openspec/` and `subsystem/` directories without modification.
- Clarify where future implementation work should be added within this scaffold.

## Out of Scope
Out of scope for this draft:
- Implementing or changing runtime business logic.
- Modifying compliance, budget, or vendor decision behavior.
- Altering any existing directory layout under `openspec/`.
- Altering any existing directory layout under `subsystem/`.
- Adding production infrastructure, deployment, or scaling work.

## Risks
1. Flat growth risk
Top-level files can become crowded if responsibilities are not enforced.

2. Module coupling risk
Without clear boundaries, `agent.py`, `tools/`, and `models.py` may become tightly coupled.

3. Test drift risk
If tool modules evolve quickly, test coverage can lag unless test ownership stays explicit.

4. Naming ambiguity risk
Simple folder names can become overloaded unless conventions are documented early.

5. Scope creep risk
Scaffolding updates can unintentionally turn into implementation work; this proposal explicitly avoids that.

## Notes
This document is intentionally limited to project structure and scaffolding decisions. It does not authorize or include feature implementation.
