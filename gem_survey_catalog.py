"""User-facing GEM research survey directory, excluding retired FDA PoA survey.

Only Phase 3 results and second post-readout financing are entry benchmarks.
All other surveys are advisory or GEM research-system quality controls.
The BPW *capability* audit may still mention BPW PoA as an external gap,
but that is never a GEM survey or a scored GEM entry gate.
"""
from __future__ import annotations

SURVEYS = (
    (1, "Phase 3 Results", "Entry benchmark 1", "clinical"),
    (2, "Second Financing Closure", "Entry benchmark 2", "financing"),
    (3, "Financial Health", "Ranking / risk", "runway"),
    (4, "Dilution Risk", "Risk", "dilution"),
    (5, "Hedge-Fund Ownership", "Ranking", "hedge"),
    (6, "Insider Trading", "Advisory ranking", "insider"),
    (7, "Stock Trading Activity", "Ranking", "market"),
    (8, "FDA / PDUFA Monitoring", "Catalyst monitoring", "fda"),
    (9, "Company Valuation", "Research (partial)", "market_cap"),
    (10, "Historical Price Performance", "Backtest (not validated)", "historical"),
    (11, "BiopharmaWatch Comparison", "Research quality control", None),
)
assert len(SURVEYS) == 11
assert [x[0] for x in SURVEYS] == list(range(1, 12))
assert "FDA Approval Probability" not in [x[1] for x in SURVEYS]


def survey_rows(comparison):
    """Display actual source coverage if the dated comparison has been verified."""
    valid = (
        isinstance(comparison, dict) and comparison.get("schema_version") == 1
        and isinstance(comparison.get("capability_matrix"), list)
        and comparison.get("same_input_score_comparison_performed") is False
    )
    data = {r.get("key"): r for r in comparison["capability_matrix"]
            if isinstance(r, dict)} if valid else {}
    result = []
    for number, title, role, key in SURVEYS:
        info = data.get(key, {})
        is_bpw = number == 11
        coverage = info.get("observed_gem_rows") if isinstance(info.get("observed_gem_rows"), int) else None
        total = info.get("total_gem_rows") if isinstance(info.get("total_gem_rows"), int) else None
        if is_bpw:
            status = "AVAILABLE — COVERAGE AUDIT" if valid else "PENDING — NO CURRENT AUDIT"
            coverage_text = "System-level quality control"
        else:
            status = info.get("state", "NOT VERIFIED")
            coverage_text = (
                f"{coverage:,} / {total:,} program rows"
                if coverage is not None and total is not None
                else "NOT VERIFIED"
            )
        result.append({
            "#": number,
            "GEM survey": title,
            "Role": role,
            "Source status": status,
            "Verified coverage": coverage_text,
        })
    return result
