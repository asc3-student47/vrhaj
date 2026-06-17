## 1. Scaffold Core Module Layout

- [x] 1.1 Create directory scaffolding for `tools/` as an integration helper boundary
- [x] 1.2 Create directory scaffolding for `data/` as a data-loading helper boundary
- [x] 1.3 Confirm top-level placeholder intent for future `agent.py` and `models.py` (files deferred)
- [x] 1.4 Keep scaffolding limited to directory creation in this phase

## 2. Establish Test Structure

- [x] 2.1 Ensure `tests/` directory remains the location for scaffold and behavior tests
- [x] 2.2 Preserve existing tests without adding new scaffold placeholder test files in this phase
- [x] 2.3 Defer new scaffold test files until implementation of corresponding modules begins

## 3. Preserve Existing Anchors and Validate Scope

- [x] 3.1 Verify no directory structure changes were made under `openspec/`
- [x] 3.2 Verify no directory structure changes were made under `subsystem/`
- [x] 3.3 Run tests and confirm scaffolding changes do not alter existing runtime business behavior

## 4. Document Ownership Conventions

- [x] 4.1 Update contributor-facing documentation to describe responsibilities and deferred file creation for `agent.py`, `models.py`, `tools/`, `data/`, and `tests/`
- [x] 4.2 Add naming guidance for future integration modules to keep concern boundaries clear
- [x] 4.3 Update `README.md` to reflect the scaffolded directory structure and note that `openspec/` and `subsystem/` remain unchanged
