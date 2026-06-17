## Context

The project defines a compliance check in the MVP flow, but no concrete subsystem implementation currently exists. The repository now includes subsystem folders, so this change should establish a minimal but useful compliance component with deterministic test data. The compliance subsystem must evaluate whether a requested tire can be used for a specific operating context (for example regional use, required load index, required speed rating, and operating region).

## Goals / Non-Goals

**Goals:**

- Implement a compliance lookup flow that evaluates tire models against request constraints.
- Store tire model specifications in a JSON mock database for easy iteration during MVP.
- Return structured compliance outcomes with pass/fail state and human-readable reasons.
- Keep the implementation simple and local to the repository with no external services.

**Non-Goals:**

- Production-grade persistence, indexing, or distributed data synchronization.
- Automatic procurement decisions or purchase order submission.
- Complex legal/compliance rule engines beyond MVP field matching and threshold checks.

## Decisions

1. Use a JSON file as the compliance data source.
- Rationale: fast setup, easy review, and deterministic behavior for MVP development.
- Alternative considered: SQLite.
- Why not now: introduces migration and query-layer complexity not required for MVP.

2. Model compliance as request-vs-record validation rules.
- Rationale: explicit rules map directly to user-provided DOT and usage constraints.
- Alternative considered: free-text heuristic matching.
- Why not now: opaque behavior and lower reliability.

3. Keep output contract explicit with machine-readable reasons.
- Rationale: downstream recommendation logic can explain eligibility to users.
- Alternative considered: boolean-only response.
- Why not now: loses traceability and debugging detail.

4. Place mock data under subsystem/compliance-system/mock.
- Rationale: keeps ownership clear and aligns with newly introduced subsystem layout.
- Alternative considered: storing mock data under openspec artifacts.
- Why not now: OpenSpec artifacts document behavior; runtime mock data should live with subsystem implementation assets.

## Risks / Trade-offs

- [Rule oversimplification] -> Start with core fields (size, load index, speed rating, application, region) and document extensibility.
- [Mock data drift from real suppliers] -> Keep schema explicit and add representative sample records across applications and regions.
- [Future migration friction] -> Keep data shape stable and isolate file-loading logic so backends can be swapped later.

## Migration Plan

- Add mock database file with normalized tire specification records.
- Add or update subsystem implementation to load records and evaluate request-fit rules.
- Validate behavior with representative matching and failing scenarios.
- Rollback strategy: revert subsystem logic and mock data additions; no persistent migrations required.

## Open Questions

- Should compliance require all certifications (for example US-DOT plus optional eco certifications) or only mandatory ones?
- Should region compatibility be strict match or allow fallback to national availability when region is absent?
- Should speed rating checks use an ordered ranking table or exact-match semantics for MVP?
