# Spec Architecture Sketch

## Purpose
This document sketches a modular requirement architecture for fleet tire procurement so product behavior and delivery process are separated clearly.

## Proposed capability map

```text
openspec/specs/
  fleet-tire-management/      # Existing baseline domain spec
  tire-compliance/            # Hard eligibility and legal/OEM policy rules
  tire-recommendation/        # Candidate scoring and ranking behavior
        procurement-handoff/        # Tire inventory search API outputs and no-match behavior (planned)
```

## Layering model

```text
Input normalization
        |
        v
Compliance eligibility (hard gate)
        |
        v
Recommendation scoring (soft optimization)
        |
        v
Inventory search response (results, summaries, no-match reasons)
```

## Requirement ownership boundaries
- `tire-compliance`: Defines pass/fail eligibility rules. No ranking logic.
- `tire-recommendation`: Defines how compliant options are scored and sorted. No legal rule authoring.
- `procurement-handoff`: Defines inventory search response contracts and no-match semantics.

Current implementation note: compliance and supplier lookup subsystems are implemented; procurement handoff remains planned.

## Cross-cutting concerns
- Explainability and auditability should be stated in each capability spec where behavior is produced.
- Performance targets should be consolidated later in one non-functional baseline section.
- Regional policy versioning should be introduced first in `tire-compliance` and referenced by downstream specs.

## Open questions
1. Should mixed-brand policy be modeled in compliance rules or recommendation strategy?
2. Is urgency (`low|medium|high`) a scoring input only, or can it relax lead-time constraints in compliance?
3. Should search result contracts be versioned now, or deferred until API clients stabilize?
