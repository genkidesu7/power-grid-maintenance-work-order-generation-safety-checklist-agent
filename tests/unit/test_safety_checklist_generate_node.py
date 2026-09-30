from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.safety_checklist_generate_node import SafetyChecklistGenerateNode


def _base_state(**overrides) -> dict:
    state = {
        "work_type": "confined_space_entry",
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }
    state.update(overrides)
    return state


def test_safety_checklist_generate_succeeds_in_mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    node = SafetyChecklistGenerateNode()
    result = node.execute(_base_state())
    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["safety_checklist"]


def test_safety_checklist_generate_missing_work_type_errors(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    node = SafetyChecklistGenerateNode()
    state = _base_state()
    del state["work_type"]
    result = node.execute(state)
    assert result["status"] == AgentStatus.ERROR.value
