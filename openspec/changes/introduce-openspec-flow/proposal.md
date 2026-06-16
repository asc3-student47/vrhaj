# OpenSpec Proposal: Compliant Tire Procurement Agent for Delivery Fleets
 
## 1. Proposal Metadata
- **Proposal ID:** OSP-FLEET-001
- **Status:** Draft
- **Owner:** Fleet Operations
- **Created:** 2026-06-16
 
## 2. Summary
Fleet Managers currently procure replacement tires for delivery trucks using manual checks across vehicle specs, regulatory rules, supplier catalogs, and budget constraints. This process is slow and can result in non-compliant purchases, delayed replacements, and excess downtime.
 
This proposal defines an agent model that recommends tire purchases per truck and wheel position while enforcing compliance and optimizing total cost of ownership.
 
## 3. Problem Statement
The fleet needs a system that can answer this question reliably at scale:
 
"Given each truck's configuration, operating region, route profile, and supplier inventory, what is the best compliant tire option to buy right now?"
 
Current pain points:
- Manual compliance validation is inconsistent across regions and team members.
- Buyers often optimize for unit price instead of lifecycle cost.
- Stockouts and lead-time issues cause emergency purchases.
 
## 4. Goals and Non-Goals
### Goals
- Guarantee that recommended tire purchases are compliant with OEM and legal requirements.
- Reduce procurement cycle time by automating qualification and ranking.
- Minimize total cost of ownership (TCO), not just upfront price.
- Produce an explainable decision record for every recommendation.
 
### Non-Goals (v1)
- Dynamic route optimization across the full logistics network.
- Predictive maintenance model training from telematics beyond existing wear thresholds.
- Autonomous PO submission without human approval.
- Dedicated workflows for secondary users (Procurement Analyst, Maintenance Planner, Compliance Officer) are out of scope for v1.
- Expanded stakeholder governance workflows (Finance, Safety, Legal, Insurance, Approved Tire Suppliers) are out of scope for v1.
 
## 5. Users and Stakeholders
- **Primary User:** Fleet Manager
 
## 6. Requirements
### 6.1 Functional Requirements
0. v0 simplified mode (tire-size first):
	- Accept known tire size as primary input instead of full per-unit fitment details
	- Require load index and speed rating as part of fitment validation inputs
	- Accept number of axles to estimate total tire demand and replacement scope
	- Use `quantity_needed` as required demand input and use axle count for validation/sanity checks
	- Validate legal/compliance constraints for that size and region
	- Return recommendations grouped by requested tire size and axle count
 
1. Ingest market context:
	- Supplier catalogs and approved-vendor status
	- In-stock quantities, lead times, and pricing
	- Warranty terms and expected mileage indicators
 
2. Validate compliance constraints before optimization:
	- Legal/DOT and regional certification requirements
	- OEM fitment and operational specification constraints
	- Company policy constraints (e.g., steer axle minimum standards)
 
3. Rank eligible tire options by weighted objective score:
	- TCO estimate
	- Availability and service risk
	- Fuel efficiency impact
	- Warranty quality
	- Ability to fulfill required volume derived from axle count
 
4. Generate outputs:
	- Recommended SKUs
	- Compliance checklist with pass/fail reasoning (only when explicitly requested)
	- Cost breakdown and comparison table
	- Estimated tire quantity needed based on axle count assumptions
	- Exception report when no compliant in-stock option exists
	- Purchase draft payload for ERP/procurement systems
 
### 6.2 Non-Functional Requirements
- Response time: under 10 seconds for a single-truck request; under 2 minutes for 1,000-truck batch.
- Explainability: every recommendation includes evidence and rule references.
- Reliability: 99.5% successful runs for scheduled batch mode.
- Security: role-based access, encrypted data in transit and at rest.
 
### 6.3 Compliance and Safety Requirements
- Do not recommend any tire failing legal or OEM constraints.
- Log all rule evaluations with timestamp and source version.
- Flag ambiguous regulatory conditions for human review.
 
## 7. Proposed Agent Model
### 7.1 Agent Responsibilities
- **Policy Agent:** Interprets and enforces compliance rules.
- **Selection Agent:** Filters and ranks compliant SKUs.
- **Cost Agent:** Computes lifecycle cost and financial comparisons.
 
