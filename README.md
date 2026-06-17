# fleet-tire-manager
Hallucinators FDE Capstone Project

## OpenSpec flow

This repository now includes an OpenSpec spec-driven workflow under `openspec/`.

### Active proposal

- `openspec/changes/introduce-openspec-flow/proposal.md`
- `openspec/changes/project-structure-scaffolding-update/proposal.md`

### Workflow commands

Use these commands in your AI tool chat to run the default OpenSpec flow:

1. `/opsx:propose <change-name-or-idea>`
2. `/opsx:apply`
3. `/opsx:sync`
4. `/opsx:archive`

### Repository structure

Current structure:

```text
copilot-instructions.md
docs/
└── agent-chat-log.md
openspec/
├── config.yaml
├── specs/
│   ├── spec-architecture.md
│   ├── fleet-tire-management/spec.md
│   ├── procurement-handoff/spec.md
│   ├── tire-compliance/spec.md
│   └── tire-recommendation/spec.md
└── changes/
    └── introduce-openspec-flow/
        ├── proposal.md
        ├── design.md
        ├── tasks.md
        └── specs/process/spec.md
pyproject.toml
subsystem/
├── budgeting-system/
├── compliance-system/
└── supplier-database/
```

Scaffold target from `project-structure-scaffolding-update` (directory-only now, with planned top-level file locations):

```text
fleet-tire-manager/
├── data/
├── tests/
├── tools/
├── agent.py                       # planned location
├── models.py                      # planned location
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

### Module ownership (planned files)

- `agent.py`: Planned main orchestration entrypoint for requisition flow.
- `models.py`: Planned shared contracts and domain data models reused across modules.
- `tools/`: Integration-facing helper directory grouped by concern.
- `data/`: Shared data loading utility directory.
- `tests/`: Test directory for scaffold and behavior coverage.

### Naming guidance

- Add one tool module per integration concern later (for example `tools/<concern>.py`).
- Keep helper modules focused on one subsystem boundary.
- Place reusable data access helpers under `data/` as files are introduced.
- Keep orchestration flow in `agent.py` when that file is introduced.
