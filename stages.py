"""Evidence-based program stages shared by tables and stock charts."""
from datetime import datetime
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import pandas as pd

PACIFIC = ZoneInfo("America/Los_Angeles")
MAX_CHECK_AGE_DAYS = 3
STAGE_HELP = "Current stage for this exact program. Financing and FDA review can overlap. Completed trials require results review; missing, conflicting or stale evidence is marked REVIEW."
DAYS_HELP = "Calendar days to the saved PDUFA date, using Pacific time. Negative values mean that date has passed. Blank means no PDUFA date is recorded."


def text(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    value = str(value).strip()
    return "" if value.lower() in {"nan", "nat", "<na>", "not available", "none"} else value


def name(value):
    return re.sub(r"[^a-z0-9]+", " ", text(value).lower()).strip()


def values(row):
    return {name(k): text(v) for k, v in dict(row).items()}


def get(row, *keys):
    for key in keys:
        value = row.get(name(key), "")
        if value:
            return value
    return ""


def stage_date(value):
    if isinstance(value, (int, float)) or not text(value):
        return None
    try:
        stamp = pd.Timestamp(value)
        if stamp.tzinfo is not None:
            stamp = stamp.tz_convert(PACIFIC)
        return stamp.date()
    except (ValueError, TypeError, OverflowError):
        return None


def fresh(value, today):
    checked = stage_date(value)
    return checked is not None and 0 <= (today - checked).days <= MAX_CHECK_AGE_DAYS


def ticker_of(row):
    row = values(row)
    ticker = get(row, "ticker", "symbol")
    if ticker.startswith("http"):
        ticker = parse_qs(urlparse(ticker).query).get("ticker", [""])[0]
    if not ticker:
        key = get(row, "event_key", "program_key")
        parts = key.split("|")
        if len(parts) > 1:
            ticker = parts[1] if parts[0] in {"PHASE3", "PIPELINE_REVIEW"} else parts[0]
    return ticker.upper().strip()


def program_stage(record, today=None):
    """Describe the recorded stage without promoting predictions to outcomes."""
    today = today or datetime.now(PACIFIC).date()
    row = values(record)
    outcome = get(row, "actual_outcome", "actual_fda_decision", "FDA Decision", "Actual FDA", "outcome").upper()
    decision = stage_date(get(row, "decision_date", "Decision Date"))
    pdufa = stage_date(get(row, "pdufa_date", "PDUFA Date", "canonical_pdufa_date"))
    observed_date = decision or pdufa
    if outcome in {"APPROVED", "CRL", "REJECTED"} and observed_date and observed_date <= today:
        return "FDA APPROVED" if outcome == "APPROVED" else "FDA CRL"

    checked = get(row, "last_checked", "checked_at", "Last Checked")
    conflict = get(row, "conflict_flag").upper() not in {"", "NONE", "NO", "FALSE", "0", "PASS"}
    current = get(row, "current_stage", "Current Stage")
    phase_status = get(row, "phase3_status", "Phase 3").upper()
    phases = get(row, "phases", "registered_phase", "Registered Phase").upper().replace(" ", "")
    trial_status = get(row, "trial_status", "Trial Status", "Phase 2 Status").upper()
    stage_verified = get(row, "pipeline_evidence_status", "Stage Evidence", "promotion_status", "Current Evidence").upper() == "VERIFIED" and fresh(checked, today)
    if "MANUAL REVIEW" in current.upper():
        clinical = "PHASE 2/3 — MANUAL REVIEW" if "2/3" in current else "PHASE 2 — MANUAL REVIEW"
    elif stage_verified or phases == "PHASE3" or "PHASE 3" in current.upper():
        clinical = "PHASE 3 COMPLETED — RESULTS REVIEW" if trial_status == "COMPLETED" or "RESULTS REVIEW" in current.upper() else "PHASE 3 ONGOING" if stage_verified else "PHASE 3 — REVIEW"
    elif "PHASE2" in phases or "PHASE 2" in current.upper():
        if "PHASE3" in phases:
            clinical = "PHASE 2/3 — REVIEW"
        elif trial_status == "COMPLETED":
            clinical = "PHASE 2 COMPLETED — PHASE 3 PENDING"
        elif trial_status == "NOT_YET_RECRUITING":
            clinical = "PHASE 2 PLANNED — REVIEW"
        else:
            clinical = "PHASE 2 ONGOING" if get(row, "promotion_status", "Graduation Status") == "AWAITING_PHASE3" and fresh(checked, today) else "PHASE 2 — REVIEW"
    elif phase_status in {"RESULTS_VERIFIED", "RESULTS_REVIEW"} or stage_date(get(row, "phase3_date", "Phase 3 Readout")):
        clinical = "PHASE 3 RESULTS VERIFIED" if phase_status == "RESULTS_VERIFIED" and not conflict and fresh(checked, today) and get(row, "trial_evidence_url") else "PHASE 3 RESULTS — REVIEW"
    else:
        clinical = "STAGE UNKNOWN — REVIEW"

    confirmation = get(row, "pdufa_confirmation").upper()
    if pdufa:
        known = confirmation.startswith("VERIFIED") and get(row, "pdufa_evidence_url") and fresh(checked, today) and not conflict
        clinical = "PDUFA / FDA REVIEW" if known and pdufa >= today else "FDA DECISION PENDING — REVIEW" if pdufa < today else "PDUFA / FDA REVIEW — EVIDENCE REVIEW"
    elif stage_date(get(row, "fda_acceptance_date", "FDA Acceptance")):
        clinical = "FDA APPLICATION ACCEPTED — REVIEW"
    elif stage_date(get(row, "nda_submission_date", "NDA Submission")):
        clinical = "NDA/BLA SUBMITTED — REVIEW"

    # CLOSED takes precedence over historical Announced/Running milestone flags.
    financing = get(row, "second_financing_status", "Financing #2 Status").upper()
    source = get(row, "second_financing_source", "Financing Close Evidence", "financing_evidence_url")
    audit = get(row, "second_financing_audit_status").upper()
    closed = get(row, "second_financing_closed", "second_financing_close_verified").upper() in {"YES", "TRUE", "1", "VERIFIED"} or financing == "CLOSED"
    finance_stamp = get(row, "verified_as_of", "financing_checked_at")
    close_date = stage_date(get(row, "second_financing_date", "Financing #2 Date"))
    if closed:
        verified = audit == "VERIFIED_SECOND_POST_PHASE3_FINANCING" and source and close_date and close_date <= today and fresh(finance_stamp, today)
        finance_stage = "2ND FINANCING CLOSED" if verified else "FINANCING STATUS — REVIEW"
    elif financing in {"RUNNING", "IN_PROGRESS", "IN PROGRESS", "PENDING", "OPEN", "PRICED", "ANNOUNCED"}:
        verified = audit.startswith("VERIFIED") and source and fresh(finance_stamp, today)
        finance_stage = ("FINANCING ANNOUNCED" if financing in {"ANNOUNCED", "PRICED"} else "FINANCING IN PROGRESS") if verified else "FINANCING STATUS — REVIEW"
    else:
        finance_stage = ""
    return f"{finance_stage} · {clinical}" if finance_stage else clinical


class StageIndex:
    """Resolve exact event/program identities and keep ambiguous tickers in REVIEW."""
    def __init__(self, records=(), today=None):
        self.today = today or datetime.now(PACIFIC).date()
        self.records = [dict(r) for r in records]
        self.by_ticker = {}
        self.by_event = {}
        for record in self.records:
            row = values(record)
            self.by_ticker.setdefault(ticker_of(record), []).append(record)
            event = get(row, "event_key")
            if event:
                self.by_event.setdefault(event, []).append(record)

    def matching_records(self, record):
        row = values(record)
        event = get(row, "event_key")
        if not event and get(row, "ticker").startswith("http"):
            event = parse_qs(urlparse(get(row, "ticker")).query).get("event", [""])[0]
        candidates = self.by_event.get(event, []) if event else self.by_ticker.get(ticker_of(record), [])
        drug, indication = name(get(row, "drug")), name(get(row, "indication"))
        pdufa = stage_date(get(row, "pdufa_date", "PDUFA Date"))
        if drug:
            candidates = [r for r in candidates if name(get(values(r), "drug")) == drug]
        if indication:
            candidates = [r for r in candidates if name(get(values(r), "indication")) == indication]
        if pdufa:
            candidates = [r for r in candidates if stage_date(get(values(r), "pdufa_date")) == pdufa]
        return candidates

    def resolve(self, record):
        row = values(record)
        if get(row, "STAGE"):
            return get(row, "STAGE")
        # A displayed pipeline row carries its own registered phase and evidence.
        if get(row, "phases", "Registered Phase", "current_stage"):
            return program_stage(record, self.today)
        candidates = self.matching_records(record)
        identities = {(name(get(values(r), "drug")), name(get(values(r), "indication")), get(values(r), "event_key")) for r in candidates}
        if len(identities) == 1:
            return program_stage(candidates[0], self.today)
        own = program_stage(record, self.today)
        if own != "STAGE UNKNOWN — REVIEW":
            return own
        return "MULTIPLE PROGRAMS — REVIEW" if candidates else own

    def countdown(self, record, use_catalog=True):
        row = values(record)
        pdufa = stage_date(get(row, "pdufa_date", "PDUFA Date", "canonical_pdufa_date"))
        if pdufa is None and use_catalog:
            candidates = self.matching_records(record)
            identities = {(name(get(values(r), "drug")), name(get(values(r), "indication")), get(values(r), "event_key")) for r in candidates}
            if len(identities) == 1:
                pdufa = stage_date(get(values(candidates[0]), "pdufa_date"))
        return (pdufa - self.today).days if pdufa else pd.NA


def add_stage_column(frame, index=None, source=None):
    """Keep Ticker, STAGE and DAYS TO PDUFA adjacent without changing rows."""
    result = frame.copy()
    ticker_column = next((c for c in result.columns if name(c) == "ticker"), None)
    if ticker_column is None:
        if source is not None:
            result.insert(0, "Ticker", [ticker_of(source.loc[i]) if isinstance(source, pd.DataFrame) else ticker_of(source) for i in result.index])
        elif any(name(c) in {"event key", "program key"} for c in result.columns) and any(ticker_of(r) for r in result.to_dict("records")):
            result.insert(0, "Ticker", [ticker_of(r) for r in result.to_dict("records")])
        else:
            return result
        ticker_column = "Ticker"
    index = index or StageIndex()
    for column in list(result.columns):
        if name(column) == "days to pdufa":
            result = result.drop(columns=[column])
    if "STAGE" in result:
        stages = result.pop("STAGE")
    else:
        stages = [program_stage(source.loc[i] if isinstance(source, pd.DataFrame) else source, index.today) if source is not None else index.resolve(r)
                  for i, r in zip(result.index, result.to_dict("records"))]
    result.insert(result.columns.get_loc(ticker_column) + 1, "STAGE", stages)
    countdown = [index.countdown(source.loc[i] if isinstance(source, pd.DataFrame) else source, use_catalog=False) if source is not None else index.countdown(r)
                 for i, r in zip(result.index, result.to_dict("records"))]
    result.insert(result.columns.get_loc("STAGE") + 1, "DAYS TO PDUFA", pd.array(countdown, dtype="Int64"))
    return result


def chart_programs(ticker, data_root):
    """Use the same saved program evidence on the dedicated stock-chart page."""
    from scripts.phase_pipeline import read_rows, reconcile_records, master_additions
    root = Path(data_root)
    live = read_rows(root / "pdufa_candidates.csv")
    finance = {r.get("event_key"): r for r in read_rows(root / "second_financing_status.csv")}
    for row in live:
        row.update({k: v for k, v in finance.get(row.get("event_key"), {}).items() if k != "event_key"})
    pipeline = reconcile_records(read_rows(root / "phase_pipeline.csv"), [], datetime.now(ZoneInfo("UTC")).date())
    rows = live + master_additions(pipeline, live)
    existing = {(ticker_of(r), name(r.get("drug")), name(r.get("indication"))) for r in rows}
    for row in sorted(pipeline, key=lambda r: r.get("source_updated", ""), reverse=True):
        key = (ticker_of(row), name(row.get("drug")), name(row.get("indication")))
        if row.get("destination") == "PIPELINE" and row.get("universe_gate") == "PASS" and key not in existing:
            rows.append(row)
            existing.add(key)
    return [r for r in rows if ticker_of(r) == ticker.upper()]
