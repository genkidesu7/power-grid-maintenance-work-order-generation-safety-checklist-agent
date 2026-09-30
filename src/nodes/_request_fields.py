"""AgentCore Platform v1.0"""

# Shared helper for inner-graph nodes (src/graph/domain_workflow_graph.py).
#
# The inner graph's initial_state only ever contains user_input —
# BaseGraph.invoke() never copies the outer pre_process's parsed fields
# (work_type, equipment_id, ...) in, even though
# WorkOrderWorkflowGraphNode.extract_input() correctly prefers
# validated_input. Every inner node that needs a parsed request field must
# re-derive it here rather than treat the raw JSON string as the field
# value itself.

from __future__ import annotations

import json
from typing import Any


def parsed_request_field(state: dict[str, Any], field: str) -> Any:
    """Return state[field] if present; otherwise re-parse it from
    validated_input/user_input (the raw structured-request JSON string).

    Returns "" (or None) if the field cannot be resolved either way.
    """
    if state.get(field):
        return state[field]

    raw = state.get("validated_input", state.get("user_input", ""))
    if not raw:
        return ""

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return ""

    return parsed.get(field, "")
