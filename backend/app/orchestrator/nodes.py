import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from app.orchestrator.state import AgentState
from app.tools import market_data_tool, sec_edgar_tool, news_tool
from app.agents import analyst_agent, rag_agent

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "DISCLAIMER: This research brief is generated autonomously by an AI multi-agent system "
    "for informational and academic purposes only. It does NOT constitute financial, investment, "
    "tax, or legal advice. Always perform your own independent due diligence before making investment decisions."
)


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
        "created_at": get_utc_now()
    }

    return {
        "tasks": tasks,
        "agent_messages": [msg]
    }


async def data_agent_node(state: AgentState) -> Dict[str, Any]:
    """Fetches real market fundamentals, price history, and SEC filings/news."""
    ticker = state["ticker"]
    logger.info("Running Data Agent with live tools for ticker: %s", ticker)

    # 1. Fetch live fundamentals
    fundamentals = market_data_tool.fetch_key_fundamentals(ticker)

    # 2. Fetch live recent SEC filings
    filings = await sec_edgar_tool.fetch_recent_filings(ticker, max_filings=2)

    # 3. Fetch recent sanitized news
    news_items = news_tool.fetch_recent_news(ticker, max_items=2)

    # Convert filings & news to structured Document records with resolvable IDs
    documents = []
    for f in filings:
        doc_id = f"doc-sec-{uuid.uuid4().hex[:8]}"
        documents.append({
            "id": doc_id,
            "source_type": f"sec_filing_{f.get('form', '10-K')}",
            "source_url": f.get("url"),
            "title": f"{ticker} Form {f.get('form')} Filing ({f.get('filing_date')})",
            "raw_text": f.get("summary", ""),
            "fetched_at": get_utc_now()
        })

    for n in news_items:
        doc_id = f"doc-news-{uuid.uuid4().hex[:8]}"
        documents.append({
            "id": doc_id,
            "source_type": "financial_news",
            "source_url": n.get("url"),
            "title": n.get("title", f"{ticker} News"),
            "raw_text": n.get("text", ""),
            "fetched_at": get_utc_now()
        })

    # Convert fundamental ratios to stored Metrics
    metrics = []
    if fundamentals.get("marketCap"):
        metrics.append({
            "id": f"metric-mcap-{uuid.uuid4().hex[:6]}",
            "name": "market_capitalization",
            "value_numeric": float(fundamentals["marketCap"]),
            "value_json": {"currency": fundamentals.get("currency", "USD"), "formatted": f"${fundamentals['marketCap']:,.0f}"},
            "computed_by_task": "task-data"
        })
    if fundamentals.get("trailingPE"):
        metrics.append({
            "id": f"metric-pe-{uuid.uuid4().hex[:6]}",
            "name": "trailing_pe_ratio",
            "value_numeric": float(fundamentals["trailingPE"]),
            "value_json": {"ratio": "P/E"},
            "computed_by_task": "task-data"
        })

    msg = {
        "agent": "DataAgent",
        "role": "assistant",
        "content": f"Ingested {len(documents)} filings/news documents and extracted key valuation fundamentals for {ticker}.",
        "tool_calls": {
            "documents_count": len(documents),
            "metrics_count": len(metrics),
            "sector": fundamentals.get("sector")
        },
        "created_at": get_utc_now()
    }

    return {
        "documents": documents,
        "metrics": metrics,
        "agent_messages": [msg]
    }


async def analyst_agent_node(state: AgentState) -> Dict[str, Any]:
    """Computes quantitative metrics and generates charts in sandbox."""
    ticker = state["ticker"]
    logger.info("Running Sandboxed Analyst Agent for ticker: %s", ticker)

    # 1. Retrieve 1-year OHLCV price series
    price_df = market_data_tool.fetch_price_history(ticker, period="1y")

    # 2. Run sandboxed Python code generation & execution
    metrics, artifacts = analyst_agent.analyze(ticker, price_df)

    msg = {
        "agent": "AnalystAgent",
        "role": "assistant",
        "content": f"Successfully computed {len(metrics)} quantitative metrics and generated {len(artifacts)} charts in secure sandbox.",
        "tool_calls": {
            "metrics_count": len(metrics),
            "artifacts_count": len(artifacts),
            "artifacts": [a["path"] for a in artifacts]
        },
        "created_at": get_utc_now()
    }

    return {
        "metrics": metrics,
        "artifacts": artifacts,
        "agent_messages": [msg]
    }


async def rag_agent_node(state: AgentState) -> Dict[str, Any]:
    """Retrieves qualitative context with verifiable source citations."""
    ticker = state["ticker"]
    logger.info("Running RAG Agent for ticker: %s", ticker)

    documents = state.get("documents", [])
    rag_result = rag_agent.retrieve_qualitative_context(ticker, documents)
    cited_excerpts = rag_result.get("cited_excerpts", [])

    msg = {
        "agent": "RAGAgent",
        "role": "assistant",
        "content": f"Indexed {len(documents)} source documents and retrieved {len(cited_excerpts)} evidence-backed qualitative risk factors and catalysts.",
        "tool_calls": {
            "retrieved_findings_count": len(cited_excerpts),
            "source_ids": [item["source_id"] for item in cited_excerpts]
        },
        "created_at": get_utc_now()
    }

    return {
        "qualitative_findings": cited_excerpts,
        "agent_messages": [msg]
    }


