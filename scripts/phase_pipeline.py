#!/usr/bin/env python3
"""Persist Phase 2 trials and route verified Phase 3 programs to the dashboard.

Trial records are the evidence ledger; routing is by ticker/drug/indication,
never by ticker alone. This module does not score drugs or alter the PDUFA feed.
"""
import argparse
import csv
import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "https://clinicaltrials.gov/api/v2/studies"
STARTED_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "COMPLETED"}
COLUMNS = [
    "nct_id", "ticker", "company", "sponsor", "drug", "indication", "program_key",
    "program_identity_status", "phases", "trial_status", "start_date", "start_date_type",
    "primary_completion", "primary_completion_type", "study_completion", "results_first_posted",
    "source_url", "source_updated", "checked_at", "phase2_first_seen", "phase2_nct_ids",
    "phase3_candidate_nct", "phase3_target_start", "promotion_status", "promotion_reason",
    "destination", "promoted_at", "phase3_nct_id", "phase3_start_date", "phase3_source_url",
    "market_cap", "market_cap_source", "market_cap_checked_at", "market_cap_status",
    "universe_gate", "universe_reason", "stage_evidence_status",
]
CAP_COLUMNS = ["ticker", "market_cap", "market_cap_source", "market_cap_checked_at", "market_cap_status"]


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def company_name(value):
    value = normalize(value)
    return re.sub(r"\s+", " ", re.sub(
        r"\b(incorporated|inc|corporation|corp|company|co|plc|limited|ltd|llc|nv|ag|sa)\b",
        " ", value,
    )).strip()


def complete_date(value):
    value = clean(value)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def date_boundary(value):
    """A month-only date is not proof that an actual start has happened."""
    return complete_date(value)


def registry_index(registry):
    index = {}
    for row in registry:
        name = company_name(row.get("company"))
        if name and clean(row.get("ticker")):
            index.setdefault(name, {})[clean(row["ticker"]).upper()] = row
    return index


def experimental_drug(arms):
    interventions = [i for i in arms.get("interventions", [])
                     if i.get("type") in {"DRUG", "BIOLOGICAL"}
                     and clean(i.get("name")) and "placebo" not in clean(i.get("name")).lower()]
    groups = {clean(g.get("label")): g.get("type") for g in arms.get("armGroups", [])}
    candidates = []
    for intervention in interventions:
        types = {groups.get(clean(label)) for label in intervention.get("armGroupLabels", [])}
        if "EXPERIMENTAL" in types and "ACTIVE_COMPARATOR" not in types:
            candidates.append(clean(intervention["name"]))
    if not candidates and len(interventions) == 1:
        candidates = [clean(interventions[0]["name"])]
    candidates = sorted(set(candidates))
    if len(candidates) == 1:
        generic = {"experimental vaccine", "experimental drug", "investigational drug", "study drug", "study treatment", "vaccine", "drug", "active treatment"}
        return candidates[0], "REVIEW" if normalize(candidates[0]) in generic else "VERIFIED"
    names = candidates or sorted({clean(i["name"]) for i in interventions})
    return " | ".join(names), "REVIEW"


