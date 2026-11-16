"""Regression checks for the separate Level 4–6 assessment contracts.

This protects the existing 123 scientific contract while the 456 design is
reconciled. It does not assert clinical scoring or FDA prediction accuracy.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "new-platform/backend/app/assessment_runtime.py"
SCIENTIFIC = ROOT / "new-platform/backend/app/scientific_trial_assessment.py"
READINESS = ROOT / "new-platform/backend/app/scientific_levels_two_to_six.py"


def assignment(path, name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                return ast.literal_eval(node.value)
    raise AssertionError(f"Missing {name} in {path}")


def test_scientific_123_names_are_preserved():
    names = assignment(SCIENTIFIC, "NAMES")
    assert names == {1: "Trial verification", 2: "Clinical trial design", 3: "Efficacy and statistics"}


def test_runtime_456_names_are_preserved():
    names = assignment(RUNTIME, "NAMES")
    assert {k: names[k] for k in (4, 5, 6)} == {
        4: "Trial design and protocol investigation",
        5: "Statistical analysis and multiplicity",
        6: "Endpoint clinical relevance",
    }


def test_readiness_456_is_distinct_from_runtime():
    runtime = assignment(RUNTIME, "NAMES")
    readiness = assignment(READINESS, "LEVELS")
    assert {k: readiness[k][0] for k in (4, 5, 6)} == {
        4: "Safety and benefit-risk",
        5: "Indication-specific clinical assessment",
        6: "FDA regulatory readiness",
    }
    assert all(runtime[k] != readiness[k][0] for k in (4, 5, 6))
