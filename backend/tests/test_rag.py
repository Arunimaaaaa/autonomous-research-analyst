import numpy as np
import pytest
from app.rag.chunker import TextChunker
from app.rag.embeddings import EmbeddingClient
from app.rag.vector_store import VectorStore
from app.agents.rag_agent import RAGAgent


def test_text_chunking():
    """Verifies that the text chunker splits text and preserves parent document IDs."""
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)
    sample_text = (
        "Item 1A. Risk Factors. The Company faces substantial supply chain constraints, "
        "geopolitical tariffs, and currency volatility in international markets. "
        "Furthermore, rapid advances in artificial intelligence require continuous capital investment."
    )
    doc_id = "doc-test-123"
    meta = {"source_type": "sec_filing_10k", "title": "Test 10-K"}

    chunks = chunker.chunk_text(sample_text, document_id=doc_id, metadata=meta)

    assert len(chunks) >= 2, "Text should be split into multiple chunks"
    for chunk in chunks:
        assert chunk.document_id == doc_id
        assert "char_start" in chunk.metadata
        assert chunk.metadata["source_type"] == "sec_filing_10k"


def test_embeddings_generation():
    """Verifies that the embedding generator produces 768-dim normalized vectors."""
    client = EmbeddingClient()
    text = "Apple reports record revenue driven by iPhone and cloud services."
    vec = client.embed_text(text)

    assert len(vec) == 768, "Embedding must be exactly 768 dimensions"
    norm = np.linalg.norm(np.array(vec))
    assert abs(norm - 1.0) < 1e-4, "Embedding vector must be L2-normalized"


def test_vector_store_similarity_search():
    """Verifies vector indexing and cosine similarity retrieval."""
    store = VectorStore()
    documents = [
        {
            "id": "doc-supply-chain",
            "source_type": "sec_filing_10k",
            "title": "Supply Chain Risks",
            "raw_text": "Manufacturing bottlenecks and single-source supplier concentration pose severe operational risks."
        },
        {
            "id": "doc-dividend-policy",
            "source_type": "sec_filing_10q",
            "title": "Capital Allocation",
            "raw_text": "The board authorized an expanded share repurchase program and quarterly cash dividend."
        }
    ]

    indexed_count = store.add_documents(documents)
    assert indexed_count >= 2

    # Query for supply chain risks
    query = "supplier bottlenecks and component shortages"
    matches = store.similarity_search(query, top_k=1)

    assert len(matches) == 1
    best_match = matches[0]
    assert best_match["document_id"] == "doc-supply-chain", "Should retrieve the supply chain document"
    assert best_match["score"] > 0


def test_rag_agent_retrieve_context():
    """Verifies that RAGAgent returns structured, evidence-backed qualitative citations."""
    agent = RAGAgent()
    docs = [
        {
            "id": "doc-apple-10k",
            "source_type": "sec_filing_10k",
            "source_url": "https://www.sec.gov/edgar/browse/?CIK=AAPL",
            "title": "AAPL 10-K Annual Report",
            "raw_text": "Our business is subject to risks associated with international trade disputes, customs tariffs, and export controls on semiconductor technologies."
        }
    ]

    result = agent.retrieve_qualitative_context("AAPL", docs)

    assert "risk_findings" in result
    assert "catalyst_findings" in result
    assert "cited_excerpts" in result
    assert len(result["cited_excerpts"]) >= 1

    # Verify that every citation ID maps to the ingested document UUID
    for excerpt in result["cited_excerpts"]:
        assert excerpt["source_id"] == "doc-apple-10k"
        assert excerpt["source_url"] == "https://www.sec.gov/edgar/browse/?CIK=AAPL"
