# Template Design Specification

**Status**: completed
**Date**: 2026-07-15
**Reviewer**: [TBD]

## Position in AgentCore Architecture

- **Agent Class**: `WorkOrderGenerationAgent`
- **L1 Base**: AgentBaseGraph (Cat 2 — outer 5-node backbone + inner `GraphNode`-wrapped domain workflow)
- **Three-Layer Separation**:
  - State: flat TypedDict composition (no Pydantic — msgpack incompatible)
  - Node: L1 inheritance (Template Method: `execute(self, state: dict) -> dict` override only)
  - Graph: composition (`register_nodes()` for node substitution)

## Architecture Overview

Cat 2 classification: this template orchestrates a fixed, specific job-to-be-done
(生成 a compliant 停電作業指示書 + safety checklist from a maintenance request) — not a
single reusable capability (Cat 1), and not an autonomous self-directed loop (Cat 3).
The outer graph keeps the standard 5-node backbone; all domain complexity (regulatory
retrieval → draft → safety checklist → compliance validation) is encapsulated in the
`main` slot via a `GraphNode` wrapping an inner `domain_workflow_graph.py`.

### Outer Graph — `src/graph/graph.py`

| Node | Responsibility | Input State | Output State | Inherits/Overrides |
|------|---------------|-------------|--------------|-------------------|
| initialize | Framework default: assigns correlation_id, trace_id, initial status | — | `correlation_id`, `trace_id`, `status` | InitializeNode (default) |
| pre_process | Parse + validate structured maintenance request (work type, equipment ID, location, schedule, crew size); reject malformed/oversized input | `user_input` | `validated_input`, `work_type`, `equipment_id`, `location`, `schedule`, `crew_size`, `status` | PreProcessNode |
| main | Run inner domain workflow: regulatory retrieve → work order draft → safety checklist generate → compliance validate | `validated_input`, `work_type`, `equipment_id`, `location`, `schedule`, `crew_size` | `work_order_draft`, `safety_checklist`, `regulatory_citations`, `compliance_flags`, `status` | `WorkOrderWorkflowGraphNode` (GraphNode) |
| post_process | Assemble final document (work order + checklist + citation index); strip grid topology/SCADA identifiers (S-3 domain gate) | `work_order_draft`, `safety_checklist`, `regulatory_citations`, `compliance_flags` | `result`, `status` | PostProcessNode |
| finalize | Framework default: final output shaping, cost enrichment | `result`, `status` | `output` | FinalizeNode (default) |

### Data Flow

```
START → initialize → pre_process → main → {route} → post_process → finalize → END
                                             ↓ (retry, max_retry=3)
                                           pre_process
```

`{route}`: `RETRY` → `pre_process` when `main` reports a transient regulatory-KB
lookup failure (bounded by `max_retry`); `ERROR` → skip to `post_process`/`finalize`
with `status=error` when compliance validation finds unrecoverable missing mandatory
fields; otherwise continue to `post_process`.

### Inner Graph — `src/graph/domain_workflow_graph.py` (`WorkOrderWorkflowGraph`)

Inherits `BaseGraph` (fully custom topology — no pre_process/main/post_process slots
needed; the four domain steps are sequential with one validation branch).

```
START → regulatory_retrieve → work_order_draft → safety_checklist_generate
      → compliance_validate → {route} → END
                                 ↓ (ERROR, missing mandatory field/citation)
                                END (status=error, compliance_flags populated)
```

| Node | Responsibility | Input State | Output State |
|------|---------------|-------------|---------------|
| regulatory_retrieve | Vector search 電気事業法 + 労働安全衛生法 KB for clauses matching `work_type` | `validated_input`, `work_type` | `regulatory_citations` |
| work_order_draft | LLM-draft the 停電作業指示書 with all mandatory fields, using retrieved citations | `validated_input`, `work_type`, `equipment_id`, `location`, `schedule`, `crew_size`, `regulatory_citations` | `work_order_draft` |
| safety_checklist_generate | Build work-type-specific safety checklist (PPE, isolation steps, emergency contacts) | `work_type`, `regulatory_citations` | `safety_checklist` |
| compliance_validate | Rule-check mandatory fields present + citation accuracy; flag gaps | `work_order_draft`, `safety_checklist`, `regulatory_citations` | `compliance_flags`, `status` |

`WorkOrderWorkflowGraphNode.merge_output()` maps the inner `get_output()` dict
(`work_order_draft`, `safety_checklist`, `regulatory_citations`, `compliance_flags`,
`status`) into these same-named outer state keys — no renaming, since outer
`post_process` consumes them directly.

