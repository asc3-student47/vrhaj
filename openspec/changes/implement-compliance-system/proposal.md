## Why

The current workflow depends on a compliance decision, but the repository does not yet include a concrete compliance subsystem implementation. Adding this now unblocks end-to-end MVP behavior and makes compliance checks testable with deterministic mock data.

## What Changes

- Implement a compliance subsystem that evaluates whether a tire model meets request constraints for intended use.
- Add a JSON mock database of tire model specifications used by the compliance subsystem.
- Support checks for key constraints such as tire size, load index, speed rating, application, and region compatibility.
- Return structured compliance results that clearly indicate pass/fail with reasons.

## Capabilities

### New Capabilities

- `compliance-system-lookup`: Lookup tire specifications and evaluate request-fit compliance using mock tire data.

### Modified Capabilities

- `tire-compliance`: Define requirements for model lookup behavior and request-fit rule evaluation used by compliance decisions.

## Impact

- Affected systems: compliance subsystem and local mock data under subsystem assets.
- Affected specs: new capability spec for compliance lookup and a delta for tire-compliance behavior.
- No external API dependencies required for MVP mock implementation.
