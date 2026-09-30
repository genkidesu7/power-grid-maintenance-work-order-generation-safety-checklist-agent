import pytest

from src.services.work_order_drafting_service import WorkOrderDraftingService


@pytest.mark.asyncio
async def test_draft_mock_mode_returns_structured_draft(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = WorkOrderDraftingService()
    draft = await service.draft(
        "transformer_replacement", "TR-1024", "Site A", "2026-08-01T09:00:00", 4, [], "mock-api-key-for-testing"
    )
    assert draft["work_type"] == "transformer_replacement"
    assert draft["equipment_id"] == "TR-1024"
    assert "isolation_procedure" in draft


@pytest.mark.asyncio
async def test_draft_empty_credential_raises(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = WorkOrderDraftingService()
    with pytest.raises(ValueError):
        await service.draft("transformer_replacement", "TR-1024", "Site A", "2026-08-01T09:00:00", 4, [], "")


class _FakeSecrets:
    def require(self, key: str) -> str:
        return f"value-for-{key}"


@pytest.mark.asyncio
async def test_draft_real_mode_uses_llm_response(monkeypatch):
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    monkeypatch.setattr(
        WorkOrderDraftingService,
        "_complete",
        staticmethod(lambda prompt, secrets: '{"isolation_procedure": "1. Open breaker"}'),
    )
    service = WorkOrderDraftingService()
    draft = await service.draft(
        "transformer_replacement",
        "TR-1024",
        "Site A",
        "2026-08-01T09:00:00",
        4,
        [{"law": "L", "article": "A", "text": "t"}],
        _FakeSecrets(),
    )
    assert draft["isolation_procedure"] == "1. Open breaker"
    assert draft["citations"] == ["L A"]


@pytest.mark.asyncio
async def test_draft_real_mode_invalid_llm_json_raises(monkeypatch):
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    monkeypatch.setattr(WorkOrderDraftingService, "_complete", staticmethod(lambda prompt, secrets: "not json"))
    service = WorkOrderDraftingService()
    with pytest.raises(ValueError):
        await service.draft("transformer_replacement", "TR-1024", "Site A", "s", 4, [], _FakeSecrets())


@pytest.mark.asyncio
async def test_draft_real_mode_rejects_plain_string_credential(monkeypatch):
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    service = WorkOrderDraftingService()
    with pytest.raises(ValueError):
        await service.draft("transformer_replacement", "TR-1024", "Site A", "s", 4, [], "placeholder")
