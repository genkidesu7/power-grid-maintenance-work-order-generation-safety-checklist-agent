"""AgentCore Platform v1.0"""

# Service layer: domain queries, external API wrappers, data aggregation.
# Must NOT contain business logic, routing, or credentials.
# Nodes call this; this calls shared/services/ for external integrations.

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ComplianceValidationService:
    """Rule-based check that a work order draft has all mandatory fields
    and that regulatory citations were actually retrieved.

    Purely local, deterministic rule evaluation — no external call, no
    credential, no mock-mode gate needed.

    Usage from a node::

        service = ComplianceValidationService()
        flags = await service.validate(work_order_draft, regulatory_citations)
    """

    _MANDATORY_FIELDS: tuple[str, ...] = (
        "equipment_id",
        "location",
        "schedule",
        "crew_size",
        "work_type",
        "isolation_procedure",
    )

    async def validate(
        self,
        work_order_draft: dict[str, Any],
        regulatory_citations: list[dict[str, Any]],
    ) -> list[str]:
        """Validate mandatory fields and citation presence.

        Args:
            work_order_draft: Drafted 停電作業指示書 fields.
            regulatory_citations: Clauses retrieved for this work type.

        Returns:
            List of flag strings describing gaps. Empty list = compliant.
        """
        flags: list[str] = []
        for field in self._MANDATORY_FIELDS:
            if not work_order_draft.get(field):
                flags.append(f"missing mandatory field: {field}")
        if not regulatory_citations:
            flags.append("no regulatory citations retrieved")
        return flags
