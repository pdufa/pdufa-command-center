"""Leakage-safe Phase 3 pre-readout assessment.

This module computes a DATA EVIDENCE COVERAGE score, not a trial-success
probability. Clinical efficacy cannot be inferred from trial metadata alone.
Scores never read posted results, p-values, eventual decisions, or stock returns.
"""
import csv
import re
from datetime import date
from pathlib import Path
import pandas as pd

FIELDS = (
    "Ticker", "Company", "Drug / Program", "Indication", "NCT ID",
    "Trial Status", "Expected Primary Completion", "Market Cap",
    "Market Cap Gate", "Evidence Score / 100", "Coverage",
    "Phase 3 Success Probability", "Phase 2 Efficacy",
    "Phase 2 Safety", "FDA Alignment", "Primary Endpoints",
    "Allocation", "Masking", "Enrollment", "Evidence Gaps",
    "Readout Verification", "Protocol Source", "Protocol Checked",
)
ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}
EXCLUDED = {"TERMINATED", "WITHDRAWN", "SUSPENDED", "UNKNOWN"}
MIN_CAP = 300_000_000
MAX_CAP = 10_000_000_000


def clean(value):
    v = "" if value is None else str(value).strip()
    return "" if v.lower() in ("nan", "nat", "none", "<na>") else v


def rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def by_nct_protocol(records):
    return {clean(r.get("nct_id")): r for r in records
            if re.fullmatch(r"NCT\d{8}", clean(r.get("nct_id")))}


def _market_caps(records):
    return {clean(r.get("ticker")).upper(): r for r in records
            if clean(r.get("ticker"))}


def _announced_ids(announcements, as_of):
    """Suppress registry POSTED results, even when protocol ledger is stale."""
    flagged = set()
    for r in announcements:
        nct = clean(r.get("nct_id"))
        posted = clean(r.get("phase3_results_posted_at"))[:10]
        if re.fullmatch(r"NCT\d{8}", nct) and posted and posted <= as_of.isoformat():
            flagged.add(nct)
    return flagged


