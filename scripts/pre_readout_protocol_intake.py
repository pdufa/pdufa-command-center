#!/usr/bin/env python3
"""Collect current Phase 3 protocol DESIGN ONLY, never outcome data.

The result is NOT a historical pre-readout snapshot and does not certify
absence of a corporate topline release. Historical backtesting requires
archived timestamped protocol versions and release dates.
"""
import argparse
import csv
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from zoneinfo import ZoneInfo
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from pre_readout import ACTIVE, MIN_CAP, MAX_CAP, clean, rows, _announced_ids, _market_caps
FIELDS = (
    "nct_id", "primary_endpoint", "primary_timeframe", "allocation", "masking",
    "intervention_model", "comparator", "enrollment", "enrollment_type",
    "study_type", "first_posted", "source_updated", "source_url", "checked_at",
    "registry_overall_status", "registry_results_first_posted",
)


def eligible_ids(root, today, include_unknown_caps=False):
    trials = rows(root / "all_phase_trials.csv")
    excluded = _announced_ids(rows(root / "phase3_announcements.csv"), today)
    caps = _market_caps(rows(root / "phase_pipeline_market_caps.csv"))
    selected = {}
    for trial in trials:
        nct = clean(trial.get("nct_id"))
        if not re.fullmatch(r"NCT\d{8}", nct) or nct in excluded:
            continue
        if clean(trial.get("phase")).upper() != "PHASE3":
            continue
        if clean(trial.get("status")).upper() not in ACTIVE:
            continue
        # Never include a trial for which this ledger contains any result date.
        if clean(trial.get("results_posted")):
            continue
        cap = caps.get(clean(trial.get("ticker")).upper(), {})
        try:
            value = float(cap.get("market_cap"))
        except (TypeError, ValueError):
            value = None
        verified = clean(cap.get("market_cap_status")).upper() == "VERIFIED"
        checked = clean(cap.get("market_cap_checked_at"))[:10]
        cap_valid = verified and checked and checked <= today.isoformat()
        if not (cap_valid and value is not None and MIN_CAP <= value <= MAX_CAP):
            if not (include_unknown_caps and value is None):
                continue
        selected[nct] = trial
    return selected


def protocol_only(study, *, checked_at):
    """Use protocolSection only. Deliberately ignore resultsSection entirely."""
    p = study.get("protocolSection") or {}
    ident = p.get("identificationModule") or {}
    status = p.get("statusModule") or {}
    design = p.get("designModule") or {}
    arms = p.get("armsInterventionsModule") or {}
    outcome = p.get("outcomesModule") or {}
    measures = outcome.get("primaryOutcomes") or []
    first = measures[0] if measures else {}
    design_info = design.get("designInfo") or {}
    en = design.get("enrollmentInfo") or {}
    mask = design_info.get("maskingInfo") or {}
    names = [(i.get("name") or "") for i in arms.get("interventions") or []]
    arms_groups = arms.get("armGroups") or []
    comparisons = [str(g.get("label") or "") for g in arms_groups
                   if g.get("type") in ("PLACEBO_COMPARATOR", "ACTIVE_COMPARATOR",
                                        "SHAM_COMPARATOR", "NO_INTERVENTION")]
    if not comparisons:
        comparisons = [name for name in names
                       if re.search(r"\b(placebo|sham|standard of care)\b", name, re.I)]
    first_posted = (status.get("studyFirstPostDateStruct") or {}).get("date", "")
    updated = (status.get("lastUpdatePostDateStruct") or {}).get("date", "")
    nct = clean(ident.get("nctId"))
    if not re.fullmatch(r"NCT\d{8}", nct):
        raise ValueError("Unexpected / missing exact NCT ID")
    return dict(
        nct_id=nct,
        primary_endpoint=str(first.get("measure") or ""),
        primary_timeframe=str(first.get("timeFrame") or ""),
        allocation=str(design_info.get("allocation") or ""),
        masking=str(mask.get("masking") or ""),
        intervention_model=str(design_info.get("interventionModel") or ""),
        comparator=" | ".join(sorted(set(c for c in comparisons if c))),
        enrollment=str(en.get("count") or ""),
        enrollment_type=str(en.get("type") or ""),
        study_type=str(design.get("studyType") or "INTERVENTIONAL"),
        first_posted=str(first_posted),
        source_updated=str(updated),
        source_url="https://clinicaltrials.gov/study/" + nct,
        checked_at=checked_at,
        registry_overall_status=str(status.get("overallStatus") or ""),
        registry_results_first_posted=str(
            (status.get("resultsFirstPostDateStruct") or {}).get("date") or ""
        ),
    )