**Every inner node that reads the primary input text falls back to `user_input`**
(`state.get("validated_input", state.get("user_input", ""))`) per the framework's
fresh-inner-state rule — the inner graph's `invoke()` only seeds `user_input`, not the
outer `pre_process`'s parsed fields, so `regulatory_retrieve` re-derives `work_type`
from `validated_input`/`user_input` if the outer-computed `work_type` field is absent
from the inner initial state (verify via the mandatory `.invoke()` smoke test before
writing node unit tests).

### State Definition (`src/schemas/state.py`)

| Field | Type | Purpose | Required |
|-------|------|---------|----------|
| `validated_input` | `str` | Sanitized structured maintenance request text (post S-1/S-2 gate) | No (set by pre_process) |
| `work_type` | `str` | Parsed work type (e.g. "transformer_replacement", "confined_space_entry") | No (set by pre_process) |
| `equipment_id` | `str` | Parsed equipment identifier | No (set by pre_process) |
| `location` | `str` | Parsed maintenance location (non-topological, e.g. facility name) | No (set by pre_process) |
| `schedule` | `str` | Parsed maintenance schedule (ISO 8601 str) | No (set by pre_process) |
| `crew_size` | `int` | Parsed crew size | No (set by pre_process) |
| `regulatory_citations` | `list[dict]` | Matched 電気事業法/労働安全衛生法 clauses (`{law, article, text}`) | No (set by main) |
| `work_order_draft` | `dict` | Drafted 停電作業指示書 mandatory fields | No (set by main) |
| `safety_checklist` | `list[dict]` | Work-type-specific safety checklist items (`{category, item, mandatory}`) | No (set by main) |
| `compliance_flags` | `list[str]` | Missing-field / citation-accuracy flags from validation | No (set by main) |
| `result` | `dict` | Final assembled document (work order + checklist + citation index) | No (set by post_process) |

**State Constraints (mandatory):**
- Flat TypedDict only (primitives + JSON-serializable types)
- No JWT, API keys, credentials in State (checkpoint DB leakage)
- InvocationContext via `config["configurable"]` only (not in State)
- No Pydantic models, dataclass, arbitrary Python objects (msgpack incompatible)
- No grid topology maps, substation coordinates, or SCADA identifiers in any field —
  enforced by the `post_process` S-3 domain gate (`_extra_security_gate_output()`)

## Framework Utilization

### Shared Components Used
- [x] InvocationContext (correlation_id, session_id, permissions, credential handle) — used by `main` for LLM credential handle, forwarded to inner graph via `WorkOrderWorkflowGraphNode._parent_config()`
- [x] ConnectionPolicy (retry/timeout strategy) — `max_retry: 3`, `timeout_seconds: 30` per `config/agent.yaml`
- [x] SecurityViolationError — raised if S-1 input-size gate or S-3 output-credential gate trips
- [x] S-2: `_extra_security_gate_input()` on `pre_process` — validates request size (max 2000 chars per proposal), confirms structured fields parse before continuing past the default PII scan
- [x] S-3: `_extra_security_gate_output()` on `post_process` — domain-specific scan/strip of grid topology, substation coordinate, and SCADA-identifier patterns from `result` before the default credential scan
- [x] S-4: `emit_trace_event()` — at least one domain event per node: `request_parsed` (pre_process), `regulatory_clauses_retrieved` (inner regulatory_retrieve), `work_order_drafted` (inner work_order_draft), `safety_checklist_generated` (inner safety_checklist_generate), `compliance_validated` (inner compliance_validate), `document_assembled` (post_process)

