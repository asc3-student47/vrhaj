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

## Run the recommendation agent

Start the interactive agent prompt flow:

```bash
python run_recommendation_pipeline.py
```

Show full tool trajectory output for a run:

```bash
python run_recommendation_pipeline.py --show-trajectory
```

At startup, the agent greets the user, prints an example prompt, and asks for a tire request.

Example prompt:

```text
Need 24 tires size 225/70R19.5 load index 120 speed rating K in TX urgency medium for regional delivery and include compliance summary.
```

This agent is configured for strict Pydantic-AI extraction. If the model is unreachable or credentials are missing, the request fails with an explicit `llm_extract_failed` error.

For multi-turn chat mode (repeat prompts until exit):

```bash
python run_recommendation_pipeline.py --chat
```

Type `exit`, `quit`, or `q` to end the session.

Every interaction prints a structured console log line with event metadata.

By default, the agent uses `openai-chat:gpt-4o-mini` and reads credentials from `.env` (for example `OPENAI_API_KEY`).

## Run the basic web UI

Launch a local browser-based UI:

```bash
python run_recommendation_ui.py
```

Then open `http://127.0.0.1:8765` in your browser.

In the UI, enable `Include trajectory` to return detailed tool-call records per request.

The UI calls the same agent pipeline used by CLI mode, and each request is logged in the server console.

Set `PROCUREMENT_AGENT_MODEL` if you want to override the default model.

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
└── supplier-system/
```