def fetch(nct):
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct
    # Be respectful of ClinicalTrials.gov rate limits: on a 429 response
    # honor Retry-After if supplied, otherwise use exponential backoff.
    for attempt in range(5):
        try:
            req = Request(url, headers={"User-Agent":"PDUFA-Pre-Readout-Research/1.0", "Accept":"application/json"})
            with urlopen(req, timeout=25) as resp:
                study = json.load(resp)
            data = protocol_only(study, checked_at=datetime.now(timezone.utc).isoformat())
            if data["nct_id"] != nct:
                raise ValueError("Registry NCT differs from requested study")
            return data
        except HTTPError as exc:
            if exc.code == 429:
                if attempt == 4:
                    raise
                retry_header = exc.headers.get("Retry-After", "") if exc.headers else ""
                try:
                    delay = min(120, max(5, int(retry_header)))
                except (TypeError, ValueError):
                    delay = min(90, 10 * (2 ** attempt))
                time.sleep(delay)
                continue
            if attempt == 4 or exc.code in (400, 401, 403, 404):
                raise
            time.sleep(min(60, 2 ** (attempt + 1)))
        except (TimeoutError, OSError):
            if attempt == 4:
                raise
            time.sleep(min(60, 2 ** (attempt + 1)))


def save_csv(path, records):
    temp = path.with_suffix(".tmp")
    with temp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(records, key=lambda x:x.get("nct_id", "")))
    temp.replace(path)


def run(data_dir, limit=160, workers=3, include_unknown_caps=False):
    data_dir = Path(data_dir)
    out = data_dir / "pre_readout_protocols.csv"
    existing = {r.get("nct_id"):r for r in rows(out) if r.get("nct_id")}
    today_local = datetime.now(ZoneInfo("America/Los_Angeles")).date()
    selected = eligible_ids(data_dir, today_local, include_unknown_caps=include_unknown_caps)
    today = datetime.now(timezone.utc)
    age_seconds = 24*3600
    # Collect missing IDs first. Refresh older snapshots only after all
    # remaining uncollected trials have had a chance to enter the scorecard.
    fresh = [n for n in sorted(selected) if n not in existing]
    def stale(n):
        # A newly introduced release-status field must be populated by
        # refetching; a recent old-schema row is not sufficient evidence.
        if "registry_results_first_posted" not in existing[n] or "registry_overall_status" not in existing[n]:
            return True
        stamp = clean(existing[n].get("checked_at"))
        if not stamp:
            return True
        try:
            return (today - datetime.fromisoformat(stamp.replace("Z","+00:00"))).total_seconds()>age_seconds
        except (TypeError, ValueError):
            return True
    old = [n for n in sorted(selected) if n in existing and stale(n)]
    due = (fresh + old)[:max(1,limit)]
    errors = {}
    with ThreadPoolExecutor(max_workers=max(1,min(workers,12))) as pool:
        jobs = {pool.submit(fetch,nct):nct for nct in due}
        for future in as_completed(jobs):
            nct=jobs[future]
            try:
                existing[nct] = future.result()
            except Exception as exc:
                errors[nct]=str(exc)[:230]
    # Persist only prospective candidates; remove those newly known to have
    # released results so their protocol cannot be misread as an active prediction.
    current_records = [v for k,v in existing.items() if k in selected]
    save_csv(out, current_records)
    state={
        "as_of":today.isoformat(),"market_cap_range_usd":[MIN_CAP,MAX_CAP],
        "active_registry_unposted_phase3_trials":len(selected),
        "protocol_records_stored":len(current_records),
        "fetched_this_run":len(due),"failed_fetches":len(errors),
        "uncollected_trials":sum(n not in existing for n in selected),
        "errors":errors,
        "clinical_success_probability":"NOT CALIBRATED",
        "limitations":"Registry-only release status; issuer topline could already be public. Current protocol revisions are not archived historical snapshots. No Phase 2 effects, safety dossier, power analysis, or FDA correspondence collected.",
    }
    state["status"]="COMPLETE" if not errors and state["uncollected_trials"]==0 else "PARTIAL"
    (data_dir/"pre_readout_intake_status.json").write_text(json.dumps(state,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in state.items() if k!="errors"},indent=2),flush=True)
    return 0 if not errors else 1


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--data-dir",type=Path,default=ROOT/"data")
    parser.add_argument("--limit",type=int,default=160)
    parser.add_argument("--workers",type=int,default=3)
    parser.add_argument("--include-unknown-caps",action="store_true")
    args=parser.parse_args()
    raise SystemExit(run(args.data_dir,args.limit,args.workers,args.include_unknown_caps))
