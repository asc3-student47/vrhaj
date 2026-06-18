# Skill: RAPID Peer Review (ITC.009)

## Trigger

Use this skill when asked to perform a peer review, run a code review, or generate
a `rapid-peer-review.md` document for this project.

## Purpose

Perform a structured peer review of recent code changes aligned to FedEx RAPID
Framework control **ITC.009 — Code Review**. The review evaluates six criteria and
produces a written findings document that a procurement officer or release manager
can act on directly.

## Instructions

Follow every step in order. Do not skip steps or combine them.

### Step 1 — Identify Modified Files

Run the following command and capture the output:

```
git diff --name-only HEAD~1 HEAD
```

If the repository has no prior commits, use:

```
git status --short
```

List every modified, added, or deleted file. This inventory is the foundation of the
review. If no files have changed, report that and stop.

### Step 2 — Identify Author and Reviewer

- **Author**: The person who made the changes (check `git log -1 --format="%an <%ae>"`).
- **Reviewer**: You are acting as the AI peer reviewer on behalf of the developer.
  Record both names in the output header.

### Step 3 — Evaluate the Six ITC.009 Criteria

For each criterion below, read the relevant files, then assign a rating of
**Pass**, **Needs Attention**, or **Fail**, and write 1–3 sentences of findings.

#### Criterion 1: Modified-File Inventory
Confirm the file list from Step 1 is complete and that no files outside the
established project structure were created without authorization (see `AGENTS.md`
Scope Constraints). Check whether `mock_data/` or `pyproject.toml` were modified
without justification.

#### Criterion 2: Author / Reviewer Separation
Confirm the author and reviewer are not the same person. If this is a self-review
(author == reviewer), flag it as Needs Attention and note the exception.

#### Criterion 3: InfoSec Alignment
Check for:
- Hardcoded secrets, API keys, passwords, or tokens in any modified file
- Sensitive data (PII, financial records) written to logs or stdout
- `.env` files or files matching patterns in `.gitignore` accidentally staged

Rate Fail if any of the above are found. Rate Pass if none are present.

#### Criterion 4: Reference Architecture Alignment
Verify that the implementation follows the project's architectural conventions:
- Data access only through `data/loader.py`, not direct file reads
- Agent logic only in `agent.py`; tool logic only in `tools/`
- Models defined only in `models.py`
- No circular imports between `agent.py`, `tools/`, `models.py`, and `data/`
- All tool functions have docstrings (required by `AGENTS.md`)
- Type hints present on all new functions and class attributes

#### Criterion 5: Documentation Adequacy
Check that:
- All new public functions and classes have docstrings
- Any new OpenSpec specifications in `openspec/` accurately describe what was implemented
- `README.md` acceptance criteria are consistent with the current implementation
- No `# TODO` comments remain in submitted code (per `AGENTS.md`)

#### Criterion 6: Behavioral Scope Compliance
Verify that the agent's observable behavior matches its specification:
- `ProcurementRecommendation.decision` is always `approve`, `deny`, or `escalate`
- `ProcurementRecommendation.rationale` is always a non-empty string
- Tool errors are caught and surfaced in the recommendation, not silently swallowed
- No external network calls are made during tests (mock data only)

### Step 4 — Write and Save the Review Document

Create or overwrite the file `docs/rapid-peer-review.md` with the structure below.
Fill in every field. Do not leave placeholder text.

```markdown
# RAPID Peer Review — ITC.009 Code Review

**Control**: ITC.009 — Code Review
**Project**: Procurement and Vendor Intelligence Agent (Track A)
**Review Date**: <today's date>
**Author**: <git author name and email>
**Reviewer**: GitHub Copilot (AI Peer Review) on behalf of <developer name>

---

## Modified Files

<bullet list of every file from Step 1>

---

## Criterion Findings

| # | Criterion | Rating | Findings |
|---|-----------|--------|----------|
| 1 | Modified-File Inventory | <Pass/Needs Attention/Fail> | <findings> |
| 2 | Author / Reviewer Separation | <Pass/Needs Attention/Fail> | <findings> |
| 3 | InfoSec Alignment | <Pass/Needs Attention/Fail> | <findings> |
| 4 | Reference Architecture Alignment | <Pass/Needs Attention/Fail> | <findings> |
| 5 | Documentation Adequacy | <Pass/Needs Attention/Fail> | <findings> |
| 6 | Behavioral Scope Compliance | <Pass/Needs Attention/Fail> | <findings> |

---

## Summary Recommendation

**Overall Rating**: <Pass / Conditional Pass / Fail>

<Two to four sentences summarizing the review outcome. Note which criteria drove
the rating. State whether the implementation is ready for the Go/No-Go gate or
whether specific items must be resolved first.>

---

## Required Actions Before Go/No-Go

<Bulleted list of specific items that must be fixed for any criterion rated
Needs Attention or Fail. If all criteria are Pass, write "None — implementation
is ready for Go/No-Go review.">
```

### Step 5 — Confirm Completion

Report to the developer:
- The overall rating
- The number of criteria that passed, need attention, or failed
- The path where the document was saved (`docs/rapid-peer-review.md`)
- Any required actions from Step 4

## Output Contract

- The file `docs/rapid-peer-review.md` must exist after this skill runs
- Every criterion must have a rating — no blank cells
- The summary recommendation must reference at least one criterion by name
- This skill does not approve or reject the implementation; it produces findings
  for the developer and the Go/No-Go reviewer to act on
