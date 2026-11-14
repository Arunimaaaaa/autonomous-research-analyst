import pytest
import pandas as pd
import numpy as np
from app.sandbox.code_runner import CodeExecutionSandbox
from app.agents.analyst_agent import AnalystAgent
from app.core.config import settings


def test_safe_code_execution():
    """Verifies that safe mathematical and pandas operations run cleanly in sandbox."""
    sandbox = CodeExecutionSandbox(timeout_seconds=5)
    code = """
import numpy as np
import pandas as pd
import json

data = [10, 20, 30, 40, 50]
s = pd.Series(data)
res = {
    "mean": float(s.mean()),
    "std": float(s.std())
}
print(json.dumps(res))
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert result.metrics["mean"] == 30.0
    assert "std" in result.metrics


def test_ast_forbidden_import_rejection():
    """Verifies that unwhitelisted imports are rejected before execution."""
    sandbox = CodeExecutionSandbox()

    dangerous_code_os = "import os\nos.system('dir')"
    result = sandbox.execute(dangerous_code_os)
    assert result.success is False
    assert "Disallowed import: 'os'" in result.error

    dangerous_code_sub = "import subprocess\nsubprocess.run(['dir'])"
    result_sub = sandbox.execute(dangerous_code_sub)
    assert result_sub.success is False
    assert "Disallowed import: 'subprocess'" in result_sub.error


def test_ast_forbidden_call_rejection():
    """Verifies that dangerous built-in calls like eval/exec are rejected."""
    sandbox = CodeExecutionSandbox()
    code = "x = eval('2 + 2')"
    result = sandbox.execute(code)
    assert result.success is False
    assert "Disallowed function call: 'eval()'" in result.error


def test_timeout_handling():
    """Verifies that infinite loops are killed by the timeout watchdog."""
    sandbox = CodeExecutionSandbox(timeout_seconds=2)
    infinite_loop_code = "while True:\n    pass"
    result = sandbox.execute(infinite_loop_code)
    assert result.success is False
    assert "timed out" in result.error


def test_analyst_agent_end_to_end():
    """Verifies that AnalystAgent generates at least 3 metrics and 2 charts."""
    dates = pd.date_range(end=pd.Timestamp.today(), periods=252, freq="B")
    prices = 100.0 + np.cumsum(np.random.normal(0.1, 1.0, 252))
    df = pd.DataFrame({"Date": dates, "Close": prices})

    agent = AnalystAgent()
    metrics, artifacts = agent.analyze("TEST_TICKER", df)

    # Acceptance criteria: >= 3 metrics, >= 2 charts
    assert len(metrics) >= 3, f"Expected >= 3 metrics, got {len(metrics)}"
    assert len(artifacts) >= 2, f"Expected >= 2 charts, got {len(artifacts)}"

    # Check that artifact files actually exist on disk
    for art in artifacts:
        full_path = settings.BASE_DIR / art["path"]
        assert full_path.exists(), f"Artifact file {full_path} was not created on disk"
