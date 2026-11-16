"""Read-only guard for the two existing L04–L06 naming systems.

Do not merge these contracts: the runtime audit and scientific readiness
inventories have distinct semantics. This script is diagnostic only.
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "new-platform/backend/app/assessment_runtime.py"
READINESS = ROOT / "new-platform/backend/app/scientific_levels_two_to_six.py"


def literal_assignment(path: Path, variable: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == variable for target in node.targets):
                return ast.literal_eval(node.value)
    raise ValueError(f"{variable} missing from {path}")


def contract_report():
    runtime = literal_assignment(RUNTIME, "NAMES")
    readiness = literal_assignment(READINESS, "LEVELS")
    if any(level not in runtime or level not in readiness for level in (4, 5, 6)):
        raise ValueError("Missing L04–L06 definition")
    return {
        level: {
            "runtime_audit": runtime[level],
            "scientific_readiness": readiness[level][0],
            "same_name": runtime[level] == readiness[level][0],
        }
        for level in (4, 5, 6)
    }


if __name__ == "__main__":
    import json
    print(json.dumps(contract_report(), indent=2))
