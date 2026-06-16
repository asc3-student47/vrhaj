# Procurement Agent — Project Conventions

## Language and Runtime
- Python 3.11+
- Use type hints on all function signatures and class attributes
- Use `pydantic-ai` for all agent construction
- Use Pydantic v2 models for all structured data (input, output, mock data)

## Code Style
- Follow PEP 8
- Maximum line length: 100 characters
- Use f-strings for string formatting
- Prefer `pathlib.Path` over `os.path` for file operations

## Testing
- Use `pytest` and `pytest-asyncio` for all tests
- Test files live in `tests/`; test file names match the module they test (e.g., `test_budget_tool.py`)
- Use simulated backends for all agent tests — do not make live API calls in tests
- Every tool function must have at least one test covering its primary success path

## Project Structure
- Agent tools live in `tools/`
- Pydantic models live in `models.py`
- The main agent lives in `agent.py`
- Mock data access goes through `data/loader.py` — do not read JSON files directly in tool code

## Mock Data
- Do not modify files in `mock_data/` directly
- All test data access must go through `data/loader.py`

## Agent Behavior
- Every recommendation must include a non-empty `rationale` string
- Tool errors must be caught and reflected in the output — never silently ignored

## Pydantic AI — Structured Output Pattern


This tells Pydantic AI to constrain the LLM's response to that model's schema.
Do not return raw strings or dicts from the agent — always use the typed output contract.

> **Note:** The older `result_type=` parameter is deprecated in Pydantic AI v1.x and will
> emit a warning. Always use `output_type=` in new code.

```python
from pydantic_ai import Agent
from models import PurchaseRequest, ProcurementRecommendation

agent = Agent(
    "anthropic:claude-3-5-haiku-latest",
    output_type=ProcurementRecommendation,  # structured output contract
    system_prompt="...",
)

result = agent.run_sync(user_prompt)
recommendation = result.data  # ProcurementRecommendation — never a raw string
```

Reference: <https://ai.pydantic.dev/results/#structured-results>

## RAPID DevSecOps Conventions

### ITC.014 — Requirements Traceability
Every commit message must reference the applicable user story from `user-stories.md`.

Format: `[US-XXX] Short description of change`
Example: `[US-001] Implement check_budget with overage detection`

A commit that touches multiple stories may reference both: `[US-001][US-005] Add budget overage to rationale`

### ITC.003 — Test Execution Records
Run the test suite with results capture before every code review and Go/No-Go:

```
pytest tests/ -v --tb=short --junitxml=docs/test-results.xml
```

Commit `docs/test-results.xml` alongside the code under review. This file is the
ITC.003-compliant test execution record.

### ITC.013 — Backout Plan
`backoutPlan.md` at the repository root is a living document. Update it:
- Before the Session 4 peer review (fill in stable baseline commit hash and contacts)
- Whenever the revert procedure or deployment approach changes
