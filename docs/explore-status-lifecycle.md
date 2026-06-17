# Draft Proposal Summary: Project Structure and Scaffolding Update

## Problem
The repository has domain specifications and subsystem assets, but the project layout is not yet organized around a clear architecture boundary model for future development. This increases onboarding friction, blurs ownership between domain and integration code, and makes it harder to evolve from mock assets to real integrations without large refactors.

## Proposed Solution
Adopt a scaffolding-first Hexagonal Architecture (Ports and Adapters) layout that defines module boundaries, import direction, and package ownership without implementing new business workflows.

Scaffolding summary:
1. Establish top-level package structure for domain, application, ports, adapters, orchestration, and presentation.
2. Define canonical interfaces and dependency direction between layers.
3. Preserve existing subsystem mock assets as adapter-side dependencies.
4. Add test folder segmentation aligned to architecture layers.
5. Document deterministic design decisions as architecture constraints for later implementation.

Key baked-in structural decisions:
- Dependency flow is one-directional toward the domain core; domain is isolated from adapter concerns.
- Existing subsystem folders remain integration assets and are not treated as domain modules.
- Compliance, supplier, and budget integration points are represented as ports first.
- Verbose/optional response behaviors are captured as contract expectations, not implemented logic.
- Deterministic ordering and validation policies are captured as future acceptance constraints.

## Proposed Directory Tree
```text
fleet-tire-manager/
	pyproject.toml
	README.md
	docs/
		agent-chat-log.md
		explore-status-lifecycle.md
	openspec/
		config.yaml
		specs/
			spec-architecture.md
			fleet-tire-management/spec.md
			tire-compliance/spec.md
			tire-recommendation/spec.md
			procurement-handoff/spec.md
			compliance-system-lookup/spec.md
		changes/
			introduce-openspec-flow/
				proposal.md
				design.md
				tasks.md
				specs/
					process/spec.md
			archive/
				2026-06-16-implement-compliance-system/
					proposal.md
					design.md
					tasks.md
					specs/
						compliance-system-lookup/spec.md
						tire-compliance/spec.md
	src/
		fleet_tire_manager/
			__init__.py
			domain/
				__init__.py
				models.py
				policy.py
				scoring.py
				exceptions.py
			application/
				__init__.py
				contracts.py
				use_cases/
					__init__.py
					evaluate_requisition.py
					generate_purchase_draft.py
			ports/
				__init__.py
				compliance_port.py
				supplier_port.py
				budget_port.py
				clock_port.py
			adapters/
				__init__.py
				compliance/
					__init__.py
					json_compliance_adapter.py
				supplier/
					__init__.py
					json_supplier_adapter.py
				budgeting/
					__init__.py
					json_budget_adapter.py
			orchestration/
				__init__.py
				workflow_service.py
			presentation/
				__init__.py
				cli.py
			config/
				__init__.py
				settings.py
	subsystem/
		compliance-system/
			compliance_system.py
			mock/
				tire-compliance-db.json
		supplier-database/
			mock/
				suppliers-db.json
		budgeting-system/
			mock/
				budgets-db.json
	tests/
		unit/
			test_domain_compliance_policy.py
			test_domain_scoring.py
		adapters/
			test_json_compliance_adapter.py
			test_json_supplier_adapter.py
			test_json_budget_adapter.py
		integration/
			test_evaluate_requisition_flow.py
			test_generate_purchase_draft.py
		test_compliance_system.py
```

## Scope
In scope for this draft scaffolding update:
- Define and document module boundaries for domain, application, ports, adapters, orchestration, and presentation concerns.
- Propose a complete directory tree aligned with the selected architecture.
- Define import rules and dependency constraints between modules.
- Define where integration adapters map to existing subsystem assets.
- Define test package layout by layer (unit, adapter, integration).
- Capture architecture decisions and constraints to guide later implementation proposals.

## Out of Scope
Out of scope for this draft:
- Implementing or changing runtime business logic.
- Modifying compliance rule execution behavior.
- Implementing ranking, budget validation, or purchase-draft generation flows.
- Adding production database migrations or service connectivity.
- Wiring CLI/API execution paths beyond placeholder scaffolding.
- Performance optimization or scaling implementation.

## Risks
1. Over-scaffolding risk
Creating too many empty layers upfront may add maintenance overhead before functionality exists.

2. Boundary mismatch risk
If scaffolding boundaries are defined incorrectly, future implementation may require structural rework.

3. Drift risk between specs and structure
OpenSpec capability boundaries can diverge from package structure if not kept synchronized.

4. Transition risk for existing contributors
Developers familiar with subsystem-first development may need guidance to adopt layered package conventions.

5. Scope creep risk
There is a risk of unintentionally implementing behavior while performing structural updates; this proposal explicitly prevents that.

## Notes
This document is intentionally limited to project structure and scaffolding decisions. It does not authorize or include feature implementation.
