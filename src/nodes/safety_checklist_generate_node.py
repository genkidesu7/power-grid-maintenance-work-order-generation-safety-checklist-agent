"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Never import from mediator/, api/, or other agents
#
# Inner-graph node: run via GraphNode.execute() -> subgraph.invoke(user_input, ...).
# The inner graph's initial_state only ever contains user_input — always fall back.

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

from src.nodes._request_fields import parsed_request_field
from src.services.safety_checklist_service import SafetyChecklistService


class SafetyChecklistGenerateNode(FunctionNode):
    """Build the work-type-specific safety checklist (PPE, isolation steps,
    emergency contacts).

    Reads work_type (re-parsed from validated_input/user_input if absent
    from inner state). Writes safety_checklist.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Building the safety checklist...",
            metadata={"stage": "safety_checklist_generate"},
        )
        work_type = parsed_request_field(state, "work_type")
        if not work_type:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["SafetyChecklistGenerateNode: work_type missing"],
            }

        service = SafetyChecklistService()
        try:
            checklist: list[dict[str, Any]] = asyncio.run(service.generate(work_type))
        except TimeoutError as exc:
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"SafetyChecklistGenerateNode: [RETRY] {exc}"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"SafetyChecklistGenerateNode: [ERROR] {exc}"],
            }

        emit_trace_event(
            "safety_checklist_generated",
            {"work_type": work_type, "item_count": len(checklist)},
            state,
        )

        return {
            "safety_checklist": checklist,
            "status": AgentStatus.SUCCESS.value,
        }
