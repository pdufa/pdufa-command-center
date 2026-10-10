"""Phase 3 PRE-READOUT clinical assessment, never post-topline prediction leakage.

As of a cutoff date, registry phase/status plus no posted registry result only
establish a screening queue; corporate topline releases must be separately
checked. Domain assessments are analyst-entered, source-dated, and cannot be
promoted to a Phase 3 success probability without independent calibration.
"""
from __future__ import annotations

from datetime import date
import re

import pandas as pd

WEIGHTS = {
    "phase2_efficacy": 25,
    "phase3_design": 30,
    "safety": 15,
    "regulatory_alignment": 15,
    "execution": 10,
    "evidence_quality": 5,
}
ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
EVIDENCE_COLUMNS = [
    "nct_id", "ticker", "drug", "indication", "assessment_cutoff_date",
    "issuer_readout_status", "issuer_readout_checked_at", "issuer_readout_source",
    "actual_topline_release_date",
] + [
    field for name in WEIGHTS for field in
    (f"{name}_points", f"{name}_source", f"{name}_source_date")
]
RESULT_COLUMNS = [
    "Ticker", "Company", "Drug", "Indication", "NCT ID", "Trial Status",
    "Primary Completion", "Primary Completion Type", "Market Cap", "Source",
    "Phase 2 NCT Links", "Program Identity", "Assessment Status",
    "Pre-Readout Evidence Points", "Phase 3 Success Probability %",
    "Missing Evidence",
]


def _cols(frame, *names):
    for name in names:
        if name in frame.columns:
            return frame[name].fillna("").astype(str).str.strip()
    return pd.Series("", index=frame.index, dtype=str)


def _dates(values):
    return pd.to_datetime(values.astype(str).str.slice(0, 10), errors="coerce")


def _iso_day(value):
    try:
        parsed = date.fromisoformat(str(value or "").strip()[:10])
        return parsed
    except (ValueError, TypeError):
        return None


