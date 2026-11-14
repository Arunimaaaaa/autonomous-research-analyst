import hashlib
import logging
import math
from typing import List, Optional
import numpy as np
from app.core.config import settings

logger = logging.getLogger(__name__)
VECTOR_DIMENSION = 768


class EmbeddingClient:
    """
    Embedding generator with Google Gemini text-embedding-004 integration
    and deterministic local mathematical fallback for offline testability.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.DEFAULT_EMBEDDING_MODEL
        self._has_gemini = bool(settings.GEMINI_API_KEY)

    def embed_text(self, text: str) -> List[float]:
        """Embeds a single string into a 768-dimensional normalized float vector."""
        if self._has_gemini:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                res = genai.embed_content(
                    model=self.model_name,
                    content=text,
                    task_type="retrieval_document"
                )
                embedding = res.get("embedding", [])
                if len(embedding) == VECTOR_DIMENSION:
                    return embedding
            except Exception as e:
                logger.warning("Gemini embedding API call failed: %s. Using local projection fallback.", str(e))

        return self._local_deterministic_embedding(text)

    def embed_query(self, query: str) -> List[float]:
        """Embeds a search query."""
        if self._has_gemini:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                res = genai.embed_content(
                    model=self.model_name,
                    content=query,
                    task_type="retrieval_query"
                )
                embedding = res.get("embedding", [])
                if len(embedding) == VECTOR_DIMENSION:
                    return embedding
            except Exception as e:
                logger.warning("Gemini query embedding failed: %s. Using local projection fallback.", str(e))

        return self._local_deterministic_embedding(query)

    def _local_deterministic_embedding(self, text: str) -> List[float]:
        """
        Generates a normalized 768-dimensional dense vector based on
        n-gram hashing and token frequency for offline development and CI.
        """
        vec = np.zeros(VECTOR_DIMENSION, dtype=np.float32)
        words = text.lower().split()

        if not words:
            return vec.tolist()

        for idx, word in enumerate(words):
            # Generate deterministic hash for the token
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            bucket_idx = h % VECTOR_DIMENSION
            weight = 1.0 / (math.log(idx + 2) + 1.0)
            vec[bucket_idx] += float(weight)

        # L2 Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm

        return vec.tolist()


embedding_client = EmbeddingClient()
