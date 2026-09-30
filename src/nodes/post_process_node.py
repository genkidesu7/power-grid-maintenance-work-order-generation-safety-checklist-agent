"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Never import from mediator/, api/, or other agents

from __future__ import annotations

import re
from typing import Any, ClassVar

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

# S-3 domain gate: no grid topology maps, substation coordinates, or SCADA
# identifiers may ever leave the agent (docs/01_proposal.md §4 note;
# docs/02_design.md "Security Considerations").
_TOPOLOGY_PATTERNS = (
    re.compile(r"\bSCADA[-_]?[A-Z0-9]{3,}\b", re.IGNORECASE),
    re.compile(r"\bsubstation[-_ ]?(coord|lat|lon)\w*\b", re.IGNORECASE),
    re.compile(r"\b\d{1,3}\.\d{3,},\s*-?\d{1,3}\.\d{3,}\b"),  # lat,lon pair
)


class PostProcessNode(FunctionNode):
    """Assemble the final work-order document.

    Reads work_order_draft, safety_checklist, regulatory_citations,
    compliance_flags. Writes result.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_output(self, result: dict[str, Any]) -> dict[str, Any]:
        """S-3 domain extension: strip/block grid topology & SCADA identifiers.

        Runs after the default credential-pattern scan. Raises to block
        output that contains a topology/SCADA-identifier pattern — this
        must never be silently downgraded, per docs/02_design.md's error
        handling policy.
        """
        doc = result.get("result", {})
        serialized = str(doc)
        for pattern in _TOPOLOGY_PATTERNS:
            if pattern.search(serialized):
                raise SecurityViolationError(
                    "PostProcessNode: grid topology/SCADA identifier pattern detected in output"
                )
        return result

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Assembling the final work order document...",
            metadata={"stage": "post_process"},
        )
        work_order_draft: dict[str, Any] = state.get("work_order_draft", {})
        safety_checklist: list[dict[str, Any]] = state.get("safety_checklist", [])
        regulatory_citations: list[dict[str, Any]] = state.get("regulatory_citations", [])
        compliance_flags: list[str] = state.get("compliance_flags", [])

        if not work_order_draft:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PostProcessNode: work_order_draft missing"],
            }

        result = {
            "work_order": work_order_draft,
            "safety_checklist": safety_checklist,
            "citation_index": regulatory_citations,
            "compliance_flags": compliance_flags,
        }

        emit_trace_event(
            "document_assembled",
            {"compliant": not compliance_flags},
            state,
        )

        return {
            "result": result,
            "status": AgentStatus.ERROR.value if compliance_flags else AgentStatus.SUCCESS.value,
        }
