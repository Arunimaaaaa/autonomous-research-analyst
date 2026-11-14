import operator
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """
    State shared across all nodes in the research LangGraph.
    Uses operator.add reducers for list fields so concurrent
    nodes (Analyst & RAG) can append safely without race conditions.
    """
    run_id: str
    ticker: str
    question: str

    # Reducer lists: any node can return elements to append to these lists
    tasks: Annotated[List[Dict[str, Any]], operator.add]
    documents: Annotated[List[Dict[str, Any]], operator.add]
    metrics: Annotated[List[Dict[str, Any]], operator.add]
    artifacts: Annotated[List[Dict[str, Any]], operator.add]
    agent_messages: Annotated[List[Dict[str, Any]], operator.add]

    # Shared mutable objects
    report_draft: Optional[Dict[str, Any]]
    verification_errors: Annotated[List[str], operator.add]
    iteration_count: int
    is_verified: bool
