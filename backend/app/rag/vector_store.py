import logging
from typing import Any, Dict, List, Optional
import numpy as np
from app.rag.chunker import Chunk, text_chunker
from app.rag.embeddings import embedding_client

logger = logging.getLogger(__name__)


class VectorStore:
    """
    In-memory vector store supporting chunk embedding and cosine similarity search.
    Preserves parent document UUIDs for citation provenance.
    """

    def __init__(self):
        self.chunks: List[Chunk] = []
        self._embeddings_matrix: Optional[np.ndarray] = None

    def clear(self):
        """Clears stored chunks and index."""
        self.chunks.clear()
        self._embeddings_matrix = None

    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        Chunks and embeds a batch of documents.
        Returns the total number of chunks indexed.
        """
        new_chunks = text_chunker.chunk_documents(documents)
        if not new_chunks:
            return 0

        # Compute embeddings for all new chunks
        embeddings_list = []
        for ch in new_chunks:
            emb = embedding_client.embed_text(ch.content)
            ch.embedding = emb
            embeddings_list.append(emb)

        self.chunks.extend(new_chunks)

        # Update numpy matrix for vectorized cosine similarity
        new_matrix = np.array(embeddings_list, dtype=np.float32)
        if self._embeddings_matrix is None:
            self._embeddings_matrix = new_matrix
        else:
            self._embeddings_matrix = np.vstack([self._embeddings_matrix, new_matrix])

        logger.info("Indexed %d chunks across %d documents in vector store.", len(new_chunks), len(documents))
        return len(new_chunks)

    def similarity_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Executes semantic cosine similarity search for a query string.
        Returns the top_k most relevant chunks with parent document IDs and scores.
        """
        if not self.chunks or self._embeddings_matrix is None:
            return []

        query_vec = np.array(embedding_client.embed_query(query), dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)
        if query_norm > 0:
            query_vec = query_vec / query_norm

        # Vectorized cosine similarity dot product
        similarities = np.dot(self._embeddings_matrix, query_vec)

        # Get indices of top_k highest scores
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            chunk = self.chunks[idx]
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content": chunk.content,
                "score": round(score, 4),
                "metadata": chunk.metadata,
                "source_type": chunk.metadata.get("source_type"),
                "source_url": chunk.metadata.get("source_url"),
                "title": chunk.metadata.get("title"),
            })

        return results


vector_store = VectorStore()
