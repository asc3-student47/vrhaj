# Design: Introduce OpenSpec flow

## Approach
Use the standard OpenSpec folder model:

- `openspec/specs/` as the source-of-truth system specs.
- `openspec/changes/` for proposal-specific deltas and execution artifacts.
- `openspec/config.yaml` for the default `core` workflow profile.

## Decisions
- Keep the baseline spec focused on tire inventory and maintenance visibility.
- Use one bootstrap change (`introduce-openspec-flow`) as the example proposal.
- Document command usage in `README.md` to reduce onboarding friction.

## Risks and mitigations
- **Risk:** Contributors skip artifacts and go straight to coding.
  **Mitigation:** Keep a visible workflow section in README and maintain required change artifacts in PRs.