### 7.2 Decision Flow
1. Normalize truck and supplier inputs.
2. Validate `quantity_needed` against `number_of_axles` using configured axle-to-tire assumptions.
3. Build candidate tire set from approved vendors.
4. Apply hard compliance constraints.
5. Score remaining options via weighted objective function.
6. Return recommendation package with rationale and exceptions.
 
### 7.3 Decision Function (v1)
For each eligible option i:
 
Score(i) = w1 * ComplianceConfidence + w2 * AvailabilityScore + w3 * TCOScore + w4 * FuelImpactScore + w5 * WarrantyScore
 
Where:
- ComplianceConfidence is binary-gated (0 if non-compliant, else 1).
- Weights are configurable by policy and region.
 
## 8. Data Contracts (Initial)
### 8.0 v0 Minimal Schema (known tire size)
Use this for a fast pilot when requestors already know required tire size.
 
Input:
- `tire_size` (e.g., 295/75R22.5)
- `load_index`
- `speed_rating`
- `number_of_axles`
- `region_code`
- `quantity_needed`
- `replacement_urgency` (low, medium, high)
- `include_compliance_summary` (optional, default: false)
 
Catalog:
- `sku`
- `supported_tire_sizes` (list)
- `certifications`
- `unit_price`
- `estimated_mileage`
- `stock_qty`
- `lead_time_days`
 
Output:
- `tire_size`
- `number_of_axles`
- `recommended_skus`
- `estimated_tires_required`
- `cost_summary`
- `exceptions`
- `compliance_summary` (only when `include_compliance_summary=true`)
 
Known tradeoffs in v0:
- Axle count improves quantity planning but does not fully resolve wheel-position fitment constraints.
- Higher chance of manual review for edge cases.
- Best for pilot/prototyping, not final compliance automation.
 
Default v0 quantity assumption:
- `estimated_tires_required = quantity_needed`.
 
### 8.1 Short Example Request (v0)
```json
{
	"tire_size": "295/75R22.5",
	"load_index": 144,
	"speed_rating": "L",
	"number_of_axles": 3,
	"region_code": "TX",
	"quantity_needed": 24,
	"replacement_urgency": "high"
}
```
 
### Input Schema (conceptual)
- `tire_size`
- `load_index`
- `speed_rating`
- `number_of_axles`
- `quantity_needed`
- `replacement_urgency`
- `region_code`
- `include_compliance_summary` (optional)
 
### Catalog Schema (conceptual)
- `supplier_id`
- `sku`
- `certifications`
- `supported_tire_sizes`
- `supported_load_indexes`
- `supported_speed_ratings`
- `unit_price`
- `estimated_mileage`
- `fuel_efficiency_rating`
- `warranty_terms`
- `stock_qty`
- `lead_time_days`
 
### Output Schema (conceptual)
- `recommendation_id`
- `tire_size`
- `load_index`
- `speed_rating`
- `number_of_axles`
- `quantity_needed`
- `estimated_tires_required`
- `recommended_skus`
- `score_breakdown`
- `cost_projection`
- `exceptions`
- `compliance_summary` (only when `include_compliance_summary=true`)
 
## 9. Success Metrics
- 100% of recommended purchases pass compliance checks.
- 50% reduction in procurement cycle time.
- 10% reduction in tire-related TCO over 2 quarters.
- 90%+ user acceptance of first recommendation without override.
 
## 10. Risks and Mitigations
- **Risk:** Supplier data quality gaps
  - **Mitigation:** Schema validation, fallback vendors, confidence scores
- **Risk:** Rule conflicts across jurisdictions
  - **Mitigation:** Policy versioning by region and legal review workflow
- **Risk:** User distrust of automation
  - **Mitigation:** Transparent rationale, override capture, feedback loop
 
## 11. Open Questions
1. Which regions/jurisdictions are in scope for pilot compliance packs?
2. What ERP/procurement system format is required for PO payloads?
3. What override policies and approval thresholds should be enforced?
4. Should mixed-brand tire recommendations be allowed per axle group?

## 12. Future TODO
1. Reconcile rubric document at certain point