"""AgentCore Platform v1.0"""

# Service layer: work-type-conditional safety checklist rule lookup (PPE,
# isolation steps, emergency contacts). Must NOT contain business routing or
# credentials.
#
# No live rule-engine backend is provisioned for this template. Per
# agenticstar-deploy's hard rule 2 ("every other service defaults to mock,
# including in real mode — only the LLM call is ever real"), this service
# always returns the sanctioned mock_data.py stub, regardless of
# mock_mode_enabled(). It never gates on it and never raises a stand-in
# error — this IS the real, intended behavior for checklist lookup today.

from __future__ import annotations

from typing import Any


class SafetyChecklistService:
    """Work-type-conditional safety checklist lookup. Always mock — see module docstring.

    Usage from a node::

        service = SafetyChecklistService()
        checklist = await service.generate(work_type)
    """

    async def generate(self, work_type: str) -> list[dict[str, Any]]:
        """Generate the safety checklist for the given work type.

        Args:
            work_type: Parsed work type (e.g. "confined_space_entry").

        Returns:
            List of checklist item dicts: {category, item, mandatory}.
        """
        if not work_type:
            raise ValueError("SafetyChecklistService.generate: work_type is empty")
        from src.services.mock_data import stub_safety_checklist

        return await stub_safety_checklist(work_type)
