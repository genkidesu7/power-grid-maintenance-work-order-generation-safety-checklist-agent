from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.work_order_draft_node import WorkOrderDraftNode


def _base_state(**overrides) -> dict:
    state = {
        "work_type": "transformer_replacement",
        "equipment_id": "TR-1024",
        "location": "Site A",
        "schedule": "2026-08-01T09:00:00",
        "crew_size": 4,
        "regulatory_citations": [{"law": "電気事業法", "article": "第39条", "text": "..."}],
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }
    state.update(overrides)
    return state


def test_work_order_draft_succeeds_with_no_secret_in_mock_mode(monkeypatch):
    """Regression test (test_rule.md Rule 2): mock mode must not require a
    resolvable AZURE_OPENAI_* secret — no bound_secrets() context at all."""
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)

    node = WorkOrderDraftNode()
    result = node.execute(_base_state())

    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["work_order_draft"]["equipment_id"] == "TR-1024"


def test_work_order_draft_missing_equipment_id_errors(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    node = WorkOrderDraftNode()
    state = _base_state()
    del state["equipment_id"]
    result = node.execute(state)
    assert result["status"] == AgentStatus.ERROR.value
