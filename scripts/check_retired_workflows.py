#!/usr/bin/env python3
"""Default-branch retirement gate: no legacy scoring jobs can be reactivated."""
import re
import sys
from pathlib import Path

root=Path(__file__).resolve().parents[1]
flows=root/".github"/"workflows"
errors=[]
for p in sorted(flows.glob("*.yml"))+sorted(flows.glob("*.yaml")):
    body=p.read_text(encoding="utf-8")
    if re.search(r"raas",p.name,re.I):
        errors.append("Retired workflow has executable YAML: "+p.name)
    if re.search(r"(?:python|node|bash|sh|uv|npm|pnpm)[^\n]*?(?:raas[_-]|raas/)|uses:\\s*[^\n]*raas",body,re.I):
        errors.append("Workflow attempts retired scoring executable: "+p.name)
if not (root/"AGENTS.md").exists():
    errors.append("Permanent Codex agent retirement policy missing")
if not (root/".github/copilot-instructions.md").exists():
    errors.append("Permanent Copilot retirement policy missing")
if errors:
    for message in errors:
        print("FAIL:",message,file=sys.stderr)
    raise SystemExit(1)
print("PASS: legacy scoring workflows absent; no executable dependencies; agent policies installed")
