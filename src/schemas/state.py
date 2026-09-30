"""AgentCore Platform v1.0"""

# ADR-005: State must be a flat TypedDict (see ADR-005 for the prohibited
# alternatives). LangGraph checkpoints use msgpack serialization, so only
# plain serializable fields are allowed. Do NOT add credentials or secrets.

from typing import Any

from framework.schemas.agent_state import AgentState


class State(AgentState):
    """Agent state.

    All shared fields (user_input, status, session_id, node_history,
    error_log, hitl_*, etc.) are inherited from AgentState.
    """

    # Set by pre_process: parsed structured maintenance request fields.
    validated_input: str
    work_type: str
    equipment_id: str
    location: str
    schedule: str
    crew_size: int

    # Set by main (inner domain workflow): regulatory retrieval, drafting,
    # safety checklist, and compliance validation outputs.
    regulatory_citations: list[dict[str, Any]]
    work_order_draft: dict[str, Any]
    safety_checklist: list[dict[str, Any]]
    compliance_flags: list[str]

    # Set by post_process: final assembled document.
    result: dict[str, Any]