def study_record(study, identities, checked_at):
    protocol = study.get("protocolSection", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    matches = identities.get(company_name(sponsor.get("name")), {})
    if sponsor.get("class") != "INDUSTRY" or len(matches) != 1:
        return None
    company = next(iter(matches.values()))
    phases = sorted(set(protocol.get("designModule", {}).get("phases", [])))
    if not {"PHASE2", "PHASE3"}.intersection(phases):
        return None
    nct = clean(protocol.get("identificationModule", {}).get("nctId"))
    if not re.fullmatch(r"NCT\d{8}", nct):
        return None
    status = protocol.get("statusModule", {})
    drug, identity = experimental_drug(protocol.get("armsInterventionsModule", {}))
    conditions = sorted({clean(c) for c in protocol.get("conditionsModule", {}).get("conditions", []) if clean(c)})
    indication = " | ".join(conditions)
    if not drug or not indication:
        identity = "REVIEW"
    ticker = clean(company["ticker"]).upper()
    row = {key: "" for key in COLUMNS}
    row.update({
        "nct_id": nct, "ticker": ticker, "company": clean(company.get("company")),
        "sponsor": clean(sponsor.get("name")), "drug": drug, "indication": indication,
        "program_key": "|".join((ticker, normalize(drug), normalize(indication))),
        "program_identity_status": identity, "phases": "|".join(phases),
        "trial_status": clean(status.get("overallStatus")),
        "start_date": clean(status.get("startDateStruct", {}).get("date")),
        "start_date_type": clean(status.get("startDateStruct", {}).get("type")),
        "primary_completion": clean(status.get("primaryCompletionDateStruct", {}).get("date")),
        "primary_completion_type": clean(status.get("primaryCompletionDateStruct", {}).get("type")),
        "study_completion": clean(status.get("completionDateStruct", {}).get("date")),
        "results_first_posted": clean(status.get("resultsFirstPostDateStruct", {}).get("date")),
        "source_url": "https://clinicaltrials.gov/study/" + nct,
        "source_updated": clean(status.get("lastUpdatePostDateStruct", {}).get("date")),
        "checked_at": checked_at,
    })
    return row


def phase3_gate(row, today=None, max_source_age=180):
    today = today or date.today()
    if row.get("phases") != "PHASE3":
        return "REVIEW", "A standalone Phase 3 trial is not verified; combined Phase 2/3 does not establish the transition."
    if row.get("program_identity_status") != "VERIFIED" or not all(clean(row.get(k)) for k in ("ticker", "drug", "indication", "program_key")):
        return "REVIEW", "Company or investigational-drug/indication identity needs review."
    nct = clean(row.get("nct_id"))
    if not re.fullmatch(r"NCT\d{8}", nct) or row.get("source_url") != "https://clinicaltrials.gov/study/" + nct:
        return "REVIEW", "An exact ClinicalTrials.gov trial source is required."
    if row.get("trial_status") not in STARTED_STATUSES:
        return "REVIEW", "Phase 3 is planned, on hold, terminated, withdrawn, or has an unknown status."
    started = complete_date(row.get("start_date"))
    if row.get("start_date_type") != "ACTUAL" or started is None or started > today:
        return "REVIEW", "Phase 3 requires an actual, dated start; an estimated or future start does not qualify."
    updated = complete_date(row.get("source_updated"))
    if updated is None or not 0 <= (today - updated).days <= max_source_age:
        return "REVIEW", "Trial evidence is missing, future-dated, or older than the source freshness limit."
    checked = complete_date(clean(row.get("checked_at"))[:10])
    if checked is None or not 0 <= (today - checked).days <= 3:
        return "REVIEW", "The trial has not been checked successfully within three days."
    return "VERIFIED", "Exact sponsor and drug/indication; standalone Phase 3 with a verified actual start."


def universe_gate(row, today=None):
    today = today or date.today()
    checked = complete_date(clean(row.get("market_cap_checked_at"))[:10])
    source = "https://api.nasdaq.com/api/quote/" + clean(row.get("ticker")).upper() + "/summary?assetclass=stocks"
    try:
        cap = float(row.get("market_cap", ""))
    except (TypeError, ValueError):
        cap = 0
    if row.get("market_cap_status") != "VERIFIED" or row.get("market_cap_source") != source or cap <= 0 or checked is None or not 0 <= (today - checked).days <= 3:
        return "REVIEW", "Verify current market cap before applying the $300M–$10B universe gate."
    if not 300_000_000 <= cap <= 10_000_000_000:
        return "FAIL", "Verified market cap is outside $300M–$10B."
    return "PASS", "Verified current market cap is within $300M–$10B."


def fetch_market_caps(tickers):
    import requests
    def fetch(ticker):
        source = "https://api.nasdaq.com/api/quote/" + ticker + "/summary?assetclass=stocks"
        row = {"ticker": ticker, "market_cap": "", "market_cap_source": source,
               "market_cap_checked_at": datetime.now(timezone.utc).isoformat(), "market_cap_status": "REVIEW"}
        try:
            response = requests.get(source, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Origin": "https://www.nasdaq.com"}, timeout=(5, 15))
            response.raise_for_status()
            data = response.json().get("data") or {}
            raw = clean((data.get("summaryData", {}).get("MarketCap") or {}).get("value"))
            if clean(data.get("symbol")).upper() == ticker and re.fullmatch(r"[\d,]+(?:\.\d+)?", raw):
                value = float(raw.replace(",", ""))
                if value > 0:
                    row["market_cap"], row["market_cap_status"] = str(value), "VERIFIED"
        except (requests.RequestException, ValueError, AttributeError):
            pass
        return row
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(fetch, sorted(set(tickers))))


def reconcile_records(previous, incoming, today=None, max_source_age=180):
    today = today or date.today()
    stamp = today.isoformat()
    records = {clean(r.get("nct_id")): dict(r) for r in previous if clean(r.get("nct_id"))}
    for new in incoming:
        old = records.get(new["nct_id"], {})
        row = dict(new)
        # Identity corrections must be investigated rather than inheriting an
        # unrelated drug's transition or its Phase 2 history.
        same_program = not old or old.get("program_key") == row.get("program_key")
        if same_program:
            for field in ("phase2_first_seen", "promoted_at", "phase3_nct_id", "phase3_start_date", "phase3_source_url"):
                row[field] = old.get(field, "")
            for field in CAP_COLUMNS[1:]:
                if not clean(row.get(field)):
                    row[field] = old.get(field, "")
        else:
            row["program_identity_status"] = "REVIEW"
        if "PHASE2" in row.get("phases", "").split("|") and not row.get("phase2_first_seen"):
            row["phase2_first_seen"] = row.get("checked_at") or stamp
        records[row["nct_id"]] = row
    by_program = {}
    for row in records.values():
        by_program.setdefault(row.get("program_key", ""), []).append(row)
    for group in by_program.values():
        phase2 = [r for r in group if r.get("phase2_first_seen") or "PHASE2" in r.get("phases", "").split("|")]
        for row in group:
            status, reason = phase3_gate(row, today, max_source_age)
            row["stage_evidence_status"] = status
            cap_status, cap_reason = universe_gate(row, today)
            row["universe_gate"], row["universe_reason"] = cap_status, cap_reason
            if status == "VERIFIED" and cap_status != "PASS":
                status, reason = "REVIEW" if cap_status == "REVIEW" else "FAIL", cap_reason
            row["promotion_status"], row["promotion_reason"] = status, reason
            if status == "VERIFIED":
                row["promoted_at"] = row.get("promoted_at") or row.get("checked_at") or stamp
                row["phase3_nct_id"] = row["nct_id"]
                row["phase3_start_date"] = row["start_date"]
                row["phase3_source_url"] = row["source_url"]
        qualified = [r for r in group if r.get("promotion_status") == "VERIFIED"]
        promoted = qualified or [r for r in group if r.get("promoted_at") and r.get("nct_id") == r.get("phase3_nct_id")]
        chosen = max(promoted, key=lambda r: r.get("source_updated", "")) if promoted else None
        candidate_trials = [r for r in group if "PHASE3" in r.get("phases", "").split("|")]
        candidate = max(candidate_trials, key=lambda r: r.get("source_updated", "")) if candidate_trials else None
        phase2_ids = " | ".join(sorted({r["nct_id"] for r in phase2}))
        for row in group:
            row["phase2_nct_ids"] = phase2_ids
            row["phase3_candidate_nct"] = candidate["nct_id"] if candidate else ""
            row["phase3_target_start"] = candidate.get("start_date", "") if candidate else ""
            if chosen:
                row["destination"] = "MASTER TABLE"
                for field in ("promoted_at", "phase3_nct_id", "phase3_start_date", "phase3_source_url"):
                    row[field] = chosen.get(field, "")
                row["promotion_status"] = chosen["promotion_status"]
                row["promotion_reason"] = chosen["promotion_reason"]
            elif "PHASE2" in row.get("phases", "").split("|"):
                row["destination"] = "PIPELINE"
                if row.get("phases") == "PHASE2" and row.get("program_identity_status") == "VERIFIED":
                    updated = complete_date(row.get("source_updated"))
                    checked = complete_date(clean(row.get("checked_at"))[:10])
                    fresh = updated is not None and 0 <= (today - updated).days <= max_source_age and checked is not None and 0 <= (today - checked).days <= 3
                    if fresh and row.get("universe_gate") == "PASS" and row.get("trial_status") in STARTED_STATUSES:
                        row["promotion_status"] = "AWAITING_PHASE3"
                        row["promotion_reason"] = "Phase 2 program; awaiting a verified Phase 3 start."
                    else:
                        row["promotion_status"] = "REVIEW"
                        row["promotion_reason"] = row.get("universe_reason") if row.get("universe_gate") != "PASS" else "Review Phase 2 source freshness or planned/halted trial status."
            else:
                row["destination"] = "REVIEW"
    return sorted(records.values(), key=lambda r: (r.get("ticker", ""), r.get("program_key", ""), r["nct_id"]))


def master_additions(records, existing):
    """Produce research rows without inventing PDUFA dates, results or scores."""
    existing_ncts = {(clean(r.get("ticker")).upper(), nct)
                     for r in existing for nct in re.findall(r"NCT\d{8}", clean(r.get("nct_id")))}
    existing_programs = {(clean(r.get("ticker")).upper(), normalize(r.get("drug")), normalize(r.get("indication"))) for r in existing}
    selected = {}
    for row in records:
        if row.get("destination") != "MASTER TABLE" or not row.get("phase3_nct_id") or row.get("universe_gate") != "PASS":
            continue
        # Retain the actual Phase 3 evidence record rather than a Phase 2 row.
        if row.get("nct_id") != row.get("phase3_nct_id"):
            continue
        key = row.get("program_key", "")
        if key not in selected or row.get("source_updated", "") > selected[key].get("source_updated", ""):
            selected[key] = row
    additions = []
    for key, row in selected.items():
        ticker = clean(row["ticker"]).upper()
        if (ticker, row["phase3_nct_id"]) in existing_ncts or (ticker, normalize(row["drug"]), normalize(row["indication"])) in existing_programs:
            continue
        verified = row.get("promotion_status") == "VERIFIED"
        additions.append({
            "event_key": "PHASE3|" + ticker + "|" + hashlib.sha256(key.encode()).hexdigest()[:16],
            "ticker": ticker, "company": row.get("company", ""), "drug": row.get("drug", ""),
            "indication": row.get("indication", ""), "nct_id": row["phase3_nct_id"],
            "pdufa_date": "", "phase3_date": "", "approval_probability": "", "trade_score": "",
            "entry_gate": "REVIEW", "monitor_eligibility": "REVIEW",
            "check_status": "PHASE3 VERIFIED / ELIGIBILITY REVIEW" if verified else "REVIEW",
            "current_stage": "PHASE 3 ONGOING" if verified and row.get("trial_status") != "COMPLETED" else "PHASE 3 — RESULTS REVIEW" if verified else "PHASE 3 — EVIDENCE REVIEW",
            "next_milestone": "Phase 3 results" if verified else "Resolve Phase 3 evidence",
            "phase3_status": row.get("trial_status", ""), "phase3_start_date": row.get("phase3_start_date", ""),
            "primary_completion": row.get("primary_completion", ""), "study_completion": row.get("study_completion", ""),
            "results_first_posted": row.get("results_first_posted", ""),
            "trial_evidence_url": row.get("phase3_source_url", ""), "pipeline_promoted_at": row.get("promoted_at", ""),
            "pipeline_evidence_status": row.get("promotion_status", "REVIEW"),
            "pipeline_evidence_note": row.get("promotion_reason", ""),
            "last_checked": row.get("checked_at", ""), "evidence_cutoff": row.get("source_updated", ""),
            "setup_phase": "Phase 3 monitoring", "record_source": "PHASE 2 / 3 PIPELINE",
            "market_cap": row.get("market_cap", ""), "market_cap_source": row.get("market_cap_source", ""),
            "market_cap_checked_at": row.get("market_cap_checked_at", ""),
            "universe_gate": row.get("universe_gate", "REVIEW"),
        })
    return additions


def manual_master_additions(records, existing, transfers):
    """Route selected Phase 2 programs for review without claiming graduation."""
    existing_ncts = {(clean(r.get("ticker")).upper(), nct)
                     for r in existing for nct in re.findall(r"NCT\d{8}", clean(r.get("nct_id")))}
    existing_programs = {(clean(r.get("ticker")).upper(), normalize(r.get("drug")), normalize(r.get("indication"))) for r in existing}
    selected = {}
    for row in records:
        key = row.get("program_key", "")
        if key not in transfers or row.get("destination") != "PIPELINE" or row.get("universe_gate") != "PASS":
            continue
        if key not in selected or row.get("source_updated", "") > selected[key].get("source_updated", ""):
            selected[key] = row
    additions = []
    for key, row in selected.items():
        ticker = clean(row.get("ticker")).upper()
        if (ticker, row.get("nct_id")) in existing_ncts or (ticker, normalize(row.get("drug")), normalize(row.get("indication"))) in existing_programs:
            continue
        stage = "PHASE 2/3" if "PHASE3" in row.get("phases", "").split("|") else "PHASE 2"
        additions.append({
            "event_key": "PIPELINE_REVIEW|" + ticker + "|" + hashlib.sha256(key.encode()).hexdigest()[:16],
            "ticker": ticker, "company": row.get("company", ""), "drug": row.get("drug", ""),
            "indication": row.get("indication", ""), "nct_id": row.get("nct_id", ""),
            "pdufa_date": "", "phase3_date": "", "phase3_start_date": "", "approval_probability": "", "trade_score": "",
            "entry_gate": "REVIEW", "monitor_eligibility": "REVIEW", "check_status": "REVIEW — MANUAL PIPELINE TRANSFER",
            "current_stage": stage + " — MANUAL REVIEW", "next_milestone": "Verify standalone Phase 3 start",
            "trial_status": row.get("trial_status", ""), "phase3_status": "REVIEW", "registered_phase": row.get("phases", ""),
            "phase2_date": row.get("start_date", "") if row.get("start_date_type") == "ACTUAL" else "",
            "primary_completion": row.get("primary_completion", ""), "study_completion": row.get("study_completion", ""),
            "results_first_posted": row.get("results_first_posted", ""), "trial_evidence_url": row.get("source_url", ""),
            "pipeline_program_key": key, "pipeline_transfer_mode": "MANUAL REVIEW", "pipeline_promoted_at": transfers[key],
            "pipeline_evidence_status": "REVIEW", "pipeline_evidence_note": row.get("promotion_reason", ""),
            "last_checked": row.get("checked_at", ""), "evidence_cutoff": row.get("source_updated", ""),
            "setup_phase": "Phase 2 review", "record_source": "MANUAL PIPELINE TRANSFER",
            "market_cap": row.get("market_cap", ""), "market_cap_source": row.get("market_cap_source", ""),
            "market_cap_checked_at": row.get("market_cap_checked_at", ""), "universe_gate": row.get("universe_gate", "REVIEW"),
        })
    return additions


def read_rows(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def scan(data_dir, lookback_days=730, page_limit=60, max_source_age=180):
    import requests
    data_dir = Path(data_dir)
    ledger_path = data_dir / "phase_pipeline.csv"
    state_path = data_dir / "phase_pipeline_state.json"
    previous = read_rows(ledger_path)
    registry = read_rows(data_dir / "company_registry.csv")
    identities = registry_index(registry)
    now = datetime.now(timezone.utc)
    today = now.date()
    cutoff = today - timedelta(days=lookback_days)
    state = {
        "started_at": now.isoformat(), "status": "RUNNING", "registry_companies": len(registry),
        "scope": "Industry Phase 2/3 records updated since " + cutoff.isoformat(),
        "source_max_age_days": max_source_age, "studies_scanned": 0, "matched_trials": 0,
        "pages_scanned": 0, "complete": False, "errors": [], "new_master_programs": [],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    incoming = {}
    previously_tracked = {r["nct_id"] for r in previous}
    params = {
        "query.term": "(AREA[Phase]PHASE2 OR AREA[Phase]PHASE3) AND AREA[LeadSponsorClass]INDUSTRY AND AREA[LastUpdatePostDate]RANGE[" + cutoff.isoformat() + ",MAX]",
        "pageSize": 1000, "format": "json", "sort": "LastUpdatePostDate:desc",
    }
    session = requests.Session()
    try:
        for page in range(page_limit):
            response = None
            for attempt in range(3):
                try:
                    response = session.get(API, params=params, timeout=(10, 45))
                    response.raise_for_status()
                    break
                except requests.RequestException:
                    if attempt == 2:
                        raise
                    time.sleep(attempt + 1)
            payload = response.json()
            if not isinstance(payload.get("studies"), list):
                raise ValueError("ClinicalTrials.gov response lacks a studies list")
            for study in payload["studies"]:
                state["studies_scanned"] += 1
                row = study_record(study, identities, now.isoformat())
                if row:
                    # Do not seed long-finished archival trials into a new queue.
                    finished = complete_date(row.get("study_completion"))
                    if row["nct_id"] not in previously_tracked and row.get("trial_status") == "COMPLETED" and finished and finished < cutoff:
                        continue
                    incoming[row["nct_id"]] = row
            state["pages_scanned"] = page + 1
            print(f"Phase 2/3 scan: {state['studies_scanned']} studies; {len(incoming)} exact registry matches", flush=True)
            token = payload.get("nextPageToken")
            if not token:
                state["complete"] = True
                break
            params["pageToken"] = token
        state["status"] = "COMPLETE" if state["complete"] else "PARTIAL"
    except Exception as exc:
        state["status"] = "FAILED" if not incoming else "PARTIAL"
        state["errors"].append(f"{type(exc).__name__}: {exc}")
    finally:
        session.close()
    tickers = {r.get("ticker") for r in [*previous, *incoming.values()] if clean(r.get("ticker"))}
    print(f"Checking market caps for {len(tickers)} registry tickers", flush=True)
    cap_rows = fetch_market_caps(tickers)
    old_caps = {r["ticker"]: r for r in read_rows(data_dir / "phase_pipeline_market_caps.csv")}
    unavailable = sum(r["market_cap_status"] != "VERIFIED" for r in cap_rows)
    cached = 0
    for index, cap in enumerate(cap_rows):
        old = old_caps.get(cap["ticker"])
        if cap["market_cap_status"] != "VERIFIED" and old and universe_gate(old, today)[0] in {"PASS", "FAIL"}:
            # Preserve the original timestamp; a failed request never refreshes evidence.
            cap_rows[index] = old
            cached += 1
    cap_index = {r["ticker"]: r for r in cap_rows}
    cap_path = data_dir / "phase_pipeline_market_caps.csv"
    with cap_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CAP_COLUMNS)
        writer.writeheader()
        writer.writerows(cap_rows)
    for row in [*previous, *incoming.values()]:
        row.update(cap_index.get(row.get("ticker"), {}))
    if state["complete"]:
        for row in previous:
            if row["nct_id"] not in incoming:
                row["checked_at"] = ""
    records = reconcile_records(previous, list(incoming.values()), today, max_source_age)
    write_rows(ledger_path, records)
    before_keys = {r.get("program_key") for r in previous if r.get("promoted_at")}
    newly_promoted = {r.get("program_key"): r for r in records if r.get("promoted_at") and r.get("program_key") not in before_keys and r.get("nct_id") == r.get("phase3_nct_id")}
    # Four mutually exclusive statuses; market-cap evidence gaps are warnings, not full coverage.
    if state["complete"] and (state["errors"] or unavailable):
        state["status"] = "COMPLETE WITH WARNINGS"
    elif state["complete"]:
        state["status"] = "COMPLETE"
    elif state["status"] != "FAILED":
        state["status"] = "PARTIAL"
    state.update({
        "finished_at": datetime.now(timezone.utc).isoformat(), "matched_trials": len(incoming),
        "stored_trials": len(records),
        "phase2_programs": len({r["program_key"] for r in records if r.get("destination") == "PIPELINE" and r.get("universe_gate") == "PASS"}),
        "master_programs": len({r["program_key"] for r in records if r.get("destination") == "MASTER TABLE" and r.get("universe_gate") == "PASS"}),
        "review_trials": sum(r.get("destination") == "REVIEW" or r.get("universe_gate") == "REVIEW" for r in records),
        "market_cap_verified_tickers": sum(r["market_cap_status"] == "VERIFIED" for r in cap_rows),
        "market_cap_source_unavailable": unavailable, "market_cap_recent_cache_retained": cached,
        "new_master_programs": [{"ticker": r["ticker"], "drug": r["drug"], "nct_id": r["nct_id"]} for r in newly_promoted.values()],
    })
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in state.items() if k != "new_master_programs"}, indent=2), flush=True)
    if state["status"] == "FAILED":
        raise RuntimeError("Phase 2/3 scan failed; saved records were preserved.")
    return state


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--lookback-days", type=int, default=730)
    parser.add_argument("--page-limit", type=int, default=60)
    parser.add_argument("--max-source-age", type=int, default=180)
    args = parser.parse_args()
    scan(args.data_dir, args.lookback_days, args.page_limit, args.max_source_age)
