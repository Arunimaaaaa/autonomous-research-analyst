import logging
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Thin wrapper around Gemini LLM client with fallback handling."""

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.DEFAULT_LLM_MODEL
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not set. LLMClient will operate in mock mode.")
            return

        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._client = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=settings.GEMINI_API_KEY,
                temperature=0.2,
            )
            logger.info("Initialized ChatGoogleGenerativeAI with model: %s", self.model_name)
        except Exception as e:
            logger.error("Failed to initialize Gemini client: %s", str(e))
            self._client = None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def get_client(self) -> Any:
        return self._client


# Singleton instance
llm_client = LLMClient()
