# Autonomous Multi-Agent Research Analyst

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/Orchestrator-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An autonomous multi-agent system that takes a natural language equity research question (e.g., *"How has Apple performed this year and what are the key risks?"*) and autonomously produces an evidence-backed, cited research brief in minutes.

---

## Key Features

- **Multi-Agent Orchestration with LangGraph:** Stateful directed graph with typed `AgentState`, parallel branches, and a self-correction feedback loop.
- **Parallel Fan-out / Fan-in Architecture:**
  - **Planner:** Decomposes queries into structured subtasks.
  - **Data Agent:** Ingests price histories, fundamentals, and regulatory filings (SEC EDGAR).
  - **Analyst Agent:** Computes quantitative metrics and renders charts.
  - **RAG Agent:** Retrieves qualitative risk factors with source mappings.
  - **Writer & Critic Loop:** Synthesizes Markdown briefs and verifies every claim against stored ground-truth source IDs.
- **Strict Grounded Citations:** Every claim links directly to a database document UUID or metric ID.
- **Real-Time Step Streaming:** WebSocket endpoint for live timeline inspection.
- **Production & Local Flexibility:** Designed for PostgreSQL 16 + `pgvector` with zero-config SQLite local development fallback.

---

## System Architecture

```
                    ┌───────────────────────────────────────────────┐
  User ── question ─▶  FastAPI (REST + WebSocket Step Streaming)    │
                    └───────────────────────┬───────────────────────┘
                                            ▼
                    ┌───────────────────────────────────────────────┐
                    │            Orchestrator (LangGraph)           │
                    │       StateGraph, Shared AgentState Reducers  │
                    └───────────────────────┬───────────────────────┘
                                            │
                                            ▼
                                  ┌───────────────────┐
                                  │   Planner Node    │
                                  └─────────┬─────────┘
                                            │
                                            ▼
                                  ┌───────────────────┐
                                  │  Data Agent Node  │
                                  └─────────┬─────────┘
                                            │ (Fan-out)
                         ┌──────────────────┴──────────────────┐
                         ▼                                     ▼
             ┌───────────────────────┐             ┌───────────────────────┐
             │  Analyst Agent Node   │             │    RAG Agent Node     │
             │ (Metrics & Chart Gen) │             │ (Qualitative Sources) │
             └───────────┬───────────┘             └───────────┬───────────┘
                         └──────────────────┬──────────────────┘
                                            │ (Fan-in)
                                            ▼
                                  ┌───────────────────┐
                                  │ Writer Agent Node │
                                  └─────────┬─────────┘
                                            │
                                            ▼
                                  ┌───────────────────┐
                                  │ Critic / Verifier ├─[Unverified]─┐
                                  └─────────┬─────────┘              │
                                            │ (Verified)             ▼
                                            ▼                   (Self-heal)
                                   Final Report Output
```

---

## Directory Structure

```text
research-analyst/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST & WebSocket endpoints
│   │   ├── core/            # App settings & LLM client wrapper
│   │   ├── orchestrator/    # LangGraph state, nodes, and compiled graph
│   │   ├── db/              # SQLAlchemy 2.0 models & session manager
│   │   ├── schemas/         # Pydantic v2 data transfer models
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Test suite with mock verification
│   ├── docker-compose.yml   # PostgreSQL + pgvector container
│   ├── requirements.txt     # Python dependencies
│   └── .env.example         # Environment template
└── README.md
```

---

## Quickstart

### 1. Environment Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY
```

### 3. Run Test Suite
```bash
pytest tests/ -v
```

### 4. Start Backend Server
```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive Swagger API docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
