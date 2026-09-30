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
from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

from src.nodes._request_fields import parsed_request_field
from src.services.mock_mode import mock_mode_enabled
from src.services.work_order_drafting_service import WorkOrderDraftingService


class WorkOrderDraftNode(FunctionNode):
    """LLM-draft the 停電作業指示書 with all mandatory fields.

    Reads work_type, equipment_id, location, schedule, crew_size (re-parsed
    from validated_input/user_input if absent from inner state),
    regulatory_citations. Writes work_order_draft.
    """

    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Drafting the work order with the LLM...",
            metadata={"stage": "work_order_draft"},
        )
        work_type = parsed_request_field(state, "work_type")
        equipment_id = parsed_request_field(state, "equipment_id")
        location = parsed_request_field(state, "location")
        schedule = parsed_request_field(state, "schedule")
        crew_size = parsed_request_field(state, "crew_size") or 0
        regulatory_citations: list[dict[str, Any]] = state.get("regulatory_citations", [])

        if not work_type or not equipment_id:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["WorkOrderDraftNode: work_type or equipment_id missing"],
            }

        # Mock mode's stub path never touches a real credential — do not
        # demand one to reach it (.claude/rules/implementation_rule.md Rule 2).
        # The AZURE_OPENAI_* secrets are require()d in the service's single
        # AzureOpenAIClient construction site, so a real deployment with a
        # missing secret fails fast rather than proceeding on a placeholder.
        credential_handle = "mock" if mock_mode_enabled() else InvocationContext.from_state(state).secrets

        service = WorkOrderDraftingService()
        try:
            draft: dict[str, Any] = asyncio.run(
                service.draft(
                    work_type,
                    equipment_id,
                    location,
                    schedule,
                    crew_size,
                    regulatory_citations,
                    credential_handle,
                )
            )
        except TimeoutError as exc:
            return {
                "status": AgentStatus.RETRY.value,
                "error_log": [f"WorkOrderDraftNode: [RETRY] {exc}"],
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"WorkOrderDraftNode: [ERROR] {exc}"],
            }

        emit_trace_event(
            "work_order_drafted",
            {"work_type": work_type, "equipment_id": equipment_id},
            state,
        )

        return {
            "work_order_draft": draft,
            "status": AgentStatus.SUCCESS.value,
        }
