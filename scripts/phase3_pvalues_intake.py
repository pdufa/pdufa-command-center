#!/usr/bin/env python3
"""Extract reported Phase 3 primary-endpoint p-values, without inferring trial success."""
import argparse
import csv
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIELDS = ["nct_id", "ticker", "company", "drug", "indication", "result_posted_at",
          "primary_endpoint", "time_frame", "comparison", "p_value", "p_value_modifier",
          "statistical_method", "effect_parameter", "effect_value", "ci_percent",
          "ci_lower", "ci_upper", "analysis_notes", "outcome_status",
          "source_url", "checked_at"]

def load(path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def save(path, records, fields):
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    os.replace(tmp, path)

def fetch(nct):
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct
    for attempt in range(4):
        try:
            with urlopen(Request(url, headers={"User-Agent": "PDUFA-Research/1.0", "Accept": "application/json"}), timeout=35) as response:
                return json.load(response)
        except (HTTPError, URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

def text(value):
    return "" if value is None else str(value)

def run(mode, data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)
    source = load(data_dir / "phase3_announcements.csv")
    trials = {r["nct_id"]: r for r in source if r.get("nct_id", "").startswith("NCT")}
    output = data_dir / "phase3_primary_pvalues.csv"
    prior = load(output)
    existing = {}
    for r in prior:
        existing.setdefault(r["nct_id"], []).append(r)
    now = datetime.now(timezone.utc).isoformat()
    recent = (datetime.now(timezone.utc).date() - timedelta(days=90)).isoformat()
    targets = [nct for nct, row in trials.items()
               if mode == "backfill" or nct not in existing or row.get("phase3_results_posted_at", "") >= recent]
    state = {"mode": mode, "started_at": now, "total_registered_trials": len(trials),
             "targets": len(targets), "checked": 0, "failed": 0, "errors": [],
             "complete": False}
    def persist():
        flat = [r for nct in sorted(existing) for r in existing[nct]]
        save(output, flat, FIELDS)
        state["trials_with_reported_primary_pvalue"] = len({
            r["nct_id"] for r in flat if r.get("p_value", "").strip()})
        state["primary_endpoint_analysis_rows"] = len(flat)
        state["trials_without_reported_primary_pvalue"] = len({
            r["nct_id"] for r in flat if not any(x.get("p_value", "").strip() for x in existing[r["nct_id"]])})
        state["unprocessed_registered_trials"] = len(set(trials) - set(existing))
        (data_dir / "phase3_pvalues_status.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    for nct in targets:
        base = trials[nct]
        try:
            study = fetch(nct)
            measures = (study.get("resultsSection") or {}).get("outcomeMeasuresModule", {}).get("outcomeMeasures") or []
            extracted = []
            for measure in measures:
                if str(measure.get("type", "")).upper() != "PRIMARY":
                    continue
                analyses = measure.get("analyses") or []
                if not analyses:
                    analyses = [{}]
                for analysis in analyses:
                    p = text(analysis.get("pValue"))
                    extracted.append({
                        "nct_id": nct, "ticker": base.get("ticker", ""), "company": base.get("company", ""),
                        "drug": base.get("drug", ""), "indication": base.get("indication", ""),
                        "result_posted_at": base.get("phase3_results_posted_at", ""),
                        "primary_endpoint": text(measure.get("title")),
                        "time_frame": text(measure.get("timeFrame")),
                        "comparison": " | ".join(map(str, analysis.get("groupIds") or [])),
                        "p_value": p, "p_value_modifier": text(analysis.get("pValueModifier")),
                        "statistical_method": text(analysis.get("statisticalMethod")),
                        "effect_parameter": text(analysis.get("paramType")),
                        "effect_value": text(analysis.get("paramValue")),
                        "ci_percent": text(analysis.get("ciPctValue")),
                        "ci_lower": text(analysis.get("ciLowerLimit")),
                        "ci_upper": text(analysis.get("ciUpperLimit")),
                        "analysis_notes": text(analysis.get("statisticalComment")),
                        "outcome_status": "PRIMARY_P_REPORTED" if p else "PRIMARY_P_NOT_REPORTED",
                        "source_url": "https://clinicaltrials.gov/study/" + nct,
                        "checked_at": now})
            if not extracted:
                extracted = [{**{key: "" for key in FIELDS}, "nct_id": nct,
                              "ticker": base.get("ticker", ""), "company": base.get("company", ""),
                              "drug": base.get("drug", ""), "indication": base.get("indication", ""),
                              "result_posted_at": base.get("phase3_results_posted_at", ""),
                              "outcome_status": "NO_PRIMARY_OUTCOME_RESULTS",
                              "source_url": "https://clinicaltrials.gov/study/" + nct, "checked_at": now}]
            existing[nct] = extracted
        except Exception as exc:
            state["failed"] += 1
            if len(state["errors"]) < 30:
                state["errors"].append(nct + ": " + type(exc).__name__ + ": " + str(exc)[:160])
        state["checked"] += 1
        if state["checked"] % 25 == 0:
            persist()
            print("Checked", state["checked"], "/", len(targets), flush=True)
        time.sleep(0.08)
    state["complete"] = state["failed"] == 0
    state["finished_at"] = datetime.now(timezone.utc).isoformat()
    state["status"] = "COMPLETE" if state["complete"] else "PARTIAL"
    persist()
    print(json.dumps(state, indent=2))
    if state["failed"]:
        raise RuntimeError("Some trial lookups failed; successful results retained for next retry.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["backfill", "daily"], default="daily")
    parser.add_argument("--data-dir", type=Path, default=DATA)
    args = parser.parse_args()
    run(args.mode, args.data_dir)
