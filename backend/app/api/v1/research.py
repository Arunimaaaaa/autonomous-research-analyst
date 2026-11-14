import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, WebSocket, WebSocketDisconnect
from app.orchestrator.graph import research_graph
from app.orchestrator.state import AgentState
from app.schemas.research import (
    ResearchRequest,
    ResearchRunResponse,
    ReportResponse,
    CitationItem,
    AgentMessageItem,
    ArtifactItem
)

router = APIRouter()

# In-memory storage cache for runs and real-time streaming connections
# (Synced to SQLAlchemy models in production db)
RUNS_STORE: Dict[str, Dict[str, Any]] = {}
ACTIVE_STREAMS: Dict[str, List[WebSocket]] = {}


async def execute_research_workflow(run_id: str, ticker: str, question: str):
    """Executes the compiled LangGraph and broadcasts steps."""
    initial_state: AgentState = {
        "run_id": run_id,
        "ticker": ticker.upper(),
        "question": question,
        "tasks": [],
        "documents": [],
        "metrics": [],
        "artifacts": [],
        "agent_messages": [],
        "report_draft": None,
        "verification_errors": [],
        "iteration_count": 0,
        "is_verified": False,
    }

    try:
        RUNS_STORE[run_id]["status"] = "running"

        # Stream node execution events from LangGraph
        async for output in research_graph.astream(initial_state):
            for node_name, node_output in output.items():
                # Notify WebSocket subscribers if any
                if run_id in ACTIVE_STREAMS:
                    payload = {
                        "event": "node_complete",
                        "node": node_name,
                        "timestamp": datetime.utcnow().isoformat(),
                        "messages": [msg.get("content") for msg in node_output.get("agent_messages", [])]
                    }
                    for ws in ACTIVE_STREAMS[run_id]:
                        try:
                            await ws.send_json(payload)
                        except Exception:
                            pass

                # Accumulate state in in-memory store
                if "agent_messages" in node_output:
                    RUNS_STORE[run_id]["messages"].extend(node_output["agent_messages"])
                if "report_draft" in node_output and node_output["report_draft"]:
                    RUNS_STORE[run_id]["report"] = node_output["report_draft"]
                if "artifacts" in node_output:
                    RUNS_STORE[run_id]["artifacts"].extend(node_output["artifacts"])
                if "metrics" in node_output:
                    RUNS_STORE[run_id]["metrics"].extend(node_output["metrics"])

        RUNS_STORE[run_id]["status"] = "completed"
        RUNS_STORE[run_id]["finished_at"] = datetime.utcnow()

    except Exception as e:
        RUNS_STORE[run_id]["status"] = "failed"
        RUNS_STORE[run_id]["error"] = str(e)


@router.post("/research", response_model=ResearchRunResponse)
async def trigger_research(payload: ResearchRequest, background_tasks: BackgroundTasks):
    """Initiates an autonomous research run for a given ticker and question."""
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    now = datetime.utcnow()

    RUNS_STORE[run_id] = {
        "id": run_id,
        "ticker": payload.ticker.upper(),
        "question": payload.question,
        "status": "pending",
        "created_at": now,
        "finished_at": None,
        "messages": [],
        "artifacts": [],
        "metrics": [],
        "report": None,
    }

    # Run LangGraph pipeline asynchronously
    background_tasks.add_task(execute_research_workflow, run_id, payload.ticker, payload.question)

    return ResearchRunResponse(
        id=run_id,
        ticker=payload.ticker.upper(),
        question=payload.question,
        status="pending",
        created_at=now,
        total_tokens=0,
        total_cost=0.0
    )


@router.get("/runs/{run_id}", response_model=ResearchRunResponse)
async def get_run_status(run_id: str):
    """Retrieves status and metadata for a specific research run."""
    run = RUNS_STORE.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return ResearchRunResponse(
        id=run["id"],
        ticker=run["ticker"],
        question=run["question"],
        status=run["status"],
        created_at=run["created_at"],
        finished_at=run.get("finished_at"),
        total_tokens=0,
        total_cost=0.0
    )


@router.get("/runs/{run_id}/report", response_model=ReportResponse)
async def get_run_report(run_id: str):
    """Retrieves the synthesized research report with citations and disclaimer."""
    run = RUNS_STORE.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    report = run.get("report")
    if not report:
        raise HTTPException(status_code=400, detail="Report generation still in progress or failed.")

    citations = [
        CitationItem(
            claim=c["claim"],
            source_id=c["source_id"],
            source_type=c["source_type"],
            source_url=c.get("source_url")
        ) for c in report.get("citations", [])
    ]

    return ReportResponse(
        run_id=run_id,
        markdown=report["markdown"],
        citations=citations,
        disclaimer=report["disclaimer"]
    )


@router.get("/runs/{run_id}/trace", response_model=List[AgentMessageItem])
async def get_run_trace(run_id: str):
    """Retrieves the chronological agent trace and message logs."""
    run = RUNS_STORE.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return [
        AgentMessageItem(
            agent=m["agent"],
            role=m["role"],
            content=m["content"],
            tool_calls=m.get("tool_calls"),
            created_at=m.get("created_at", datetime.utcnow())
        ) for m in run.get("messages", [])
    ]


@router.get("/runs/{run_id}/artifacts", response_model=List[ArtifactItem])
async def get_run_artifacts(run_id: str):
    """Retrieves charts and table artifacts produced during the research run."""
    run = RUNS_STORE.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Research run not found.")

    return [
        ArtifactItem(
            kind=a["kind"],
            path=a["path"],
            caption=a["caption"],
            produced_by_task=a.get("produced_by_task")
        ) for a in run.get("artifacts", [])
    ]


@router.websocket("/runs/{run_id}/stream")
async def stream_run_steps(websocket: WebSocket, run_id: str):
    """WebSocket connection for real-time agent execution step streaming."""
    await websocket.accept()
    if run_id not in ACTIVE_STREAMS:
        ACTIVE_STREAMS[run_id] = []
    ACTIVE_STREAMS[run_id].append(websocket)

    try:
        while True:
            # Keep-alive heartbeat
            await websocket.receive_text()
    except WebSocketDisconnect:
        ACTIVE_STREAMS[run_id].remove(websocket)
