"""AgentCore Platform v1.0"""

# Node contract (agents_layer_design.md §1):
#  - Extend FunctionNode; implement execute(state) -> dict
#  - Return ONLY the fields this node changes (never full state)
#  - Return AgentStatus enum constants — never plain strings [A1]
#  - Read input_context via state.get("input_context", {}) — read-only [C1]
#  - Never import from mediator/, api/, or other agents

from __future__ import annotations

import json
from typing import Any, ClassVar

from framework.errors import SecurityViolationError
from framework.nodes.function_node import FunctionNode
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel
from shared.services.events import emitter
from shared.services.events.types import EventType
from shared.utils.audit_logger import emit_trace_event

MAX_INPUT_CHARS = 2000
REQUIRED_FIELDS = ("work_type", "equipment_id", "location", "schedule", "crew_size")


class PreProcessNode(FunctionNode):
    """Parse and validate the structured maintenance request.

    Reads user_input (JSON string with work_type, equipment_id, location,
    schedule, crew_size). Writes validated_input and the parsed fields.
    """

    # Matches config/agent.yaml's agent-wide required_trust_level — this
    # agent is invoked by grid operations planners / scheduling tooling,
    # not anonymous callers.
    required_trust_level: ClassVar[TrustLevel] = TrustLevel.VERIFIED_EXTERNAL

    def _extra_security_gate_input(self, state: dict[str, Any]) -> dict[str, Any]:
        """S-2 domain extension: enforce max size (proposal §4: max 2000 chars)."""
        user_input = state.get("user_input", "")
        if not isinstance(user_input, str):
            raise SecurityViolationError("PreProcessNode: user_input must be a plain string")
        if len(user_input) > MAX_INPUT_CHARS:
            raise SecurityViolationError(f"PreProcessNode: user_input exceeds {MAX_INPUT_CHARS} chars")
        return state

    def execute(self, state: dict[str, Any]) -> dict[str, Any]:
        emitter().emit_event(
            event_type=EventType.PROGRESS_UPDATE,
            message="Validating the maintenance request...",
            metadata={"stage": "request_parse"},
        )
        user_input = state.get("user_input", "")

        if not user_input or not user_input.strip():
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PreProcessNode: user_input is empty or missing"],
            }

        try:
            parsed = json.loads(user_input)
        except (json.JSONDecodeError, TypeError):
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": ["PreProcessNode: user_input is not valid JSON"],
            }

        missing = [f for f in REQUIRED_FIELDS if not parsed.get(f)]
        if missing:
            return {
                "status": AgentStatus.ERROR.value,
                "error_log": [f"PreProcessNode: missing required fields: {', '.join(missing)}"],
            }

        emit_trace_event(
            "request_parsed",
            {"work_type": parsed["work_type"], "equipment_id": parsed["equipment_id"]},
            state,
        )

        return {
            "validated_input": user_input.strip(),
            "work_type": str(parsed["work_type"]),
            "equipment_id": str(parsed["equipment_id"]),
            "location": str(parsed["location"]),
            "schedule": str(parsed["schedule"]),
            "crew_size": int(parsed["crew_size"]),
            "status": AgentStatus.SUCCESS.value,
        }
