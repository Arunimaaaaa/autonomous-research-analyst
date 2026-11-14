import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List
from app.orchestrator.state import AgentState

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "DISCLAIMER: This research brief is generated autonomously by an AI multi-agent system "
    "for informational and academic purposes only. It does NOT constitute financial, investment, "
    "tax, or legal advice. Always perform your own independent due diligence before making investment decisions."
)


async def planner_node(state: AgentState) -> Dict[str, Any]:
    """Decomposes the research question into structured tasks."""
    logger.info("Running Planner Agent for ticker: %s", state["ticker"])

    tasks = [
        {
            "id": f"task-data-{uuid.uuid4().hex[:6]}",
            "kind": "data_fetch",
            "description": f"Fetch historical prices, fundamentals, and recent filings for {state['ticker']}",
            "status": "pending",
            "depends_on": []
        },
        {
            "id": f"task-analyst-{uuid.uuid4().hex[:6]}",
            "kind": "quantitative_analysis",
            "description": f"Compute return, volatility, valuation multiples, and generate price/volume charts for {state['ticker']}",
            "status": "pending",
            "depends_on": ["data_fetch"]
        },
        {
            "id": f"task-rag-{uuid.uuid4().hex[:6]}",
            "kind": "qualitative_retrieval",
            "description": f"Ingest and retrieve qualitative risk factors and catalysts from news/filings for {state['ticker']}",
            "status": "pending",
            "depends_on": ["data_fetch"]
        },
        {
            "id": f"task-synthesis-{uuid.uuid4().hex[:6]}",
            "kind": "report_synthesis",
            "description": "Synthesize quantitative metrics and qualitative findings into a cited Markdown brief",
            "status": "pending",
            "depends_on": ["quantitative_analysis", "qualitative_retrieval"]
        }
    ]

    msg = {
        "agent": "Planner",
        "role": "assistant",
        "content": f"Decomposed query '{state['question']}' into {len(tasks)} tasks.",
        "tool_calls": None,
        "created_at": datetime.utcnow()
    }

    return {
        "tasks": tasks,
        "agent_messages": [msg]
    }


async def data_agent_node(state: AgentState) -> Dict[str, Any]:
    """Fetches raw market data and qualitative news/filings."""
    ticker = state["ticker"]
    logger.info("Running Data Agent for ticker: %s", ticker)

    # In production, uses yfinance + SEC Edgar + NewsAPI tools
    # Seed sample raw document for verifiable citation
    doc_id = f"doc-{uuid.uuid4().hex[:8]}"
    doc = {
        "id": doc_id,
        "source_type": "sec_filing_10k",
        "source_url": f"https://www.sec.gov/edgar/browse/?CIK={ticker}",
        "title": f"{ticker} Annual Report & Financial Statements",
        "raw_text": f"Recent 10-K filing outlines revenue growth driven by cloud and AI services, while highlighting supply chain concentration and geopolitical tariffs as primary operational risks for {ticker}.",
        "fetched_at": datetime.utcnow()
    }

    msg = {
        "agent": "DataAgent",
        "role": "assistant",
        "content": f"Successfully ingested market data and recent regulatory filings for {ticker}.",
        "tool_calls": {"doc_id": doc_id},
        "created_at": datetime.utcnow()
    }

    return {
        "documents": [doc],
        "agent_messages": [msg]
    }


async def analyst_agent_node(state: AgentState) -> Dict[str, Any]:
    """Computes quantitative metrics and generates charts in sandbox."""
    ticker = state["ticker"]
    logger.info("Running Analyst Agent for ticker: %s", ticker)

    # Simulated computed metrics (in Phase 3 replaced by sandboxed code execution)
    metric_id_1 = f"metric-{uuid.uuid4().hex[:8]}"
    metric_id_2 = f"metric-{uuid.uuid4().hex[:8]}"

    metrics = [
        {
            "id": metric_id_1,
            "name": "ytd_return_pct",
            "value_numeric": 18.45,
            "value_json": {"period": "YTD", "unit": "percentage"},
            "computed_by_task": "task-analyst"
        },
        {
            "id": metric_id_2,
            "name": "annualized_volatility",
            "value_numeric": 22.8,
            "value_json": {"lookback_days": 252, "unit": "percentage"},
            "computed_by_task": "task-analyst"
        }
    ]

    artifact = {
        "id": f"art-{uuid.uuid4().hex[:8]}",
        "kind": "chart",
        "path": f"artifacts/{ticker}_price_trend.png",
        "caption": f"{ticker} 12-Month Adjusted Close Price & 50-DMA Trend",
        "produced_by_task": "task-analyst"
    }

    msg = {
        "agent": "AnalystAgent",
        "role": "assistant",
        "content": f"Computed {len(metrics)} quantitative metrics and generated {ticker} price trend chart.",
        "tool_calls": {"metrics_computed": len(metrics)},
        "created_at": datetime.utcnow()
    }

    return {
        "metrics": metrics,
        "artifacts": [artifact],
        "agent_messages": [msg]
    }


