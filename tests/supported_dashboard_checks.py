"""Run retained dashboard contracts against the supported Next.js/FastAPI app.

Legacy Python UI tests use this bridge while their assertions live beside the
runtime they exercise. Each frontend file runs in its own Node process, exactly
once per pytest process; failures and empty discovery are never converted to a
skip. It does not fetch live evidence, dispatch scans or start a deployment.
"""
from functools import lru_cache
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "new-platform/frontend"
BACKEND = ROOT / "new-platform/backend"


@lru_cache(maxsize=None)
def run_frontend_contract(filename):
    """Execute one current frontend suite and require real test discovery."""
    path = FRONTEND / "tests" / filename
    assert path.parent == FRONTEND / "tests" and path.suffix == ".cjs", filename
    assert path.is_file(), f"Supported frontend contract is missing: {path}"
    result = subprocess.run(
        ["node", str(path)], cwd=FRONTEND, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
    )
    output = result.stdout
    assert result.returncode == 0, f"{filename} failed:\n{output}"
    totals = re.findall(r"(?:ℹ|#) tests (\d+)", output)
    failures = re.findall(r"(?:ℹ|#) fail (\d+)", output)
    assert totals and int(totals[-1]) > 0, f"{filename} discovered no tests:\n{output}"
    assert failures and int(failures[-1]) == 0, f"{filename} did not report success:\n{output}"
    return int(totals[-1])


@lru_cache(maxsize=None)
def run_backend_contract(*filenames):
    """Isolate backend imports from retired Streamlit modules in root tests."""
    assert filenames, "At least one backend contract is required"
    paths = [BACKEND / "tests" / name for name in filenames]
    assert all(path.parent == BACKEND / "tests" and path.is_file() for path in paths)
    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *map(str, paths)],
        cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, timeout=120,
    )
    assert result.returncode == 0, f"Supported backend contracts failed:\n{result.stdout}"
    totals = re.findall(r"\b(\d+) passed\b", result.stdout)
    assert totals and int(totals[-1]) > 0, f"Backend contracts discovered no passing tests:\n{result.stdout}"
    return int(totals[-1])
