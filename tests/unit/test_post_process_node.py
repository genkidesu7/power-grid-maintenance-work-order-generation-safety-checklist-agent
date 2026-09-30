from framework.errors import SecurityViolationError
from framework.schemas.agent_status import AgentStatus
from framework.schemas.trust_level import TrustLevel

from src.nodes.post_process_node import PostProcessNode

DRAFT = {"equipment_id": "TR-1024", "work_type": "transformer_replacement"}


def _base_state(**overrides) -> dict:
    state = {
        "work_order_draft": DRAFT,
        "safety_checklist": [{"category": "PPE", "item": "gloves", "mandatory": True}],
        "regulatory_citations": [{"law": "電気事業法", "article": "第39条", "text": "..."}],
        "compliance_flags": [],
        "caller_trust_level": TrustLevel.VERIFIED_EXTERNAL.value,
        "correlation_id": "test-corr",
        "session_id": "test-session",
        "thread_id": "test-thread",
        "trace_id": "test-trace",
    }
    state.update(overrides)
    return state


def test_post_process_assembles_document_on_success():
    node = PostProcessNode()
    result = node.execute(_base_state())
    assert result["status"] == AgentStatus.SUCCESS.value
    assert result["result"]["work_order"] == DRAFT


def test_post_process_missing_draft_errors():
    node = PostProcessNode()
    state = _base_state(work_order_draft={})
    result = node.execute(state)
    assert result["status"] == AgentStatus.ERROR.value


def test_post_process_propagates_compliance_flags_as_error():
    node = PostProcessNode()
    result = node.execute(_base_state(compliance_flags=["missing mandatory field: schedule"]))
    assert result["status"] == AgentStatus.ERROR.value


def test_post_process_s3_gate_blocks_scada_identifier():
    """S-3 domain gate must raise, not silently pass, when a SCADA
    identifier pattern is present in the assembled result."""
    node = PostProcessNode()
    result = {"result": {"work_order": {**DRAFT, "notes": "SCADA-99231 reroute"}}}
    try:
        node._extra_security_gate_output(result)
        raised = False
    except SecurityViolationError:
        raised = True
    assert raised


def test_post_process_s3_gate_allows_clean_output():
    node = PostProcessNode()
    result = {"result": {"work_order": DRAFT}}
    returned = node._extra_security_gate_output(result)
    assert returned is result