def score_row(trial, protocol=None, cap=None, *, as_of):
    """Return one prospective-only, uncalibrated assessment or None if ineligible."""
    nct = clean(trial.get("nct_id"))
    phase = clean(trial.get("phase")).upper()
    if not re.fullmatch(r"NCT\d{8}", nct) or phase != "PHASE3":
        return None
    published = clean(trial.get("results_posted"))[:10]
    if published and published <= as_of.isoformat():
        return None
    status = clean(trial.get("status")).upper()
    if status not in ACTIVE:
        # An already completed trial may have had an unindexed press release.
        # Do not classify it as prospectively unreported on registry data alone.
        return None

    protocol = protocol or {}
    cap = cap or {}
    points = 0
    gaps = []

    ticker = clean(trial.get("ticker")).upper()
    drug = clean(trial.get("drug"))
    indication = clean(trial.get("indication"))
    if ticker and drug and indication and clean(trial.get("source_url")):
        points += 10
    else:
        gaps.append("Company / drug / indication identity")

    primary = clean(protocol.get("primary_endpoint"))
    frame = clean(protocol.get("primary_timeframe"))
    if primary:
        points += 15
    else:
        gaps.append("Protocol primary endpoint")
    if frame:
        points += 5
    else:
        gaps.append("Endpoint time frame")

    allocation = clean(protocol.get("allocation")).upper()
    masking = clean(protocol.get("masking")).upper()
    if allocation and allocation not in {"NA", "UNKNOWN"}:
        points += 7
    else:
        gaps.append("Randomization / allocation method")
    if masking and masking not in {"UNKNOWN", "NA"}:
        points += 8
    else:
        gaps.append("Masking / blinding plan")

    comparator = clean(protocol.get("comparator"))
    if comparator:
        points += 10
    else:
        gaps.append("Control / comparator design")

    enrollment = clean(protocol.get("enrollment"))
    if enrollment.isdigit() and int(enrollment) > 0:
        points += 8
    else:
        gaps.append("Sample size / enrollment")
    if clean(protocol.get("enrollment_type")):
        points += 2
    else:
        gaps.append("Actual vs planned enrollment")

    completion = clean(trial.get("primary_completion"))
    if completion:
        points += 5
    else:
        gaps.append("Expected primary completion date")
    if clean(protocol.get("study_type")) and frame:
        points += 5
    else:
        gaps.append("Follow-up and protocol context")

    # No outcome evidence is safely collected here. It must be supported by
    # dated, indication-matched Phase 2 source documents before adding points.
    gaps.extend([
        "Phase 2 efficacy / effect size and CI (15)",
        "Phase 2 adverse events / discontinuation evidence (5)",
        "Documented pre-readout FDA alignment (5)",
        "Statistical power calculation and missing-data plan (not captured)",
    ])
    value = pd.to_numeric(cap.get("market_cap", ""), errors="coerce")
    cap_value = float(value) if pd.notna(value) else None
    cap_status = "IN RANGE" if cap_value is not None and MIN_CAP <= cap_value <= MAX_CAP else (
        "OUT OF RANGE" if cap_value is not None else "UNVERIFIED"
    )
    # Presence of registry data does NOT prove a company hasn't announced a
    # topline readout through press releases.
    protocol_source = clean(protocol.get("source_url")) or clean(trial.get("source_url"))
    return {
        "Ticker": ticker,
        "Company": clean(trial.get("company")),
        "Drug / Program": drug,
        "Indication": indication,
        "NCT ID": nct,
        "Trial Status": status,
        "Expected Primary Completion": completion,
        "Market Cap": cap_value,
        "Market Cap Gate": cap_status,
        "Evidence Score / 100": points,
        "Coverage": ("PROTOCOL PARTIAL" if protocol else "PROTOCOL NOT COLLECTED"),
        "Phase 3 Success Probability": "NOT CALIBRATED",
        "Phase 2 Efficacy": "NOT VERIFIED",
        "Phase 2 Safety": "NOT VERIFIED",
        "FDA Alignment": "NOT VERIFIED",
        "Primary Endpoints": primary,
        "Allocation": allocation,
        "Masking": masking,
        "Enrollment": enrollment,
        "Evidence Gaps": "; ".join(gaps),
        "Readout Verification": "REGISTRY UNPOSTED — CORPORATE READOUT NOT EXCLUDED",
        "Protocol Source": protocol_source,
        "Protocol Checked": clean(protocol.get("checked_at")),
    }


def build_scorecard(trials, protocols=(), market_caps=(), announcements=(),
                    *, as_of=None, cap_filter=True, include_unknown_caps=False):
    as_of = as_of or date.today()
    indexed = by_nct_protocol(protocols)
    caps = _market_caps(market_caps)
    released = _announced_ids(announcements, as_of)
    scored = {}
    for trial in trials:
        nct = clean(trial.get("nct_id"))
        if nct in released:
            continue
        ticker = clean(trial.get("ticker")).upper()
        row = score_row(trial, indexed.get(nct), caps.get(ticker), as_of=as_of)
        if row is None:
            continue
        if cap_filter and row["Market Cap Gate"] != "IN RANGE":
            if not (include_unknown_caps and row["Market Cap Gate"] == "UNVERIFIED"):
                continue
        old = scored.get(nct)
        if old is None or (row["Evidence Score / 100"], row["Protocol Checked"]) > (
            old["Evidence Score / 100"], old["Protocol Checked"]
        ):
            scored[nct] = row
    if not scored:
        return pd.DataFrame(columns=FIELDS)
    result = pd.DataFrame(scored.values(), columns=FIELDS)
    return result.sort_values(["Evidence Score / 100", "Ticker", "NCT ID"],
                              ascending=[False, True, True], kind="stable").reset_index(drop=True)


def load_scorecard(root="data", *, as_of=None, cap_filter=True, include_unknown_caps=False):
    root = Path(root)
    return build_scorecard(
        rows(root / "all_phase_trials.csv"),
        rows(root / "pre_readout_protocols.csv"),
        rows(root / "phase_pipeline_market_caps.csv"),
        rows(root / "phase3_announcements.csv"),
        as_of=as_of,
        cap_filter=cap_filter,
        include_unknown_caps=include_unknown_caps,
    )
