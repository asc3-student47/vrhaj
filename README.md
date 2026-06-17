# fleet-tire-manager
Hallucinators FDE Capstone Project

## OpenSpec flow

This repository now includes an OpenSpec spec-driven workflow under `openspec/`.

### Active proposal

- `openspec/changes/introduce-openspec-flow/proposal.md`

### Workflow commands

Use these commands in your AI tool chat to run the default OpenSpec flow:

1. `/opsx:propose <change-name-or-idea>`
2. `/opsx:apply`
3. `/opsx:sync`
4. `/opsx:archive`

### Repository structure

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
