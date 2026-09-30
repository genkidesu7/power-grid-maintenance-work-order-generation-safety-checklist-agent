# PB-3: Level 2 -> External service boundary.
# In mock mode the "external service" is the mock_data stub path — this
# confirms the service layer actually reaches and returns data from that
# boundary (rather than the node/service call silently no-op'ing).

import pytest

from src.services.regulatory_retrieval_service import RegulatoryRetrievalService
from src.services.safety_checklist_service import SafetyChecklistService
from src.services.work_order_drafting_service import WorkOrderDraftingService


@pytest.mark.asyncio
async def test_pb3_regulatory_retrieval_reaches_external_boundary(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = RegulatoryRetrievalService()
    data = await service.retrieve("transformer_replacement")
    assert data, "PB-3: no data retrieved across the external service boundary"


@pytest.mark.asyncio
async def test_pb3_work_order_drafting_reaches_external_boundary(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = WorkOrderDraftingService()
    data = await service.draft(
        "transformer_replacement", "TR-1", "Site A", "2026-08-01T09:00:00", 4, [], "mock-api-key-for-testing"
    )
    assert data, "PB-3: no data retrieved across the external service boundary"


@pytest.mark.asyncio
async def test_pb3_safety_checklist_reaches_external_boundary(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = SafetyChecklistService()
    data = await service.generate("confined_space_entry")
    assert data, "PB-3: no data retrieved across the external service boundary"


@pytest.mark.asyncio
async def test_pb3_real_llm_path_requires_secrets_not_placeholder(monkeypatch):
    """No mock flag (every accepted alias cleared) -> the real LLM path must
    demand the Azure secrets via require() and raise MissingSecret, never
    proceed on a placeholder credential."""
    from framework.secrets.base import MissingSecret, NullProvider

    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    service = WorkOrderDraftingService()
    with pytest.raises(MissingSecret):
        await service.draft("transformer_replacement", "TR-1", "Site A", "2026-08-01T09:00:00", 4, [], NullProvider())
