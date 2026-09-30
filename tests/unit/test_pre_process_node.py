import json

from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.pre_process_node import PreProcessNode

VALID_REQUEST = json.dumps(
    {
        "work_type": "transformer_replacement",
        "equipment_id": "TR-1024",
        "location": "Site A",
        "schedule": "2026-08-01T09:00:00",
        "crew_size": 4,
    }
)


def _base_state(user_input: str) -> dict:
    return {
        "user_input": user_input,
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }


def test_pre_process_parses_valid_request():
    node = PreProcessNode()
    result = node.execute(_base_state(VALID_REQUEST))
    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["work_type"] == "transformer_replacement"
    assert result["equipment_id"] == "TR-1024"
    assert result["crew_size"] == 4
    assert result["validated_input"] == VALID_REQUEST


def test_pre_process_empty_input_errors():
    node = PreProcessNode()
    result = node.execute(_base_state(""))
    assert result["status"] == AgentStatus.ERROR.value


def test_pre_process_invalid_json_errors():
    node = PreProcessNode()
    result = node.execute(_base_state("not json"))
    assert result["status"] == AgentStatus.ERROR.value


def test_pre_process_missing_required_field_errors():
    incomplete = json.dumps({"work_type": "transformer_replacement"})
    node = PreProcessNode()
    result = node.execute(_base_state(incomplete))
    assert result["status"] == AgentStatus.ERROR.value
    assert "missing required fields" in result["error_log"][0]


def test_pre_process_full_call_through_security_gates():
    """Exercise __call__() end-to-end (S-1 -> S-2 -> execute -> S-3)."""
    node = PreProcessNode()
    result = node(_base_state(VALID_REQUEST))
    assert result["status"] == AgentStatus.SUCCESS.value
