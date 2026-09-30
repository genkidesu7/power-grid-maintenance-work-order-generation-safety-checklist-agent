"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Never import from mediator/, api/, or other agents
#
# Inner-graph terminal node. Not retried on gaps found — a missing mandatory
# field or citation is a content-completeness issue, not a transient fault
# (docs/02_design.md "Error Handling").

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

from src.services.compliance_validation_service import ComplianceValidationService


class ComplianceValidateNode(FunctionNode):
    """Rule-check mandatory fields present + regulatory citation accuracy.

    Reads work_order_draft, regulatory_citations. Writes compliance_flags
    and terminal status: ERROR (with flags populated) if any gap is found,
    SUCCESS otherwise.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Validating work order compliance...",
            metadata={"stage": "compliance_validate"},
        )
        work_order_draft: dict[str, Any] = state.get("work_order_draft", {})
        regulatory_citations: list[dict[str, Any]] = state.get("regulatory_citations", [])

        service = ComplianceValidationService()
        flags: list[str] = asyncio.run(service.validate(work_order_draft, regulatory_citations))

        emit_trace_event(
            "compliance_validated",
            {"flag_count": len(flags)},
            state,
        )

        if flags:
            return {
                "compliance_flags": flags,
                "status": AgentStatus.ERROR.value,
                "error_log": [f"ComplianceValidateNode: {f}" for f in flags],
            }

        return {
            "compliance_flags": [],
            "status": AgentStatus.SUCCESS.value,
        }