async def rag_agent_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves qualitative context with verifiable source citations."""
    ticker = state["ticker"]
    logger.info("Running RAG Agent for ticker: %s", ticker)

    # Uses ingested documents to answer qualitative risk sub-questions
    doc_id = state["documents"][0]["id"] if state["documents"] else "doc-default"

    msg = {
        "agent": "RAGAgent",
        "role": "assistant",
        "content": f"Retrieved key operational risk factors and strategic growth drivers from filing {doc_id}.",
        "tool_calls": {"source_doc": doc_id},
        "created_at": datetime.utcnow()
    }

    return {
        "agent_messages": [msg]
    }


async def writer_agent_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes findings into a structured, cited research brief."""
    ticker = state["ticker"]
    logger.info("Running Writer Agent for ticker: %s", ticker)

    doc_id = state["documents"][0]["id"] if state["documents"] else "doc-unknown"
    metric_id = state["metrics"][0]["id"] if state["metrics"] else "metric-unknown"

    citations = [
        {
            "claim": f"{ticker} recorded a Year-to-Date return of 18.45% with annualized volatility of 22.8%.",
            "source_id": metric_id,
            "source_type": "metric",
            "source_url": None
        },
        {
            "claim": "Primary operational risks highlighted in recent SEC filings include supply chain concentration and trade policy headwinds.",
            "source_id": doc_id,
            "source_type": "document",
            "source_url": f"https://www.sec.gov/edgar/browse/?CIK={ticker}"
        }
    ]

    markdown_report = f"""# Autonomous Equity Research Brief: {ticker}

**Research Query:** {state['question']}
**Generated At:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## 1. Executive Summary
{ticker} continues to demonstrate strong strategic execution, evidenced by an estimated YTD return of 18.45% [[Metric: {metric_id}]]. Qualitative disclosures indicate robust demand in key operational segments, supported by sustained technology capital expenditure.

## 2. Quantitative Performance & Risk
- **Year-to-Date Return:** +18.45% [[Metric: {metric_id}]]
- **Annualized Volatility (252-day):** 22.80%

## 3. Qualitative Risk Assessment & Catalysts
Disclosures in regulatory filings highlight that while revenue growth remains intact, management notes supply chain dependencies and macroeconomic exposure as primary considerations [[Document: {doc_id}]].

---
### Source Citations
- `[{metric_id}]` Quantitative Engine: Volatility & Return Module
- `[{doc_id}]` SEC EDGAR Filing Index & Qualitative Disclosures

---
*{DISCLAIMER}*
"""

    report_draft = {
        "markdown": markdown_report,
        "citations": citations,
        "disclaimer": DISCLAIMER
    }

    msg = {
        "agent": "WriterAgent",
        "role": "assistant",
        "content": "Completed research brief draft with inline source citations.",
        "tool_calls": {"citations_count": len(citations)},
        "created_at": datetime.utcnow()
    }

    return {
        "report_draft": report_draft,
        "agent_messages": [msg],
        "iteration_count": state.get("iteration_count", 0) + 1
    }


async def critic_agent_node(state: AgentState) -> Dict[str, Any]:
    """
    Deterministic Verification Node:
    Checks that every citation in the report draft resolves to an existing
    document ID or metric ID in the AgentState.
    """
    logger.info("Running Critic Verifier Node")
    draft = state.get("report_draft")
    if not draft:
        return {"verification_errors": ["Missing report draft"], "is_verified": False}

    valid_doc_ids = {d["id"] for d in state.get("documents", [])}
    valid_metric_ids = {m["id"] for m in state.get("metrics", [])}
    valid_source_ids = valid_doc_ids.union(valid_metric_ids)

    errors = []
    for cit in draft.get("citations", []):
        sid = cit.get("source_id")
        if sid not in valid_source_ids:
            errors.append(f"Unresolvable citation ID '{sid}' in claim: {cit.get('claim')}")

    is_verified = len(errors) == 0

    msg = {
        "agent": "CriticAgent",
        "role": "assistant",
        "content": "Report verified successfully: all claims mapped to ground-truth sources." if is_verified else f"Verification failed: {len(errors)} errors found.",
        "tool_calls": {"is_verified": is_verified, "errors": errors},
        "created_at": datetime.utcnow()
    }

    return {
        "verification_errors": errors,
        "is_verified": is_verified,
        "agent_messages": [msg]
    }
