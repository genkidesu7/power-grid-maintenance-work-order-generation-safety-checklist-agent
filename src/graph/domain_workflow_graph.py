"""AgentCore Platform v1.0"""

# src/graph/domain_workflow_graph.py
#
# Inner graph for the Cat 2 work-order generation workflow. Instantiated by
# WorkOrderWorkflowGraphNode.get_subgraph() in src/graph/graph.py.
# src/graph/ is the ONLY accepted path for this file.
#
# Pipeline:
#   START → regulatory_retrieve → work_order_draft → safety_checklist_generate
#         → compliance_validate → {route} → END
#
# Inherits BaseGraph (fully custom topology) — the four domain steps don't
# map onto pre_process/main/post_process slots.

from typing import Any

from langgraph.graph import END, START

from framework.graph.base_graph import BaseGraph
from framework.schemas.agent_status import AgentStatus
from src.nodes.compliance_validate_node import ComplianceValidateNode
from src.nodes.regulatory_retrieve_node import RegulatoryRetrieveNode
from src.nodes.safety_checklist_generate_node import SafetyChecklistGenerateNode
from src.nodes.work_order_draft_node import WorkOrderDraftNode
from src.schemas.state import State


class WorkOrderWorkflowGraph(BaseGraph):
    """Inner graph: regulatory retrieve -> draft -> safety checklist -> compliance validate.

    Called by WorkOrderWorkflowGraphNode.get_subgraph() in src/graph/graph.py.
    """

    # ── Identity ──────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "work_order_generation_workflow"

    @property
    def state_schema(self) -> type:
        return State

    # ── Config validation ────────────────────────────────────────────────

    def _validate_config(self) -> None:
        """No mandatory config for this inner graph."""
        pass

    # ── Node registration ────────────────────────────────────────────────

    def register_nodes(self) -> None:
        """No super() call — BaseGraph.register_nodes() is abstract.

        Do NOT register initialize/finalize — outer backbone concern.
        """
        self._nodes["regulatory_retrieve"] = RegulatoryRetrieveNode()
        self._nodes["work_order_draft"] = WorkOrderDraftNode()
        self._nodes["safety_checklist_generate"] = SafetyChecklistGenerateNode()
        self._nodes["compliance_validate"] = ComplianceValidateNode()

    # ── Edge wiring ───────────────────────────────────────────────────────

    def add_edges(self) -> None:
        self._sg.add_edge(START, "regulatory_retrieve")
        self._sg.add_edge("regulatory_retrieve", "work_order_draft")
        self._sg.add_edge("work_order_draft", "safety_checklist_generate")
        self._sg.add_edge("safety_checklist_generate", "compliance_validate")
        self._sg.add_conditional_edges("compliance_validate", self.route)

    # ── Routing ───────────────────────────────────────────────────────────

    def route(self, state: State) -> str:
        """compliance_validate is terminal — ERROR or SUCCESS both end here.

        A missing mandatory field/citation is a content-completeness issue,
        not a transient fault (docs/02_design.md "Error Handling") — it is
        not retried within the inner graph.
        """
        return END

    # ── Output shape ─────────────────────────────────────────────────────

    def get_output(self, state: State) -> dict[str, Any]:
        """Shape the sub_result dict passed to the outer merge_output()."""
        return {
            "work_order_draft": state.get("work_order_draft", {}),
            "safety_checklist": state.get("safety_checklist", []),
            "regulatory_citations": state.get("regulatory_citations", []),
            "compliance_flags": state.get("compliance_flags", []),
            "status": state.get("status", AgentStatus.SUCCESS.value),
        }
