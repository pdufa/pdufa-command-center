"""Transparent pre-readout data-availability audit for Pipeline.

Counts verifiable field PRESENCE, not favorable clinical evidence. External
issuer and clinical publications are analyst-entered until independently
confirmed. No Phase 3 outcomes, p-values, FDA decisions or trading returns.
"""
from datetime import date
import re
import pandas as pd
from pre_readout_score import WEIGHTS


def _value(frame, column):
    if frame is None or frame.empty or column not in frame:
        return pd.Series(dtype="str")
    return frame[column].fillna("").astype(str).str.strip()


def _on_or_before(value, cutoff):
    try:
        d = date.fromisoformat(str(value or "")[:10])
        return d <= cutoff
    except ValueError:
        return False


def audit_inputs(queue, protocol, manual, cutoff):
    """Summarize Phase 3 PRE-RELEASE inputs without interpreting their outcomes.

    queue: prospective exact-NCT candidates constrained by current market cap
    protocol: design-only (no resultsSection) coverage scorecard
    manual: original dated evidence sources and issuer-readout checks
    """
    cutoff = cutoff if isinstance(cutoff, date) else date.fromisoformat(str(cutoff)[:10])
    frame = queue if queue is not None else pd.DataFrame()
    total = len(frame)
    ids = set(_value(frame, "NCT ID"))
    designs = (protocol if protocol is not None else pd.DataFrame()).copy()
    if "NCT ID" in designs:
        designs = designs[designs["NCT ID"].astype(str).isin(ids)].drop_duplicates("NCT ID")
    else:
        designs = pd.DataFrame()
    reviews = (manual if manual is not None else pd.DataFrame()).copy()
    if "nct_id" in reviews:
        reviews = reviews[reviews["nct_id"].astype(str).isin(ids)].drop_duplicates("nct_id", keep="last")
    else:
        reviews = pd.DataFrame()

    def count_for(frame, column, predicate=None):
        s = _value(frame, column)
        if predicate is not None:
            return int(predicate(s).sum())
        return int(s.ne("").sum())

    checks = {}
    checks["Verified investigational program identity"] = (
        count_for(frame, "Program Identity", lambda s: s.str.upper().eq("VERIFIED")),
        "Registry identity field; does not validate clinical efficacy",
    )
    checks["Earlier Phase 2 trial IDs linked"] = (
        count_for(frame, "Phase 2 NCT Links"),
        "Trial ID only; not a validated Phase 2 effect size or positive outcome",
    )
    checks["Prospective protocol design records"] = (
        count_for(designs, "Coverage", lambda s: s.eq("PROTOCOL PARTIAL")),
        "Design metadata; current revision, not necessarily a historical snapshot",
    )
    checks["Primary endpoint described"] = (
        count_for(designs, "Primary Endpoints"),
        "Field presence; endpoint quality and FDA acceptance not established",
    )
    checks["Allocation method described"] = (
        count_for(designs, "Allocation"),
        "Described does not mean randomized, adequately controlled or unbiased",
    )
    checks["Blinding/masking described"] = (
        count_for(designs, "Masking"),
        "NONE counts as described; quality must be assessed separately",
    )
    checks["Trial enrollment recorded"] = (
        count_for(designs, "Enrollment", lambda s: s.str.fullmatch(r"\d+").fillna(False)),
        "Sample size recorded; power assumptions not validated",
    )

    manual_index = {}
    for _, r in reviews.iterrows():
        nct = str(r.get("nct_id", "")).strip()
        if nct in ids and nct:
            manual_index[nct] = r
    issuer_checked = 0
    domain_counts = {k: 0 for k in WEIGHTS}
    for nct in ids:
        evidence = manual_index.get(nct)
        if evidence is None:
            continue
        reviewed_on = str(evidence.get("issuer_readout_checked_at", ""))[:10]
        issuer_valid = (
            str(evidence.get("assessment_cutoff_date", ""))[:10] == cutoff.isoformat()
            and reviewed_on == cutoff.isoformat()
            and str(evidence.get("issuer_readout_status", "")).upper() == "VERIFIED_UNRELEASED"
            and str(evidence.get("issuer_readout_source", "")).startswith(("https://", "http://"))
            and not _on_or_before(evidence.get("actual_topline_release_date", ""), cutoff)
        )
        if issuer_valid:
            issuer_checked += 1
        for name, max_points in WEIGHTS.items():
            try:
                amount = float(str(evidence.get(f"{name}_points", "")).strip())
            except (ValueError, TypeError):
                continue
            src = str(evidence.get(f"{name}_source", "")).strip()
            published = evidence.get(f"{name}_source_date", "")
            if (0 <= amount <= max_points and src.startswith(("https://", "http://"))
                    and _on_or_before(published, cutoff)):
                domain_counts[name] += 1
    checks["Issuer topline absence checked today (analyst entry)"] = (
        issuer_checked, "Status supplied by researcher, not independently monitored by scanner",
    )
    for domain, label in [
        ("phase2_efficacy", "Phase 2 efficacy analysis source-dated"),
        ("phase3_design", "Phase 3 design interpretation source-dated"),
        ("safety", "Clinical safety assessment source-dated"),
        ("regulatory_alignment", "FDA/regulatory alignment source-dated"),
        ("execution", "Trial execution assessment source-dated"),
        ("evidence_quality", "Evidence-quality assessment source-dated"),
    ]:
        checks[label] = (
            domain_counts[domain], "Analyst-entered points and URL/date; no automatic document validation",
        )
    checks["Complete 100-point research rubric"] = (
        count_for(frame, "Pre-Readout Evidence Points", lambda s: s.ne("")),
        "Research assessment only; not a success probability",
    )
    checks["Independently calibrated Phase 3 probability"] = (
        0, "NOT AVAILABLE — requires frozen historical outcomes and out-of-sample calibration",
    )
    return pd.DataFrame([
        {"Pre-readout input": label, "Present": min(present, total),
         "Missing": max(0, total - present), "Evidence meaning": note}
        for label, (present, note) in checks.items()
    ])