> **S-2/S-3 gate behaviour by node type (ADR-017):**
> - `FunctionNode` subclass (pre_process, post_process, and all four inner nodes) →
>   framework `@final` gate always runs automatically; extend via
>   `_extra_security_gate_input()` / `_extra_security_gate_output()` only
> - `GraphNode` (`WorkOrderWorkflowGraphNode` in the `main` slot) → deliberate no-op
>   (inner graph's own node-level gates already applied to each inner node)
> - No custom `BaseNode` subclass in this design

### Composition Pattern

- **Pattern**: GraphNode (subgraph) — `main` slot wraps the inner domain workflow graph
- **Composition target**: `src/graph/domain_workflow_graph.py::WorkOrderWorkflowGraph`
- **Error propagation strategy**: `propagate` (default) — a failure inside regulatory
  retrieval, drafting, or validation is a safety-relevant failure and must surface as a
  hard error rather than degrade silently, given the mandatory qualified-engineer review
  gate depends on receiving a complete or explicitly-flagged draft, never a partially
  failed one masked as success.
- **`propagate_hitl`**: `False` — this template has no HITL interrupt; approval happens
  out-of-band by a human engineer after the agent returns its output, not via an
  in-graph `interrupt()`.

## Import Isolation Confirmation
- [x] Template does not import agenticstar-platform SDK (Level 0)
- [x] Import targets: framework/ and shared/ only (no agents/base/ required)

## Services (`src/services/`)

- **RegulatoryRetrievalService** — vector search against the 電気事業法 +
  労働安全衛生法 KB; used by inner `regulatory_retrieve` node.
- **WorkOrderDraftingService** — LLM prompt construction and invocation for
  drafting the 停電作業指示書; used by inner `work_order_draft` node.
- **SafetyChecklistService** — work-type-conditional checklist rule lookup (PPE,
  isolation steps, emergency contacts); used by inner `safety_checklist_generate` node.
- **ComplianceValidationService** — rule-based mandatory-field and citation-accuracy
  checker; used by inner `compliance_validate` node.

All services follow the mock-mode pattern (`get_flag()` / `USE_MOCK` +
`STG_MOCK_MODE` resolution via the shared `mock_mode_enabled()` helper — see
`.claude/rules/implementation_rule.md` Rule 1) and use `InvocationContext.credential_handle`
for any LLM access, never a raw API key.

## Error Handling

- **Malformed/oversized maintenance request** (`pre_process`): S-1 input gate rejects
  requests over 2000 chars; `_extra_security_gate_input()` validates required structured
  fields are present → `status=error` if request cannot be parsed at all (permanent
  failure, not retried).
- **Regulatory KB lookup transient failure** (inner `regulatory_retrieve`): `RETRY` up to
  `max_retry=3`, looping back through outer `pre_process` per the framework backbone.
- **Missing mandatory field or inaccurate citation** (inner `compliance_validate`):
  not retried — this is a content-completeness issue, not a transient fault. Routes to
  `END` with `status=error` and `compliance_flags` populated so the caller (grid
  operations planner) knows exactly what is missing, rather than receiving a silently
  incomplete document.
- **S-3 output gate trip** (`post_process`): if grid topology/SCADA-identifier pattern
  or a credential pattern is detected in the assembled `result`, `SecurityViolationError`
  is raised — this must never be caught and downgraded to a soft warning, since it is
  exactly the safety/security boundary this template exists to enforce (§2 of the
  proposal: "no grid topology maps, substation coordinates, or SCADA identifiers ever
  enter State or output").

## Security Considerations

- `required_trust_level: VERIFIED_EXTERNAL` (matches `config/agent.yaml`) — this agent
  is invoked by grid operations planners and scheduling tooling, not anonymous callers.
- No PII beyond what's operationally necessary (equipment ID, location, schedule, crew
  size) ever leaves `pre_process` un-scanned — default S-2 PII scan plus the domain
  `_extra_security_gate_input()` size/shape check.
- Output never contains grid topology, substation coordinates, or SCADA identifiers —
  enforced by the domain `_extra_security_gate_output()` hook, independent of the
  default credential-pattern scan.
- All LLM/vector-DB access goes through `shared/services/` with `credential_handle`,
  never a raw key in State, logs, or node arguments.

## Performance Requirements

- Target: draft generation completes in well under the proposal's "<10 minutes draft
  generation + review" business target — the agent's own draft step should complete in
  low tens-of-seconds range given a single LLM draft call + one vector search, well
  within `timeout_seconds: 30` per node step (see `config/agent.yaml`); end-to-end
  human review time is out of the agent's control and out of scope for this design.
- `max_retry: 3` bounds cost/latency on transient regulatory-KB lookup failures.

## Design Decision Record

| Decision | Option A | Option B | Chosen | Rationale |
|----------|----------|----------|--------|-----------|
| L1 base type | AgentBaseGraph | AutonomousBaseGraph | **AgentBaseGraph** | Fixed job-to-be-done (parse → retrieve → draft → validate → assemble), no self-directed reasoning loop or open-ended termination — Cat 2, not Cat 3 |
| Composition pattern | Standalone (all logic in outer pre/main/post) | GraphNode (inner domain_workflow_graph) | **GraphNode** | Four distinct domain steps (retrieve, draft, checklist, validate) with their own state transitions belong in an inner topology, keeping the outer graph as the standard 5-node backbone per Cat 2 convention |
| Inner graph base | BaseGraph (custom topology) | AgentBaseGraph (5-node pipeline) | **BaseGraph** | The four inner steps don't map onto pre_process/main/post_process slots — a fully custom linear-with-validation-branch topology is a better fit and avoids forcing an artificial pre/main/post split inside the inner graph |
| Error propagation (GraphNode) | propagate | handle | **propagate** | A failed/incomplete draft must surface as a hard error, not a degraded-but-still-returned "success" — the mandatory human review gate depends on receiving either a complete draft or an explicit failure, never a silently partial one |
| HITL | enabled | disabled | **disabled** | Approval is an out-of-band human process (qualified electrical engineer reviews the returned document before work commences) — not an in-graph pause/resume interrupt |
