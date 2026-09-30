import pytest

from src.services.safety_checklist_service import SafetyChecklistService


@pytest.mark.asyncio
async def test_generate_produces_different_checklists_for_different_work_types(monkeypatch):
    """Proves work-type-conditional logic, not a static template."""
    monkeypatch.setenv("USE_MOCK", "true")
    service = SafetyChecklistService()
    transformer = await service.generate("transformer_replacement")
    confined_space = await service.generate("confined_space_entry")
    assert transformer != confined_space
    assert transformer
    assert confined_space


@pytest.mark.asyncio
async def test_generate_empty_work_type_raises(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    service = SafetyChecklistService()
    with pytest.raises(ValueError):
        await service.generate("")
