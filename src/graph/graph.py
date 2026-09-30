"""AgentCore Platform v1.0"""

# Cat 2 — Power Grid Maintenance Work Order Generation & Safety Checklist Agent
#
#   Parent  : AgentBaseGraph (outer graph, this file) + GraphNode in the
#             `main` slot wrapping the inner domain workflow graph.
#   Pipeline: START → initialize → pre_process → main → {route} → post_process → finalize → END
#                                             ↓ (RETRY, max 3)
#                                          pre_process
#   Layout  : src/graph/graph.py                 ← outer graph (this file)
#             src/graph/domain_workflow_graph.py ← inner graph (regulatory
#                                                   retrieve -> draft ->
#                                                   safety checklist ->
#                                                   compliance validate)
#
# See docs/02_design.md for the full architecture rationale.

from typing import Any, ClassVar

from framework.graph.agent_base_graph import AgentBaseGraph
from framework.nodes.graph_node import GraphNode
from framework.schemas.agent_state import AgentState
from src.nodes.pre_process_node import PreProcessNode
from src.nodes.post_process_node import PostProcessNode
from src.schemas.state import State


class WorkOrderWorkflowGraphNode(GraphNode):
    """Wraps the inner domain workflow graph; assigned to the `main` slot."""

    # A failed/incomplete draft must surface as a hard error, not a
    # degraded-but-still-returned "success" — the mandatory human review
    # gate depends on receiving either a complete draft or an explicit
    # failure (docs/02_design.md Design Decision Record).
    error_strategy: ClassVar[str] = "propagate"

    # Approval is an out-of-band human process, not an in-graph interrupt.
    propagate_hitl: ClassVar[bool] = False

    def get_subgraph(self) -> Any:
        from src.graph.domain_workflow_graph import WorkOrderWorkflowGraph

        return WorkOrderWorkflowGraph(config=self._parent_config())

    def extract_input(self, state: AgentState) -> str:
        return str(state.get("validated_input", state.get("user_input", "")))

    def merge_output(self, state: AgentState, sub_result: dict[str, Any]) -> dict[str, Any]:
        """1:1 field mapping — outer post_process consumes these directly."""
        return {
            "work_order_draft": sub_result.get("work_order_draft", {}),
            "safety_checklist": sub_result.get("safety_checklist", []),
            "regulatory_citations": sub_result.get("regulatory_citations", []),
            "compliance_flags": sub_result.get("compliance_flags", []),
            "status": sub_result.get("status"),
        }

    def _parent_config(self) -> dict[str, Any]:
        return {}


class WorkOrderGenerationAgent(AgentBaseGraph):
    """Cat 2 outer graph — Power Grid Maintenance Work Order Generation & Safety Checklist Agent.

    Domain logic is encapsulated in WorkOrderWorkflowGraphNode (`main` slot).
    Backbone: initialize → pre_process → main → post_process → finalize (fixed).
    """

    @property
    def name(self) -> str:
        return "ene_c2_034_work_order_generation"

    @property
    def state_schema(self) -> type:
        return State

    def register_nodes(self) -> None:
        super().register_nodes()  # injects InitializeNode + FinalizeNode

        self._nodes["pre_process"] = PreProcessNode()
        self._nodes["main"] = WorkOrderWorkflowGraphNode()
        self._nodes["post_process"] = PostProcessNode()

    # add_edges() is NOT overridden — backbone wiring belongs to the framework.
