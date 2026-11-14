import logging
from langgraph.graph import StateGraph, START, END
from app.orchestrator.state import AgentState
from app.orchestrator.nodes import (
    planner_node,
    data_agent_node,
    analyst_agent_node,
    rag_agent_node,
    writer_agent_node,
    critic_agent_node,
)

logger = logging.getLogger(__name__)


def should_continue_or_finish(state: AgentState) -> str:
    """Conditional router checking verification status and iteration threshold."""
    if state.get("is_verified", False):
        return "finish"
    if state.get("iteration_count", 0) >= 3:
        logger.warning("Max verification iterations reached (3). Forcing completion.")
        return "finish"
    logger.info("Report unverified. Routing back to writer for correction.")
    return "revise"


def create_research_graph():
    """
    Constructs and compiles the multi-agent research workflow graph.
    Topology:
      START
        └─> planner
              └─> data_agent
                    ├─> analyst_agent (quantitative) ──┐
                    └─> rag_agent     (qualitative)  ──┼─> writer_agent
                                                            └─> critic_agent
                                                                  ├─[verified / max iter]─> END
                                                                  └─[retry revision]─────> writer_agent
    """
    workflow = StateGraph(AgentState)

    # 1. Register Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("data_agent", data_agent_node)
    workflow.add_node("analyst_agent", analyst_agent_node)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("writer_agent", writer_agent_node)
    workflow.add_node("critic_agent", critic_agent_node)

    # 2. Add Edges
    workflow.add_edge(START, "planner")
    workflow.add_edge("planner", "data_agent")

    # Parallel Fan-Out from Data Agent to Analyst & RAG
    workflow.add_edge("data_agent", "analyst_agent")
    workflow.add_edge("data_agent", "rag_agent")

    # Fan-In from Analyst & RAG into Writer
    workflow.add_edge("analyst_agent", "writer_agent")
    workflow.add_edge("rag_agent", "writer_agent")

    # Critic Check
    workflow.add_edge("writer_agent", "critic_agent")

    # Conditional Self-Correction Loop
    workflow.add_conditional_edges(
        "critic_agent",
        should_continue_or_finish,
        {
            "finish": END,
            "revise": "writer_agent"
        }
    )

    return workflow.compile()


# Pre-compiled graph instance
research_graph = create_research_graph()
