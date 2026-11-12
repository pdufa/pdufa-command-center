"""Read-only local Ollama controller smoke test for Windows PDUFA.

This test NEVER writes to the repository, executes generated code, or pushes changes.
"""
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
POLICY = ROOT / "AGENTS.md"
URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:1.5b"


def main():
    if not POLICY.is_file():
        print("STOP: AGENTS.md is missing; refusing to proceed.")
        return 2
    prompt = (
        "You are assisting a protected PDUFA scientific assessment repository. "
        "No file edits, shell commands, deployment, or live prediction changes are authorized. "
        "Respond with exactly three brief safety checks for a proposed code change. "
        "Do not claim you performed the checks.\n"
        + POLICY.read_text(encoding="utf-8", errors="replace")[:8000]
    )
    payload = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                          "options": {"num_predict": 160, "temperature": 0}}).encode()
    request = urllib.request.Request(URL, data=payload,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.load(response)
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"Local Ollama test failed: {exc}")
        return 1
    print("LOCAL MODEL RESPONSE (untrusted; not executed):")
    print(result.get("response", "").strip())
    print("\nPASS: Local inference responded. No project files changed by this script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
