# Autonomous Multi-Agent Research Analyst

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/Orchestrator-LangGraph-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![React + Vite](https://img.shields.io/badge/Frontend-React_18_%2B_Vite-61dafb.svg?logo=react)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind-3.4+-38bdf8.svg?logo=tailwind-css)](https://tailwindcss.com/)
[![Tests Passing](https://img.shields.io/badge/pytest-14%2F14_passing-brightgreen.svg)](https://docs.pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An end-to-end, enterprise-grade autonomous multi-agent equity research analyst. Given a ticker and question (e.g., *"How has Apple performed over the past year and what are the key risks disclosed in 10-K filings?"*), the system plans, fetches live regulatory and market data, executes sandboxed Python code to calculate metrics and render visual charts, retrieves qualitative evidence via RAG, and synthesizes a cited research brief with deterministic verification.

---

## Architecture

```
                    ┌────────────────────────────────────────────────────────┐
  User ── question ─▶   FastAPI (REST Endpoints + WebSocket Streaming)       │
                    └───────────────────────────┬────────────────────────────┘
                                                ▼
                    ┌────────────────────────────────────────────────────────┐
                    │                Orchestrator (LangGraph)                │
                    │         Typed AgentState with Operator Reducers        │
                    └───────────────────────────┬────────────────────────────┘
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
                                                │ (Parallel Fan-out)
                             ┌──────────────────┴──────────────────┐
                             ▼                                     ▼
                 ┌───────────────────────┐             ┌───────────────────────┐
                 │  Analyst Agent Node   │             │    RAG Agent Node     │
                 │  (Sandboxed Python)   │             │ (Vector Cosine Search)│
                 │  - 50/200 DMA Signals │             │ - SEC 10-K/10-Q Chunks│
                 │  - Volatility & Return│             │ - Prompt Sanitization │
                 │  - Generates 2 Charts │             │ - Source Attribution  │
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
                                      │ Critic / Verifier ├─[Unresolvable Citation]─┐
                                      └─────────┬─────────┘                         │
                                                │ (All Claims Grounded)             ▼
                                                ▼                               (Self-Correction)
                                     Final Persisted Brief
```

---

## Production Features

1. **Stateful Graph Orchestration (LangGraph)**:
   - Uses `Annotated[List, operator.add]` state reducers so parallel worker nodes (Analyst Agent & RAG Agent) execute concurrently without race conditions.
2. **Deterministic Source Attribution**:
   - 100% of claims cite ground-truth document UUIDs or metric IDs.
   - The Critic node audits every citation against stored entities before releasing the brief.
3. **Subprocess Code Execution Sandbox**:
   - Uses Abstract Syntax Tree (AST) static analysis to enforce strict library whitelisting (`pandas`, `numpy`, `matplotlib`).
   - Rejects unwhitelisted imports (`os`, `sys`, `subprocess`, `shutil`, `socket`) and unsafe built-ins (`eval`, `exec`).
   - Enforces a 30-second hard execution timeout to eliminate infinite loops.
4. **Live Data & Compliance Integrations**:
   - **SEC EDGAR API:** Complies with SEC User-Agent header standards to pull Form 10-K/10-Q filings with direct links to the SEC archive.
   - **yfinance:** Resilient 2-hour disk caching in `.cache/market_data/` to eliminate rate limiting.
   - **News Sanitizer:** Defends against prompt injection attacks by stripping script blocks, unescaping HTML, and redacting jailbreak prompts.
5. **Interactive React 18 + Vite UI**:
   - Real-time WebSocket step streaming.
   - Preset selector for quick analysis.
   - Visual chart gallery rendering generated artifacts.
   - Interactive citation pill inspector.
   - Chronological agent execution trace drawer.

---

## Directory Layout

```text
research-analyst/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST & WebSocket endpoints
│   │   ├── core/            # Config, settings, and LLM wrapper
│   │   ├── orchestrator/    # LangGraph state, nodes, and compiled graph
│   │   ├── agents/          # AnalystAgent, RAGAgent
│   │   ├── tools/           # MarketDataTool, SecEdgarTool, NewsTool
│   │   ├── sandbox/         # CodeExecutionSandbox with AST checker
│   │   ├── rag/             # TextChunker, EmbeddingClient, VectorStore
│   │   ├── db/              # SQLAlchemy 2.0 models & async session
│   │   ├── schemas/         # Pydantic v2 schemas
│   │   └── main.py          # FastAPI application
│   ├── artifacts/           # Stored charts (PNG) and data tables (CSV)
│   ├── tests/               # 14/14 Pytest test suite
│   ├── docker-compose.yml   # PostgreSQL 16 + pgvector container
│   ├── pytest.ini           # Pytest async configuration
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Full dashboard SPA
│   │   ├── main.tsx         # React root
│   │   └── index.css        # Tailwind styling
│   ├── package.json         # Node dependencies
│   ├── vite.config.ts       # Reverse proxy configuration
│   └── tailwind.config.js   # Dark financial theme
└── README.md
```

---

## Quickstart

### 1. Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY (optional for local/mock mode)
```

### 3. Run the Automated Test Suite (14 Tests)
```bash
pytest -v
```

### 4. Start the Application

#### Option A: Run Full Stack via Backend (Single Port)
```bash
# Inside backend/
uvicorn app.main:app --reload --port 8000
```
Open **`http://localhost:8000`** in your browser.

#### Option B: Run Frontend with Hot-Reload (Vite Dev Server)
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev
```
Open **`http://localhost:3000`** in your browser.
