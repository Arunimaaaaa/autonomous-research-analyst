import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
import yfinance as yf
from app.core.config import settings

logger = logging.getLogger(__name__)

CACHE_DIR = settings.BASE_DIR / ".cache" / "market_data"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_HOURS = 2


class MarketDataTool:
    """
    Robust market data fetcher using yfinance with disk-based caching
    and defensive field parsing to prevent rate-limiting and missing-key crashes.
    """

    def __init__(self, cache_ttl_hours: int = CACHE_TTL_HOURS):
        self.cache_ttl = timedelta(hours=cache_ttl_hours)

    def _get_cache_path(self, ticker: str, data_type: str) -> Path:
        return CACHE_DIR / f"{ticker.upper()}_{data_type}.json"

    def _read_cache(self, ticker: str, data_type: str) -> Optional[Dict[str, Any]]:
        cache_file = self._get_cache_path(ticker, data_type)
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            cached_time = datetime.fromisoformat(cached.get("cached_at", "1970-01-01T00:00:00+00:00"))
            if datetime.now(timezone.utc) - cached_time < self.cache_ttl:
                logger.info("Using cached %s data for %s", data_type, ticker)
                return cached.get("data")
        except Exception as e:
            logger.warning("Failed to read cache for %s (%s): %s", ticker, data_type, str(e))
        return None

    def _write_cache(self, ticker: str, data_type: str, data: Any):
        cache_file = self._get_cache_path(ticker, data_type)
        try:
            payload = {
                "ticker": ticker.upper(),
                "cached_at": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, default=str)
        except Exception as e:
            logger.warning("Failed to write cache for %s (%s): %s", ticker, data_type, str(e))

    def fetch_price_history(self, ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
        """
        Fetches historical OHLCV price series.
        Returns a DataFrame indexed by date with Open, High, Low, Close, Volume.
        """
        cached_data = self._read_cache(ticker, f"prices_{period}_{interval}")
        if cached_data:
            df = pd.DataFrame(cached_data)
            if "Date" in df.columns:
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
            return df

        logger.info("Fetching price history from yfinance for %s (period=%s)", ticker, period)
        try:
            yf_ticker = yf.Ticker(ticker)
            df = yf_ticker.history(period=period, interval=interval)

            if df.empty:
                logger.warning("No price history returned for %s", ticker)
                return pd.DataFrame()

            # Clean and serialize to cache
            df_reset = df.reset_index()
            if "Date" in df_reset.columns:
                df_reset["Date"] = df_reset["Date"].dt.strftime("%Y-%m-%d")
            records = df_reset.to_dict(orient="records")
            self._write_cache(ticker, f"prices_{period}_{interval}", records)
            return df
        except Exception as e:
            logger.error("Error fetching price history for %s: %s", ticker, str(e))
            return pd.DataFrame()

    def fetch_key_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches key balance sheet, valuation, and performance fundamentals.
        Defensively defaults missing fields.
        """
        cached = self._read_cache(ticker, "fundamentals")
        if cached:
            return cached

        logger.info("Fetching key fundamentals from yfinance for %s", ticker)
        try:
            yf_ticker = yf.Ticker(ticker)
            info = yf_ticker.info or {}

            fundamentals = {
                "symbol": ticker.upper(),
                "shortName": info.get("shortName", ticker.upper()),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "marketCap": info.get("marketCap"),
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "priceToBook": info.get("priceToBook"),
                "debtToEquity": info.get("debtToEquity"),
                "returnOnEquity": info.get("returnOnEquity"),
                "revenueGrowth": info.get("revenueGrowth"),
                "grossMargins": info.get("grossMargins"),
                "operatingMargins": info.get("operatingMargins"),
                "fiftyTwoWeekHigh": info.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": info.get("fiftyTwoWeekLow"),
                "currency": info.get("currency", "USD"),
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }

            self._write_cache(ticker, "fundamentals", fundamentals)
            return fundamentals
        except Exception as e:
            logger.error("Error fetching fundamentals for %s: %s", ticker, str(e))
            return {
                "symbol": ticker.upper(),
                "error": str(e),
                "retrieved_at": datetime.now(timezone.utc).isoformat()
            }


market_data_tool = MarketDataTool()
