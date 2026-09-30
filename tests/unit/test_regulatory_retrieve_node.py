from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.regulatory_retrieve_node import RegulatoryRetrieveNode


def _base_state(**overrides) -> dict:
    state = {
        "work_type": "transformer_replacement",
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }
    state.update(overrides)
    return state


def test_regulatory_retrieve_succeeds_with_no_secret_in_mock_mode(monkeypatch):
    """Regression test (test_rule.md Rule 2): a fresh CI checkout has no env/
    secret files at all. Mock mode must not depend on a secret being
    resolvable — no bound_secrets() context at all."""
    monkeypatch.setenv("USE_MOCK", "true")

    node = RegulatoryRetrieveNode()
    result = node.execute(_base_state())

    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["regulatory_citations"]


def test_regulatory_retrieve_falls_back_to_user_input_json(monkeypatch):
    """Inner graph's initial_state only has user_input — work_type must be
    re-derived from the raw JSON string when the outer-parsed field is
    absent."""
    monkeypatch.setenv("USE_MOCK", "true")
    state = {
        "user_input": '{"work_type": "confined_space_entry", "equipment_id": "CS-1"}',
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }
    node = RegulatoryRetrieveNode()
    result = node.execute(state)
    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["regulatory_citations"]


def test_regulatory_retrieve_missing_work_type_errors(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    node = RegulatoryRetrieveNode()
    state = _base_state()
    del state["work_type"]
    result = node.execute(state)
    assert result["status"] == AgentStatus.ERROR.value
