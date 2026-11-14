import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Chunk:
    id: str
    document_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


class TextChunker:
    """
    Splits long financial reports and news text into overlapping semantic chunks
    while preserving document UUID references for source traceability.
    """

    def __init__(self, chunk_size: int = 400, chunk_overlap: int = 80):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, document_id: str, metadata: Optional[Dict[str, Any]] = None) -> List[Chunk]:
        """Splits a single text into overlapping Chunk objects."""
        if not text:
            return []

        metadata = metadata or {}
        chunks: List[Chunk] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size
            chunk_content = text[start:end].strip()

            if chunk_content:
                chunk_id = f"chunk-{uuid.uuid4().hex[:8]}"
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        document_id=document_id,
                        content=chunk_content,
                        metadata={
                            **metadata,
                            "char_start": start,
                            "char_end": min(end, text_len),
                        }
                    )
                )

            # Advance by step size (chunk_size - chunk_overlap)
            step = max(1, self.chunk_size - self.chunk_overlap)
            start += step

        return chunks

    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Chunk]:
        """Chunks a batch of raw document records from AgentState."""
        all_chunks: List[Chunk] = []
        for doc in documents:
            doc_id = doc.get("id", f"doc-{uuid.uuid4().hex[:8]}")
            raw_text = doc.get("raw_text", "")
            meta = {
                "source_type": doc.get("source_type", "unknown"),
                "source_url": doc.get("source_url"),
                "title": doc.get("title", "Untitled Document"),
            }
            chunks = self.chunk_text(raw_text, document_id=doc_id, metadata=meta)
            all_chunks.extend(chunks)
        return all_chunks


text_chunker = TextChunker()
