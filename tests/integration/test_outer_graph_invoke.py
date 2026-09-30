# Integration test: real .compile() + .invoke() through the compiled outer
# graph — not direct node/execute()/route() calls with a stubbed dict.
# LangGraph's runtime schema projection can silently differ from what a
# stubbed-state unit test observes (sdk-expertise "Running and
# smoke-testing locally").

import json

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from framework.secrets.context import bound_secrets
from shared.secrets.inmemory_provider import InMemoryProvider

from src.graph.graph import WorkOrderGenerationAgent

VALID_REQUEST = json.dumps(
    {
        "work_type": "transformer_replacement",
        "equipment_id": "TR-1024",
        "location": "Site A",
        "schedule": "2026-08-01T09:00:00",
        "crew_size": 4,
    }
)


def _mock_provider() -> InMemoryProvider:
    return InMemoryProvider(
        {
            "AZURE_OPENAI_API_KEY": "mock-api-key-for-testing",
            "AZURE_OPENAI_ENDPOINT": "https://example.invalid",
            "AZURE_OPENAI_DEPLOYMENT": "mock-deployment",
        }
    )


def test_outer_graph_compiles():
    agent = WorkOrderGenerationAgent(config={"max_retry": 1})
    agent.compile()


def test_outer_graph_invoke_end_to_end_success(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    agent = WorkOrderGenerationAgent(config={"max_retry": 1})
    agent.compile()
    provider = _mock_provider()
    agent.provision_secrets(provider)

    ctx = InvocationContext(caller_trust_level=TrustLevel.VERIFIED_EXTERNAL)
    with bound_secrets(provider):
        result = agent.invoke(VALID_REQUEST, ctx=ctx)

    assert result["status"] == "success"
    assert "PostProcessNode" in result["node_history"]
    assert result["output"]["work_order"]["equipment_id"] == "TR-1024"
    assert result["output"]["safety_checklist"]
    assert result["output"]["citation_index"]
    assert result["output"]["compliance_flags"] == []


def test_outer_graph_invoke_malformed_input_errors(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    agent = WorkOrderGenerationAgent(config={"max_retry": 1})
    agent.compile()
    provider = _mock_provider()
    agent.provision_secrets(provider)

    ctx = InvocationContext(caller_trust_level=TrustLevel.VERIFIED_EXTERNAL)
    with bound_secrets(provider):
        result = agent.invoke("not valid json", ctx=ctx)

    assert result["status"] == "error"
    assert "PostProcessNode" not in result["node_history"]


def test_outer_graph_invoke_anonymous_caller_denied_at_s1(monkeypatch):
    """Standalone caller with no elevated trust must be refused, not silently
    processed (S-1 gate)."""
    monkeypatch.setenv("USE_MOCK", "true")
    agent = WorkOrderGenerationAgent(config={"max_retry": 1})
    agent.compile()
    provider = _mock_provider()
    agent.provision_secrets(provider)

    ctx = InvocationContext(caller_trust_level=TrustLevel.ANONYMOUS)
    with bound_secrets(provider):
        result = agent.invoke(VALID_REQUEST, ctx=ctx)

    assert result["status"] == "error"
