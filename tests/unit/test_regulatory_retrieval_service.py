import pytest

from src.services.regulatory_retrieval_service import RegulatoryRetrievalService


@pytest.mark.asyncio
async def test_retrieve_mock_mode_returns_clauses_for_known_work_type(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = RegulatoryRetrievalService()
    citations = await service.retrieve("transformer_replacement")
    assert citations
    assert all({"law", "article", "text"} <= c.keys() for c in citations)


@pytest.mark.asyncio
async def test_retrieve_empty_work_type_raises(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = RegulatoryRetrievalService()
    with pytest.raises(ValueError):
        await service.retrieve("")


@pytest.mark.asyncio
async def test_retrieve_non_mock_mode_serves_fixture_clauses(monkeypatch):
    """No KB client is provisioned: only the LLM is ever real, so retrieval
    serves the fixture clauses regardless of mock mode."""
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    service = RegulatoryRetrievalService()
    citations = await service.retrieve("transformer_replacement")
    assert citations
