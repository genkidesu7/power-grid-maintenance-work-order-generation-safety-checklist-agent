"""AgentCore Platform v1.0"""

# Service layer: domain queries, external API wrappers, data aggregation.
# Must NOT contain business logic, routing, or credentials.
# Nodes call this; this calls shared/services/ for external integrations.

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RegulatoryRetrievalService:
    """Look-up of 電気事業法 + 労働安全衛生法 clauses for a work type.

    No regulatory knowledge-base client is provisioned for this agent, so
    retrieval is served from the fixture clauses in ``mock_data.py`` in every
    mode — only the LLM drafting call is ever real. Replace
    ``_call_external`` with a vector-search client once a knowledge base is
    provisioned.

    Usage from a node::

        service = RegulatoryRetrievalService()
        citations = await service.retrieve(work_type)
    """

    async def retrieve(self, work_type: str) -> list[dict[str, Any]]:
        """Retrieve regulatory clauses matching the given work type.

        Args:
            work_type: Parsed work type (e.g. "transformer_replacement").

        Returns:
            List of clause dicts: {law, article, text}.
        """
        if not work_type:
            raise ValueError("RegulatoryRetrievalService.retrieve: work_type is empty")
        return await self._call_external(work_type)

    async def _call_external(self, work_type: str) -> list[dict[str, Any]]:
        from src.services.mock_data import stub_regulatory_retrieve

        return await stub_regulatory_retrieve(work_type)
