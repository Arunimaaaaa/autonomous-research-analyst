import logging
from typing import Any, Dict, List
from app.rag.vector_store import vector_store

logger = logging.getLogger(__name__)


class RAGAgent:
    """
    Qualitative retrieval agent that indexes raw filings & news,
    executes semantic similarity queries, and produces evidence-backed citations.
    """

    def retrieve_qualitative_context(self, ticker: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Indexes documents and extracts cited findings for risks and catalysts.
        """
        if not documents:
            logger.warning("No documents provided to RAG agent for ticker %s", ticker)
            return {
                "risk_findings": [],
                "catalyst_findings": [],
                "cited_excerpts": []
            }

        # 1. Clear previous index and index new documents
        vector_store.clear()
        vector_store.add_documents(documents)

        # 2. Query 1: Operational Risks & Headwinds
        risk_query = f"{ticker} operational risks supply chain concentration regulatory tariffs competition headwinds"
        risk_matches = vector_store.similarity_search(risk_query, top_k=2)

        # 3. Query 2: Strategic Catalysts & Growth Drivers
        catalyst_query = f"{ticker} revenue growth capital expenditure product innovation market share catalysts"
        catalyst_matches = vector_store.similarity_search(catalyst_query, top_k=2)

        # 4. Format findings with parent document UUIDs for verifiable citations
        risk_findings = []
        for match in risk_matches:
            risk_findings.append({
                "claim": f"Disclosures indicate operational sensitivity to {match['content'][:140]}...",
                "source_id": match["document_id"],
                "source_type": match.get("source_type", "sec_filing"),
                "source_url": match.get("source_url"),
                "score": match["score"],
                "excerpt": match["content"]
            })

        catalyst_findings = []
        for match in catalyst_matches:
            catalyst_findings.append({
                "claim": f"Strategic disclosures highlight ongoing investments: {match['content'][:140]}...",
                "source_id": match["document_id"],
                "source_type": match.get("source_type", "news"),
                "source_url": match.get("source_url"),
                "score": match["score"],
                "excerpt": match["content"]
            })

        all_cited_excerpts = risk_findings + catalyst_findings

        return {
            "risk_findings": risk_findings,
            "catalyst_findings": catalyst_findings,
            "cited_excerpts": all_cited_excerpts
        }


rag_agent = RAGAgent()
