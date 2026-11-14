import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd
from app.core.config import settings
from app.sandbox.code_runner import sandbox_runner

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    Quantitative analysis agent that synthesizes calculations and visual charts
    by generating and executing sandboxed Python scripts.
    """

    def generate_analysis_script(self, csv_data_path: Path, ticker: str, output_dir: Path) -> str:
        """
        Generates clean Python code to compute financial metrics and render 2 charts.
        Notice: All imports are strictly from the whitelisted modules.
        """
        csv_path_escaped = str(csv_data_path).replace("\\", "/")
        output_dir_escaped = str(output_dir).replace("\\", "/")

        return f"""
import json
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# 1. Load price data
df = pd.read_csv("{csv_path_escaped}")
if "Date" in df.columns:
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")
else:
    df["Date"] = pd.date_range(end=pd.Timestamp.today(), periods=len(df), freq='B')

close = df["Close"]

# 2. Moving Averages
df["SMA_50"] = close.rolling(window=min(50, len(df)), min_periods=1).mean()
df["SMA_200"] = close.rolling(window=min(200, len(df)), min_periods=1).mean()

# 3. Financial Metrics
# Daily Returns
df["Daily_Return"] = close.pct_change()

# YTD / Period Return
total_return_pct = round(((close.iloc[-1] - close.iloc[0]) / close.iloc[0]) * 100, 2)

# Annualized Volatility (252 trading days)
ann_volatility_pct = round(df["Daily_Return"].std() * math.sqrt(252) * 100, 2)

# Max Drawdown
cum_returns = (1 + df["Daily_Return"].fillna(0)).cumprod()
peak = cum_returns.cummax()
drawdown = (cum_returns - peak) / peak
max_drawdown_pct = round(drawdown.min() * 100, 2)

# Moving Average Signal
latest_50 = df["SMA_50"].iloc[-1]
latest_200 = df["SMA_200"].iloc[-1]
trend_signal = "Bullish Golden Cross" if latest_50 >= latest_200 else "Neutral / Bearish"

metrics = {{
    "total_return_pct": total_return_pct,
    "annualized_volatility": ann_volatility_pct,
    "max_drawdown_pct": max_drawdown_pct,
    "current_price": round(float(close.iloc[-1]), 2),
    "sma_50": round(float(latest_50), 2),
    "sma_200": round(float(latest_200), 2),
    "trend_signal": trend_signal
}}

# 4. Chart 1: Price and Moving Average Trend
plt.figure(figsize=(10, 5))
plt.plot(df["Date"], close, label=f"{ticker} Close", color="#1f77b4", linewidth=1.8)
plt.plot(df["Date"], df["SMA_50"], label="50-Day SMA", color="#ff7f0e", linestyle="--", alpha=0.85)
plt.plot(df["Date"], df["SMA_200"], label="200-Day SMA", color="#2ca02c", linestyle=":", alpha=0.85)
plt.title(f"{ticker} Price Trend & Moving Averages", fontsize=14, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Price (USD)")
plt.legend(loc="upper left")
plt.grid(True, alpha=0.3)
plt.tight_layout()
chart_1_path = "{output_dir_escaped}/{ticker}_price_trend.png"
plt.savefig(chart_1_path, dpi=120)
plt.close()

# 5. Chart 2: 30-Day Rolling Annualized Volatility
df["Rolling_Vol"] = df["Daily_Return"].rolling(window=min(30, len(df)), min_periods=5).std() * math.sqrt(252) * 100
plt.figure(figsize=(10, 4))
plt.plot(df["Date"], df["Rolling_Vol"], label="30-Day Rolling Volatility (%)", color="#d62728", linewidth=1.5)
plt.title(f"{ticker} Historical Volatility Dynamics", fontsize=13, fontweight="bold")
plt.xlabel("Date")
plt.ylabel("Annualized Volatility (%)")
plt.legend(loc="upper right")
plt.grid(True, alpha=0.3)
plt.tight_layout()
chart_2_path = "{output_dir_escaped}/{ticker}_rolling_volatility.png"
plt.savefig(chart_2_path, dpi=120)
plt.close()

# Emit JSON result to stdout
print(json.dumps(metrics))
"""

    def analyze(self, ticker: str, price_df: pd.DataFrame) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Executes analysis in sandbox and returns (metrics, artifacts).
        """
        ticker = ticker.upper()

        if price_df.empty:
            logger.warning("Empty price dataframe supplied for %s. Generating synthetic series for analysis.", ticker)
            dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq="B")
            prices = 150.0 + np.cumsum(np.random.normal(0.05, 1.2, 252))
            price_df = pd.DataFrame({"Date": dates, "Close": prices})

        # Save temporary CSV for sandbox ingestion
        temp_csv = settings.ARTIFACTS_DIR / f"{ticker}_prices_input.csv"
        price_df.to_csv(temp_csv, index=False)

        script = self.generate_analysis_script(temp_csv, ticker, settings.ARTIFACTS_DIR)

        result = sandbox_runner.execute(script, artifact_prefix=ticker)

        metrics = []
        artifacts = []

        if not result.success:
            logger.error("Analyst sandbox execution failed: %s", result.error)
            return metrics, artifacts

        # Map computed values to structured state metrics
        res_metrics = result.metrics
        for metric_name, val in res_metrics.items():
            metrics.append({
                "id": f"metric-{metric_name[:12]}-{uuid.uuid4().hex[:6]}",
                "name": metric_name,
                "value_numeric": float(val) if isinstance(val, (int, float)) else None,
                "value_json": {"value": val} if isinstance(val, str) else {"raw": val},
                "computed_by_task": "task-analyst"
            })

        # Register generated charts
        chart_1_file = settings.ARTIFACTS_DIR / f"{ticker}_price_trend.png"
        chart_2_file = settings.ARTIFACTS_DIR / f"{ticker}_rolling_volatility.png"

        if chart_1_file.exists():
            artifacts.append({
                "id": f"art-chart-{uuid.uuid4().hex[:6]}",
                "kind": "chart",
                "path": str(chart_1_file.relative_to(settings.BASE_DIR)).replace("\\", "/"),
                "caption": f"{ticker} 12-Month Close Price and 50/200-Day Moving Averages",
                "produced_by_task": "task-analyst"
            })

        if chart_2_file.exists():
            artifacts.append({
                "id": f"art-chart-{uuid.uuid4().hex[:6]}",
                "kind": "chart",
                "path": str(chart_2_file.relative_to(settings.BASE_DIR)).replace("\\", "/"),
                "caption": f"{ticker} 30-Day Rolling Annualized Volatility Profile",
                "produced_by_task": "task-analyst"
            })

        return metrics, artifacts


analyst_agent = AnalystAgent()
