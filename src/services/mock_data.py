"""AgentCore Platform v1.0"""

# Mock-mode stub responses. Used only when mock_mode_enabled() is True —
# see src/services/mock_mode.py. Keeps fixture data out of service classes.

from __future__ import annotations

from typing import Any

_SAFETY_CHECKLISTS: dict[str, list[dict[str, Any]]] = {
    "transformer_replacement": [
        {"category": "PPE", "item": "絶縁手袋 (class 0, 1000V rated)", "mandatory": True},
        {"category": "PPE", "item": "絶縁靴", "mandatory": True},
        {"category": "isolation", "item": "変圧器一次側・二次側の開路確認", "mandatory": True},
        {"category": "isolation", "item": "検電器による無電圧確認", "mandatory": True},
        {"category": "emergency", "item": "現場責任者・緊急連絡先の掲示", "mandatory": True},
    ],
    "confined_space_entry": [
        {"category": "PPE", "item": "酸素濃度計・可燃性ガス検知器", "mandatory": True},
        {"category": "PPE", "item": "送気マスクまたは自給式呼吸器", "mandatory": True},
        {"category": "isolation", "item": "入槽前の酸素濃度・有毒ガス測定（18%以上）", "mandatory": True},
        {"category": "isolation", "item": "監視員の常時配置", "mandatory": True},
        {"category": "emergency", "item": "救出用具・避難経路の確保", "mandatory": True},
    ],
}

_DEFAULT_CHECKLIST: list[dict[str, Any]] = [
    {"category": "PPE", "item": "絶縁手袋", "mandatory": True},
    {"category": "isolation", "item": "停電確認・検電", "mandatory": True},
    {"category": "emergency", "item": "緊急連絡先の掲示", "mandatory": True},
]

_REGULATORY_CLAUSES: dict[str, list[dict[str, Any]]] = {
    "transformer_replacement": [
        {
            "law": "電気事業法",
            "article": "第39条",
            "text": "事業用電気工作物の技術基準適合維持義務（停電作業時の絶縁確保）",
        },
        {
            "law": "労働安全衛生規則",
            "article": "第349条",
            "text": "高圧活線近接作業における絶縁用保護具等の使用義務",
        },
    ],
    "confined_space_entry": [
        {
            "law": "労働安全衛生法",
            "article": "第五章 酸素欠乏症等防止規則",
            "text": "酸素欠乏危険場所における作業環境測定及び換気義務",
        },
        {
            "law": "労働安全衛生規則",
            "article": "第389条の2",
            "text": "酸素欠乏危険作業主任者の選任及び監視員の配置義務",
        },
    ],
}

_MANDATORY_WORK_ORDER_FIELDS = (
    "equipment_id",
    "location",
    "schedule",
    "crew_size",
    "work_type",
    "isolation_procedure",
)


async def stub_regulatory_retrieve(work_type: str) -> list[dict[str, Any]]:
    return _REGULATORY_CLAUSES.get(work_type, [])


async def stub_work_order_draft(
    work_type: str,
    equipment_id: str,
    location: str,
    schedule: str,
    crew_size: int,
    regulatory_citations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "work_type": work_type,
        "equipment_id": equipment_id,
        "location": location,
        "schedule": schedule,
        "crew_size": crew_size,
        "isolation_procedure": f"Standard isolation procedure for {work_type} (mock draft)",
        "citations": [f"{c['law']} {c['article']}" for c in regulatory_citations],
    }


async def stub_safety_checklist(work_type: str) -> list[dict[str, Any]]:
    return _SAFETY_CHECKLISTS.get(work_type, _DEFAULT_CHECKLIST)


async def stub_compliance_validate(
    work_order_draft: dict[str, Any],
    regulatory_citations: list[dict[str, Any]],
) -> list[str]:
    flags: list[str] = []
    for field in _MANDATORY_WORK_ORDER_FIELDS:
        if not work_order_draft.get(field):
            flags.append(f"missing mandatory field: {field}")
    if not regulatory_citations:
        flags.append("no regulatory citations retrieved")
    return flags
