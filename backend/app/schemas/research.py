from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    ticker: str = Field(..., description="Equity ticker symbol (e.g. AAPL, NVDA, TSLA)", example="AAPL")
    question: str = Field(..., description="Research question to analyze", example="How has Apple performed this year and what are the key risks?")


class TaskItem(BaseModel):
    id: str
    kind: str
    description: str
    status: str
    depends_on: List[str] = Field(default_factory=list)


class MetricItem(BaseModel):
    name: str
    value_numeric: Optional[float] = None
    value_json: Optional[Dict[str, Any]] = None
    computed_by_task: Optional[str] = None


class ArtifactItem(BaseModel):
    kind: str = Field(..., description="chart or table")
    path: str
    caption: str
    produced_by_task: Optional[str] = None


class CitationItem(BaseModel):
    claim: str
    source_id: str
    source_type: str  # document or metric
    source_url: Optional[str] = None


class AgentMessageItem(BaseModel):
    agent: str
    role: str
    content: str
    tool_calls: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ReportResponse(BaseModel):
    run_id: str
    markdown: str
    citations: List[CitationItem] = Field(default_factory=list)
    disclaimer: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResearchRunResponse(BaseModel):
    id: str
    ticker: str
    question: str
    status: str
    created_at: datetime
    finished_at: Optional[datetime] = None
    total_tokens: Optional[int] = 0
    total_cost: Optional[float] = 0.0
