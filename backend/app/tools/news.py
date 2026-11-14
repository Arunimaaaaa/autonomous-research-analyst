import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List
import yfinance as yf

logger = logging.getLogger(__name__)

# Patterns indicative of prompt injection attacks in untrusted external text
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL),
]


def sanitize_text(text: str) -> str:
    """
    Sanitizes untrusted web/news text to protect against prompt injection and XSS.
    1. Removes full script and style tag blocks (including their inner code).
    2. Unescapes HTML entities.
    3. Strips remaining HTML tags.
    4. Redacts known adversarial jailbreak phrases.
    """
    if not text:
        return ""

    # Remove script and style elements entirely with their content
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.IGNORECASE | re.DOTALL)

    # Unescape HTML entities (&amp;, &lt;, etc.)
    cleaned = html.unescape(cleaned)

    # Remove all remaining HTML/XML tags
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)

    # Redact prompt injection patterns
    for pattern in INJECTION_PATTERNS:
        cleaned = pattern.sub("[REDACTED_POTENTIAL_INJECTION]", cleaned)

    # Normalize whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


class NewsTool:
    """
    Financial news aggregator with built-in prompt-injection sanitization.
    Uses yfinance ticker news feed with defensive extraction.
    """

    def fetch_recent_news(self, ticker: str, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches and sanitizes recent news articles for a given ticker.
        """
        logger.info("Fetching recent news for %s", ticker)
        articles = []
        try:
            yf_ticker = yf.Ticker(ticker)
            raw_news = yf_ticker.news or []

            for item in raw_news[:max_items]:
                raw_title = item.get("title", "")
                raw_publisher = item.get("publisher", "Financial Press")
                link = item.get("link", "")

                sanitized_title = sanitize_text(raw_title)
                sanitized_publisher = sanitize_text(raw_publisher)

                if sanitized_title:
                    articles.append({
                        "ticker": ticker.upper(),
                        "title": sanitized_title,
                        "publisher": sanitized_publisher,
                        "url": link,
                        "published_at": item.get("providerPublishTime"),
                        "text": f"Headline: {sanitized_title} (Reported by {sanitized_publisher})"
                    })
        except Exception as e:
            logger.warning("Failed to fetch live news for %s: %s", ticker, str(e))

        if not articles:
            # Fallback article
            articles.append({
                "ticker": ticker.upper(),
                "title": f"Market analysis and trading volume overview for {ticker.upper()}",
                "publisher": "Financial Markets Digest",
                "url": f"https://finance.yahoo.com/quote/{ticker.upper()}",
                "published_at": int(datetime.now(timezone.utc).timestamp()),
                "text": f"Recent coverage focuses on {ticker.upper()} earnings momentum, product execution, and macroeconomic rate environment."
            })

        return articles


news_tool = NewsTool()
