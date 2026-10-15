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


def _numeric(value):
    """A saved numeric observation is not itself a verified entry signal."""
    if value is None or isinstance(value, bool):
        return False
    try:
        return str(value).strip() != "" and float(value) == float(value)
    except (ValueError, TypeError, OverflowError):
        return False


def _saved_source_observations(scans):
    """Conservative source evidence counts from the exact Pipeline-scoped GEM rows.

    These are per-program observations, not validated true/false outcomes,
    complete issuer coverage, or extra eligibility gates.
    """
    rows = [r for r in scans if isinstance(r, dict)]
    total = len(rows)
    counts = {
        "clinical": sum(r.get("Benchmark 1 — Phase 3 released") ==
                        "PASS — VERIFIED RESULTS RELEASE" for r in rows),
        "financing": sum(r.get("Benchmark 2 — Financing #2 closed") ==
                         "PASS — TWO POST-READOUT CLOSES" for r in rows),
        "runway": sum(_numeric(r.get("Cash runway (months)")) and
                      str(r.get("Cash runway gate") or "").startswith(("PASS", "HOLD"))
                      for r in rows),
        "dilution": sum(str(r.get("GEM 3 dilution status") or "").startswith(
                            ("NO NEW DILUTION FLAG", "ALERT", "WARNING"))
                        for r in rows),
        "hedge": sum(r.get("Hedge-fund signal") ==
                     "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS" for r in rows),
        "insider": sum(r.get("Insider Form 4 signal") ==
                       "SOURCE-VERIFIED SEC FORM 4 OBSERVATIONS" for r in rows),
        "market": sum(_numeric(r.get("Market activity /10")) and
                      float(r.get("Market activity /10")) >= 4 and
                      r.get("Rating status") != "NOT RATED — SNAPSHOT STALE"
                      for r in rows),
        "fda": sum(r.get("PDUFA verification") ==
                   "VERIFIED — SOURCE LINKED" for r in rows),
    }
    return {
        key: {"observed_gem_rows": count, "total_gem_rows": total}
        for key, count in counts.items()
    }


def survey_rows(comparison, *, scans=None, feed_current=None):
    """Display optional dated source-coverage observations, not new eligibility.

    A 13F row and a Form 4 row may cover the same program; never add their
    observation counts together or claim combined unique-program coverage.
    Optional saved-source scan rows replace diagnostic comparison observations
    in the primary directory; neither input implies complete live collection.
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
    if scans is not None:
        # Live directory coverage is sourced from the GEM scan's exact
        # Pipeline-origin program rows, NEVER the optional BPW diagnostic.
        data = _saved_source_observations(scans)
        valid = True
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
        if scans is not None:
            # Expose evidence freshness without claiming all sources verified.
            seen = ([data.get(k, {}) for k in key]
                    if isinstance(key, tuple) else [data.get(key, {})])
            observed = sum(int(x.get("observed_gem_rows") or 0) for x in seen)
            if not observed:
                state = "NOT VERIFIED / NO MATCHED OBSERVATIONS"
            elif feed_current is False:
                state = "STALE SOURCE FEED — SAVED OBSERVATIONS"
            else:
                state = "SAVED EVIDENCE — CHECK INDIVIDUAL SOURCE DATES"
        result.append({
            "#": number,
            "GEM survey": title,
            "Role": role,
            "Source status": state,
            "Verified coverage": coverage,
        })
    return result
