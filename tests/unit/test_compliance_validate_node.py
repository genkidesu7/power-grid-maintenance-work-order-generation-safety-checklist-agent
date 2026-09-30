from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.compliance_validate_node import ComplianceValidateNode

COMPLETE_DRAFT = {
    "equipment_id": "TR-1024",
    "location": "Site A",
    "schedule": "2026-08-01T09:00:00",
    "crew_size": 4,
    "work_type": "transformer_replacement",
    "isolation_procedure": "Standard isolation procedure",
}
CITATIONS = [{"law": "電気事業法", "article": "第39条", "text": "..."}]


def _base_state(**overrides) -> dict:
    state = {
        "work_order_draft": COMPLETE_DRAFT,
        "regulatory_citations": CITATIONS,
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }
    state.update(overrides)
    return state


def test_compliance_validate_complete_draft_succeeds():
    node = ComplianceValidateNode()
    result = node.execute(_base_state())
    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["compliance_flags"] == []


def test_compliance_validate_incomplete_draft_errors_not_retries():
    """A missing mandatory field is a content-completeness issue, not a
    transient fault — must be ERROR, never RETRY (docs/02_design.md)."""
    incomplete = dict(COMPLETE_DRAFT)
    del incomplete["isolation_procedure"]
    node = ComplianceValidateNode()
    result = node.execute(_base_state(work_order_draft=incomplete))
    assert result["status"] == AgentStatus.ERROR.value
    assert result["compliance_flags"]
