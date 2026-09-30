import pytest

from src.services.compliance_validation_service import ComplianceValidationService

COMPLETE_DRAFT = {
    "equipment_id": "TR-1024",
    "location": "Site A",
    "schedule": "2026-08-01T09:00:00",
    "crew_size": 4,
    "work_type": "transformer_replacement",
    "isolation_procedure": "Standard isolation procedure",
}
CITATIONS = [{"law": "電気事業法", "article": "第39条", "text": "..."}]


@pytest.mark.asyncio
async def test_validate_complete_draft_returns_no_flags():
    service = ComplianceValidationService()
    flags = await service.validate(COMPLETE_DRAFT, CITATIONS)
    assert flags == []


@pytest.mark.asyncio
async def test_validate_missing_field_flagged():
    service = ComplianceValidationService()
    incomplete = dict(COMPLETE_DRAFT)
    del incomplete["isolation_procedure"]
    flags = await service.validate(incomplete, CITATIONS)
    assert any("isolation_procedure" in f for f in flags)


@pytest.mark.asyncio
async def test_validate_no_citations_flagged():
    service = ComplianceValidationService()
    flags = await service.validate(COMPLETE_DRAFT, [])
    assert any("citation" in f.lower() for f in flags)