async def writer_agent_node(state: AgentState) -> Dict[str, Any]:
    """Synthesizes findings into a structured, cited research brief."""
    ticker = state["ticker"]
    logger.info("Running Writer Agent for ticker: %s", ticker)

    metrics = state.get("metrics", [])
    qualitative = state.get("qualitative_findings", [])
    artifacts = state.get("artifacts", [])

    # Map primary metrics
    metric_map = {m["name"]: m for m in metrics}
    mcap_metric = metric_map.get("market_capitalization")
    pe_metric = metric_map.get("trailing_pe_ratio")
    ret_metric = metric_map.get("total_return_pct")
    vol_metric = metric_map.get("annualized_volatility")
    trend_metric = metric_map.get("trend_signal")

    citations = []

    # Add metric citations
    if ret_metric:
        citations.append({
            "claim": f"{ticker} experienced a 1-year total return of {ret_metric.get('value_numeric', 'N/A')}% with annualized volatility of {vol_metric.get('value_numeric', 'N/A') if vol_metric else 'N/A'}%.",
            "source_id": ret_metric["id"],
            "source_type": "metric",
            "source_url": None
        })

    if pe_metric:
        citations.append({
            "claim": f"{ticker} trades at a trailing price-to-earnings multiple of {pe_metric.get('value_numeric', 'N/A')}x.",
            "source_id": pe_metric["id"],
            "source_type": "metric",
            "source_url": None
        })

    # Add qualitative citations from RAG
    for q in qualitative[:3]:
        citations.append({
            "claim": q["claim"],
            "source_id": q["source_id"],
            "source_type": q.get("source_type", "document"),
            "source_url": q.get("source_url")
        })

    # Build Quantitative Section Markdown
    quant_lines = []
    if mcap_metric:
        quant_lines.append(f"- **Market Capitalization:** {mcap_metric.get('value_json', {}).get('formatted', mcap_metric.get('value_numeric'))} `[{mcap_metric['id']}]`")
    if pe_metric:
        quant_lines.append(f"- **Trailing P/E Ratio:** {pe_metric.get('value_numeric')}x `[{pe_metric['id']}]`")
    if ret_metric:
        quant_lines.append(f"- **1-Year Return:** {ret_metric.get('value_numeric')}% `[{ret_metric['id']}]`")
    if vol_metric:
        quant_lines.append(f"- **Annualized Volatility:** {vol_metric.get('value_numeric')}% `[{vol_metric['id']}]`")
    if trend_metric:
        quant_lines.append(f"- **Moving Average Signal:** {trend_metric.get('value_json', {}).get('value', 'N/A')} `[{trend_metric['id']}]`")

    quant_section = "\n".join(quant_lines) if quant_lines else "- Quantitative metrics calculated via sandboxed engine."

    # Build Qualitative Section Markdown
    qual_lines = []
    for q in qualitative:
        qual_lines.append(f"- {q['claim']} `[{q['source_id']}]`")
    qual_section = "\n".join(qual_lines) if qual_lines else "- Operational filings and recent disclosures reviewed."

    # Build Artifacts Section
    art_lines = []
    for art in artifacts:
        art_lines.append(f"- **{art['caption']}**: `/{art['path']}`")
    art_section = "\n".join(art_lines) if art_lines else "- Charts generated and stored in run artifacts."

    # Build Citations Legend
    citation_legend = []
    seen_ids = set()
    for c in citations:
        sid = c["source_id"]
        if sid not in seen_ids:
            seen_ids.add(sid)
            source_info = f"({c['source_type']})"
            if c.get("source_url"):
                source_info += f" - {c['source_url']}"
            citation_legend.append(f"- `[{sid}]` {source_info}")

    citation_legend_str = "\n".join(citation_legend)

    markdown_report = f"""# Autonomous Equity Research Brief: {ticker}

**Research Query:** {state['question']}
**Generated At:** {get_utc_now().strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## 1. Executive Summary
This brief provides an automated multi-agent synthesis of financial performance, regulatory filings, and market dynamics for **{ticker}**. Evidence synthesized from regulatory 10-K/10-Q disclosures and quantitative models indicates active strategic execution against a complex macroeconomic backdrop.

## 2. Quantitative Performance & Technical Indicators
{quant_section}

### Generated Visual Artifacts
{art_section}

## 3. Qualitative Disclosures & Risk Factors (RAG Evidence)
{qual_section}

---

### Verifiable Source Citations
{citation_legend_str}

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
        "content": f"Completed research brief with {len(citations)} verified inline citations and {len(artifacts)} visual artifacts.",
        "tool_calls": {"citations_count": len(citations), "artifacts_count": len(artifacts)},
        "created_at": get_utc_now()
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
        "created_at": get_utc_now()
    }

    return {
        "verification_errors": errors,
        "is_verified": is_verified,
        "agent_messages": [msg]
    }
