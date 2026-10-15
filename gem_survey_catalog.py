"""Seven active GEM survey categories plus optional research diagnostics.

The seven surveys observe existing PIPELINE-origin programs. Only the first
two are GEM qualification benchmarks. Historical trade calibration and BPW
feature comparisons are diagnostics, not additional nightly surveys.
"""
from __future__ import annotations

SURVEYS = (
    (1, "Phase 3 Results", "Entry benchmark 1", "clinical"),
    (2, "Second Financing Closure", "Entry benchmark 2", "financing"),
    (3, "Financial Health", "Ranking / risk", "runway"),
    (4, "Dilution Risk", "Risk", "dilution"),
    (5, "Ownership & Insider Activity", "Advisory / ranking", ("hedge", "insider")),
    (6, "Stock Trading Activity", "Ranking / entry-exit monitoring", "market"),
    (7, "FDA / PDUFA Monitoring", "Catalyst and exit monitoring", "fda"),
)
RESEARCH_DIAGNOSTICS = (
    "Historical Price Performance / Score Calibration",
    "BiopharmaWatch Feature-Coverage Comparison",
)
assert len(SURVEYS) == 7
assert [row[0] for row in SURVEYS] == list(range(1, 8))
assert [row[2] for row in SURVEYS[:2]] == [
    "Entry benchmark 1", "Entry benchmark 2",
]


def _coverage(info):
    observed = info.get("observed_gem_rows")
    total = info.get("total_gem_rows")
    if type(observed) is int and type(total) is int:
        return f"{observed:,} / {total:,} program rows"
    return "NOT VERIFIED"


def survey_rows(comparison):
    """Display optional dated source-coverage observations, not new eligibility.

    A 13F row and a Form 4 row may cover the same program; never add their
    observation counts together or claim combined unique-program coverage.
    Missing or stale comparison data never implies successful live collection.
    """
    valid = (
        isinstance(comparison, dict) and comparison.get("schema_version") == 1
        and isinstance(comparison.get("capability_matrix"), list)
        and comparison.get("same_input_score_comparison_performed") is False
    )
    data = {
        r.get("key"): r for r in comparison["capability_matrix"]
        if isinstance(r, dict) and r.get("key")
    } if valid else {}
    result = []
    for number, title, role, key in SURVEYS:
        if isinstance(key, tuple):
            hedge, insider = (data.get(k, {}) for k in key)
            state = (
                "13F: " + str(hedge.get("state", "NOT VERIFIED")) +
                " · Form 4: " + str(insider.get("state", "NOT VERIFIED"))
                if valid else "NOT VERIFIED"
            )
            coverage = (
                "13F: " + _coverage(hedge) +
                " · Form 4: " + _coverage(insider)
                if valid else "NOT VERIFIED"
            )
        else:
            info = data.get(key, {})
            state = info.get("state", "NOT VERIFIED")
            coverage = _coverage(info)
        result.append({
            "#": number,
            "GEM survey": title,
            "Role": role,
            "Source status": state,
            "Verified coverage": coverage,
        })
    return result
