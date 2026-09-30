# Integration test: real .compile() + .invoke() through the compiled inner
# domain workflow graph directly (regulatory_retrieve -> work_order_draft ->
# safety_checklist_generate -> compliance_validate).

import json

from framework.schemas.invocation_context import InvocationContext
from framework.schemas.trust_level import TrustLevel
from framework.secrets.context import bound_secrets
from shared.secrets.inmemory_provider import InMemoryProvider

from src.graph.domain_workflow_graph import WorkOrderWorkflowGraph

VALID_REQUEST = json.dumps(
    {
        "work_type": "confined_space_entry",
        "equipment_id": "CS-88",
        "location": "Plant B",
        "schedule": "2026-08-05T10:00:00",
        "crew_size": 3,
    }
)


def test_inner_graph_compiles():
    graph = WorkOrderWorkflowGraph(config={})
    graph.compile()


def test_inner_graph_invoke_end_to_end_success(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    graph = WorkOrderWorkflowGraph(config={})
    graph.compile()
    provider = InMemoryProvider(
        {
            "AZURE_OPENAI_API_KEY": "mock-api-key-for-testing",
            "AZURE_OPENAI_ENDPOINT": "https://example.invalid",
            "AZURE_OPENAI_DEPLOYMENT": "mock-deployment",
        }
    )
    graph.provision_secrets(provider)

    ctx = InvocationContext(caller_trust_level=TrustLevel.VERIFIED_EXTERNAL)
    with bound_secrets(provider):
        result = graph.invoke(VALID_REQUEST, ctx=ctx)

    assert result["status"] == "success"
    assert result["work_order_draft"]["equipment_id"] == "CS-88"
    assert result["safety_checklist"]
    assert result["regulatory_citations"]
    assert result["compliance_flags"] == []
