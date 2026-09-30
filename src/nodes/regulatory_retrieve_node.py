"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Never import from mediator/, api/, or other agents
#
# Inner-graph node: run via GraphNode.execute() -> subgraph.invoke(user_input, ...).
# The inner graph's initial_state only ever contains user_input (BaseGraph.invoke()
# never copies the outer pre_process's validated_input in) — always fall back.

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
from src.services.regulatory_retrieval_service import RegulatoryRetrievalService


class RegulatoryRetrieveNode(FunctionNode):
    """Vector search 電気事業法 + 労働安全衛生法 for the parsed work type.

    Reads work_type (re-parsed from validated_input/user_input if the
    outer-computed field is absent from the inner graph's fresh state).
    Writes regulatory_citations.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Retrieving applicable regulations...",
            metadata={"stage": "regulatory_retrieve"},
        )
        work_type = parsed_request_field(state, "work_type")
        if not work_type:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["RegulatoryRetrieveNode: work_type missing"],
            }

        service = RegulatoryRetrievalService()
        try:
            citations: list[dict[str, Any]] = asyncio.run(service.retrieve(work_type))
        except TimeoutError as exc:
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"RegulatoryRetrieveNode: [RETRY] {exc}"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"RegulatoryRetrieveNode: [ERROR] {exc}"],
            }

        emit_trace_event(
            "regulatory_clauses_retrieved",
            {"work_type": work_type, "clause_count": len(citations)},
            state,
        )

        return {
            "regulatory_citations": citations,
            "status": AgentStatus.SUCCESS.value,
        }