def candidate_queue(pipeline, announcements, cap_cache, as_of, protocols=None, *, require_protocol=False):
    """Return *potential* pre-readout Phase 3 trials in $300M–$10B universe.

    Not a certification that topline results have not been announced elsewhere.
    Do not use historical snapshots built from today's mutable registry data.
    """
    if pipeline is None or pipeline.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    as_of = _iso_day(as_of)
    if as_of is None:
        raise ValueError("as_of must be a valid YYYY-MM-DD cutoff")
    # If the caller supplies a protocol ledger, its absence is not evidence
    # that clinical topline results remain unpublished.
    if protocols is not None and (protocols.empty or "nct_id" not in protocols):
        return pd.DataFrame(columns=RESULT_COLUMNS)
    x = pipeline.copy()
    necessary = ["nct_id", "ticker", "phases", "trial_status"]
    if any(col not in x.columns for col in necessary):
        return pd.DataFrame(columns=RESULT_COLUMNS)
    for col in x.columns:
        if x[col].dtype == "object":
            x[col] = x[col].fillna("")
    phase = _cols(x, "phases").str.upper().eq("PHASE3")
    active = _cols(x, "trial_status").str.upper().isin(ACTIVE)
    nct = _cols(x, "nct_id").str.upper()
    valid = nct.str.fullmatch(r"NCT\d{8}").fillna(False)
    ticker = _cols(x, "ticker").str.upper()
    not_posted = _cols(x, "results_first_posted").eq("")
    # A current mutable registry record is never a valid historical snapshot
    # for a cutoff preceding its actual retrieval OR posted protocol revision.
    # Prevent "pre-readout" backtests from seeing later registry design fields.
    checked = _dates(_cols(x, "checked_at"))
    updated = _dates(_cols(x, "source_updated"))
    cutoff_safe = checked.dt.date.le(as_of).fillna(False)
    cutoff_safe &= (updated.isna() | updated.dt.date.le(as_of))
    if announcements is not None and not announcements.empty:
        published = _dates(_cols(announcements, "phase3_results_posted_at"))
        past_or_present = published.dt.date.le(as_of).fillna(False)
        prior_ncts = set(_cols(announcements.loc[past_or_present], "nct_id").str.upper())
        # If issuer announcements have no exact NCT ID, do NOT assume a ticker
        # match establishes a particular trial's outcome.
        not_posted &= ~nct.isin(prior_ncts - {""})
    # Production screening fails closed when a contemporaneous exact-NCT
    # protocol is missing: the broad Phase 3 ledger may be stale about
    # discontinued studies and already posted registry results.
    if require_protocol and (
        protocols is None or protocols.empty or "nct_id" not in protocols
    ):
        return pd.DataFrame(columns=RESULT_COLUMNS)
    # A fresh protocol fetch can detect posted results or a stopped study
    # before the slower local pipeline registry ledger is refreshed. Never
    # score it as pre-readout simply because that ledger is stale.
    if protocols is not None and not protocols.empty and "nct_id" in protocols:
        p = protocols.copy()
        protocol_nct = _cols(p, "nct_id").str.upper()
        source = _cols(p, "source_url")
        checked_proto = _dates(_cols(p, "checked_at"))
        valid_proto = (
            protocol_nct.str.fullmatch(r"NCT\d{8}").fillna(False)
            & source.eq("https://clinicaltrials.gov/study/" + protocol_nct)
            & checked_proto.dt.date.le(as_of).fillna(False)
        )
        # Fail closed on refreshed registry records with missing/unknown trial
        # status or existing published results. An unresolved NCT is not safe
        # to advertise as a pre-readout opportunity.
        published_proto = _cols(p, "registry_results_first_posted").ne("")
        not_active_proto = ~_cols(p, "registry_overall_status").str.upper().isin(ACTIVE)
        blocked = set(protocol_nct.loc[valid_proto & (published_proto | not_active_proto)])
        # Only accept an exact-NCT protocol fetched and last revised by cutoff.
        # A stale Phase 3 ledger alone is insufficient to rule out a readout.
        protocol_revision = _dates(_cols(p, "source_updated")).dt.date
        # Do not call a trial presently unreleased based on a stale protocol:
        # its registry results or status might have changed since that fetch.
        checked_day = checked_proto.dt.date
        recent_proto = checked_day.ge(as_of - pd.Timedelta(days=2)).fillna(False)
        latest_active = set(protocol_nct.loc[
            valid_proto & ~published_proto & ~not_active_proto
            & protocol_revision.le(as_of).fillna(False) & recent_proto
        ])
        not_posted &= ~nct.isin(blocked) & nct.isin(latest_active)
    if cap_cache is None or cap_cache.empty or "ticker" not in cap_cache:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    c = cap_cache.copy().drop_duplicates("ticker", keep="last")
    caps = pd.to_numeric(_cols(c, "market_cap"), errors="coerce")
    verified = _cols(c, "market_cap_status").str.upper().eq("VERIFIED")
    # Market caps must have been verified no later than the cutoff date.
    cap_dates = _dates(_cols(c, "market_cap_checked_at"))
    valid_date = cap_dates.dt.date.le(as_of).fillna(False)
    valid_caps = c.loc[verified & valid_date & caps.between(300e6, 10e9)]
    allowed = set(_cols(valid_caps, "ticker").str.upper())
    chosen = x.loc[phase & active & valid & cutoff_safe & not_posted & ticker.isin(allowed)].copy()
    if chosen.empty:
        return pd.DataFrame(columns=RESULT_COLUMNS)
    chosen = chosen.drop_duplicates("nct_id", keep="last")
    cap_map = pd.Series(
        pd.to_numeric(_cols(valid_caps, "market_cap"), errors="coerce").to_numpy(),
        index=_cols(valid_caps, "ticker").str.upper().to_numpy(),
    ).to_dict()
    queue = pd.DataFrame({
        "Ticker": _cols(chosen, "ticker").str.upper(),
        "Company": _cols(chosen, "company"),
        "Drug": _cols(chosen, "drug"),
        "Indication": _cols(chosen, "indication"),
        "NCT ID": _cols(chosen, "nct_id"),
        "Trial Status": _cols(chosen, "trial_status"),
        "Primary Completion": _cols(chosen, "primary_completion"),
        "Primary Completion Type": _cols(chosen, "primary_completion_type"),
        "Market Cap": _cols(chosen, "ticker").str.upper().map(cap_map),
        "Source": _cols(chosen, "source_url"),
        "Phase 2 NCT Links": _cols(chosen, "phase2_nct_ids"),
        "Program Identity": _cols(chosen, "program_identity_status"),
        "Assessment Status": "NOT SCORED — BEFORE-READOUT EVIDENCE INCOMPLETE",
        "Pre-Readout Evidence Points": pd.Series(pd.NA, index=chosen.index, dtype="Float64"),
        "Phase 3 Success Probability %": pd.Series(pd.NA, index=chosen.index, dtype="Float64"),
        "Missing Evidence": "Phase 2 efficacy; Phase 3 design; safety; FDA alignment; execution; evidence quality; issuer readout check",
    }, index=chosen.index)
    return queue.sort_values(["Ticker", "NCT ID"], kind="stable").reset_index(drop=True)


