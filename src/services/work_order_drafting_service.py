"""AgentCore Platform v1.0"""

# Service layer: domain queries, external API wrappers, data aggregation.
# Must NOT contain business logic or routing.
# Nodes call this; this is the one place that constructs AzureOpenAIClient.

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from framework.secrets.base import SecretProvider

from src.services.mock_mode import mock_mode_enabled

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a licensed electrical engineer drafting a 停電作業指示書 (power outage work order) "
    "for a qualified reviewer. Respond with a single JSON object with exactly one key, "
    '"isolation_procedure": a concise, numbered, step-by-step isolation procedure (de-energize, '
    "open/lock-out, verify no voltage, earth) appropriate to the work type. "
    "Do not include grid topology, substation coordinates or SCADA identifiers."
)


class WorkOrderDraftingService:
    """LLM-drafts the 停電作業指示書 with all mandatory fields.

    Usage from a node::

        service = WorkOrderDraftingService()
        draft = await service.draft(work_type, equipment_id, location,
                                     schedule, crew_size, regulatory_citations,
                                     credential_handle)
    """

    def __init__(self) -> None:
        self._mock_mode: bool = mock_mode_enabled()

    async def draft(
        self,
        work_type: str,
        equipment_id: str,
        location: str,
        schedule: str,
        crew_size: int,
        regulatory_citations: list[dict[str, Any]],
        credential_handle: SecretProvider | str,
    ) -> dict[str, Any]:
        """Draft the structured work order.

        Args:
            work_type: Parsed work type.
            equipment_id: Parsed equipment identifier.
            location: Parsed maintenance location (non-topological).
            schedule: Parsed maintenance schedule (ISO 8601 str).
            crew_size: Parsed crew size.
            regulatory_citations: Clauses retrieved for this work type.
            credential_handle: ``ctx.secrets`` (a SecretProvider) on the real
                path; the literal ``"mock"`` in mock mode. Never log or store it.

        Returns:
            Draft work order dict with mandatory fields.
        """
        if isinstance(credential_handle, str) and not credential_handle:
            raise ValueError(
                "WorkOrderDraftingService.draft: credential_handle is empty — " "check InvocationContext configuration"
            )
        return await self._call_llm(
            work_type, equipment_id, location, schedule, crew_size, regulatory_citations, credential_handle
        )

    async def _call_llm(
        self,
        work_type: str,
        equipment_id: str,
        location: str,
        schedule: str,
        crew_size: int,
        regulatory_citations: list[dict[str, Any]],
        credential_handle: SecretProvider | str,
    ) -> dict[str, Any]:
        if self._mock_mode:
            from src.services.mock_data import stub_work_order_draft

            return await stub_work_order_draft(
                work_type, equipment_id, location, schedule, crew_size, regulatory_citations
            )
        if isinstance(credential_handle, str):
            raise ValueError(
                "WorkOrderDraftingService._call_llm: real mode requires a SecretProvider (ctx.secrets), "
                "not a plain string"
            )

        prompt = json.dumps(
            {
                "work_type": work_type,
                "equipment_id": equipment_id,
                "location": location,
                "schedule": schedule,
                "crew_size": crew_size,
                "regulatory_citations": regulatory_citations,
            },
            ensure_ascii=False,
        )
        content = await asyncio.to_thread(self._complete, prompt, credential_handle)
        isolation_procedure = self._parse_isolation_procedure(content)
        return {
            "work_type": work_type,
            "equipment_id": equipment_id,
            "location": location,
            "schedule": schedule,
            "crew_size": crew_size,
            "isolation_procedure": isolation_procedure,
            "citations": [f"{c['law']} {c['article']}" for c in regulatory_citations],
        }

    @staticmethod
    def _complete(prompt: str, secrets: SecretProvider) -> str:
        from shared.services.llm.azure_openai_client import AzureOpenAIClient  # lazy import

        client = AzureOpenAIClient(
            config={
                "api_key": secrets.require("AZURE_OPENAI_API_KEY"),
                "azure_endpoint": secrets.require("AZURE_OPENAI_ENDPOINT"),
                "azure_deployment": secrets.require("AZURE_OPENAI_DEPLOYMENT"),
                "temperature": 0,
            }
        )
        response = client.complete(
            [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        return str(response["content"])

    @staticmethod
    def _parse_isolation_procedure(content: str) -> str:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`")
            text = text.removeprefix("json").strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError("WorkOrderDraftingService: LLM response was not valid JSON") from exc
        procedure = parsed.get("isolation_procedure") if isinstance(parsed, dict) else None
        if not isinstance(procedure, str) or not procedure.strip():
            raise ValueError("WorkOrderDraftingService: LLM response missing 'isolation_procedure'")
        return procedure.strip()
