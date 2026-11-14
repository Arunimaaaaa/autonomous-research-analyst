import ast
import json
import logging
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Security: Strictly whitelisted top-level modules
ALLOWED_MODULES = {
    "pandas",
    "numpy",
    "matplotlib",
    "matplotlib.pyplot",
    "json",
    "math",
    "datetime",
    "typing",
}

# Forbidden AST call / name identifiers
FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "__import__",
    "breakpoint",
}


@dataclass
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    error: Optional[str] = None


class SecurityASTVisitor(ast.NodeVisitor):
    """AST validator that verifies Python code complies with the library whitelist."""

    def __init__(self):
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module not in ALLOWED_MODULES and alias.name not in ALLOWED_MODULES:
                self.violations.append(f"Disallowed import: '{alias.name}'")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module not in ALLOWED_MODULES and node.module not in ALLOWED_MODULES:
                self.violations.append(f"Disallowed import: '{node.module}'")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.violations.append(f"Disallowed function call: '{node.func.id}()'")
        self.generic_visit(node)


class CodeExecutionSandbox:
    """
    Subprocess-isolated code execution engine for financial calculations and plotting.
    Enforces AST security checks, strict timeouts, and output directory isolation.
    """

    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds

    def validate_code(self, code_str: str) -> List[str]:
        """Parses and checks code against security policies. Returns list of violations."""
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return [f"Syntax error: {str(e)}"]

        visitor = SecurityASTVisitor()
        visitor.visit(tree)
        return visitor.violations

    def execute(self, code_str: str, artifact_prefix: str = "run") -> ExecutionResult:
        """
        Executes verified Python code in an isolated subprocess.
        """
        violations = self.validate_code(code_str)
        if violations:
            msg = f"Security check failed: {'; '.join(violations)}"
            logger.warning(msg)
            return ExecutionResult(success=False, error=msg)

        # Create temporary working directory for this execution
        with tempfile.TemporaryDirectory(prefix="sandbox_run_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            script_path = tmp_path / "analysis_script.py"

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(code_str)

            # Subprocess execution using the current Python runtime
            python_executable = sys.executable

            try:
                proc = subprocess.run(
                    [python_executable, str(script_path)],
                    cwd=str(tmp_path),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env={
                        "PYTHONPATH": str(settings.BASE_DIR),
                        "ARTIFACTS_DIR": str(settings.ARTIFACTS_DIR),
                        "MPLBACKEND": "Agg",  # Headless matplotlib
                    }
                )

                if proc.returncode != 0:
                    return ExecutionResult(
                        success=False,
                        stdout=proc.stdout,
                        stderr=proc.stderr,
                        error=f"Process exited with code {proc.returncode}: {proc.stderr.strip()}"
                    )

                # Parse JSON output from stdout if available
                metrics_dict = {}
                stdout_lines = proc.stdout.strip().split("\n")
                for line in stdout_lines:
                    line_clean = line.strip()
                    if line_clean.startswith("{") and line_clean.endswith("}"):
                        try:
                            metrics_dict = json.loads(line_clean)
                            break
                        except Exception:
                            pass

                # Scan artifacts generated with prefix
                generated_artifacts = []
                for p in settings.ARTIFACTS_DIR.glob(f"{artifact_prefix}*.*"):
                    generated_artifacts.append(str(p.name))

                return ExecutionResult(
                    success=True,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    metrics=metrics_dict,
                    artifacts=generated_artifacts
                )

            except subprocess.TimeoutExpired:
                return ExecutionResult(
                    success=False,
                    error=f"Execution timed out after {self.timeout_seconds} seconds."
                )
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Subprocess execution error: {str(e)}"
                )


sandbox_runner = CodeExecutionSandbox()