def assess(queue, evidence, as_of):
    """Add strictly pre-result 100-point *research* assessments, not PoS.

    Every score component must have a source URL and its original publication
    date no later than the cutoff. An explicit issuer readout check is required.
    Evidence entered after the fact is not automatically eligible for a
    historical/backtest prediction.
    """
    out = queue.copy()
    if out.empty or evidence is None or evidence.empty:
        return out
    cutoff = _iso_day(as_of)
    if cutoff is None:
        raise ValueError("Invalid cutoff date")
    if "nct_id" not in evidence:
        return out
    lookup = evidence.copy().drop_duplicates("nct_id", keep="last").set_index("nct_id")
    for i, row in out.iterrows():
        nct = str(row["NCT ID"])
        if nct not in lookup.index:
            continue
        e = lookup.loc[nct]
        missing = []
        # Never attach evidence for a different ticker, intervention or
        # indication simply because an NCT identifier matches.
        for src, dst in (("ticker", "Ticker"), ("drug", "Drug"), ("indication", "Indication")):
            if str(e.get(src, "")).strip() != str(row.get(dst, "")).strip():
                missing.append("matching trial " + src)
        if str(row.get("Program Identity", "")).strip().upper() != "VERIFIED":
            missing.append("verified investigational drug and program identity")
        if not str(row.get("Source", "")).strip().startswith(("http://", "https://")):
            missing.append("registry trial source")
        declared_cutoff = _iso_day(e.get("assessment_cutoff_date"))
        if declared_cutoff is None or declared_cutoff != cutoff:
            missing.append("exact assessment cutoff date")
        if str(e.get("issuer_readout_status", "")).strip().upper() != "VERIFIED_UNRELEASED":
            missing.append("independent issuer topline-release verification")
        checked = _iso_day(e.get("issuer_readout_checked_at"))
        if checked is None or checked != cutoff:
            missing.append("issuer check performed on the assessment cutoff date")
        issuer = str(e.get("issuer_readout_source", "")).strip()
        if not issuer.startswith(("https://", "http://")):
            missing.append("issuer release-status source")
        released = _iso_day(e.get("actual_topline_release_date"))
        if released is not None and released <= cutoff:
            missing.append("Phase 3 already publicly released")
        total = 0.0
        for name, maximum in WEIGHTS.items():
            try:
                value = float(str(e.get(f"{name}_points", "")).strip())
            except (ValueError, TypeError):
                value = float("nan")
            if not 0 <= value <= maximum:
                missing.append(f"{name} assessed points (0–{maximum})")
                continue
            source = str(e.get(f"{name}_source", "")).strip()
            published = _iso_day(e.get(f"{name}_source_date"))
            if not source.startswith(("https://", "http://")) or published is None or published > cutoff:
                missing.append(f"{name} source published on/before cutoff")
                continue
            total += value
        if missing:
            out.at[i, "Missing Evidence"] = "; ".join(missing)
            continue
        out.at[i, "Pre-Readout Evidence Points"] = total
        out.at[i, "Assessment Status"] = "100-POINT RESEARCH SCORE — UNCALIBRATED"
        out.at[i, "Missing Evidence"] = "None for documented rubric; independent historical calibration still missing"
        # Deliberately do NOT calculate any probability from points.
    return out


def evidence_template(queue):
    """Blank, explicitly analyst-verified evidence template for eligible trials."""
    if queue is None or queue.empty:
        return pd.DataFrame(columns=EVIDENCE_COLUMNS)
    rows = []
    for _, record in queue.iterrows():
        item = {col: "" for col in EVIDENCE_COLUMNS}
        item.update({
            "nct_id": record.get("NCT ID", ""),
            "ticker": record.get("Ticker", ""),
            "drug": record.get("Drug", ""),
            "indication": record.get("Indication", ""),
        })
        rows.append(item)
    return pd.DataFrame(rows, columns=EVIDENCE_COLUMNS)
