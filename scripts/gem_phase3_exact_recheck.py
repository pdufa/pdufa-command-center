#!/usr/bin/env python3
"""Recheck exact-NCT ClinicalTrials.gov result postings for GEM programs.

Registry result-posting dates are discovery evidence, NOT independently
verified Phase 3 topline success or the issuer's actual release date. This
file only publishes source-review observations; trading gates are unchanged.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

FIELDS = (
    "event_key", "ticker", "drug", "saved_phase3_status", "saved_phase3_date",
    "saved_trial_source", "nct_ids", "nct_checked", "nct_results_posted",
    "nct_without_results", "nct_unavailable", "registry_results_post_dates",
    "source_recheck_status", "verification_needed", "checked_at_utc",
    "gem_phase3_benchmark_upgraded",
)
NCT_RE = re.compile(r"NCT\d{8}", re.I)


def get_study(nct):
    request = urllib.request.Request(
        "https://clinicaltrials.gov/api/v2/studies/" + nct,
        headers={"User-Agent": "PDUFACommandCenter/1.0 (research-only)",
                 "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=14) as resp:
        if resp.status != 200:
            raise ValueError("Unsuccessful registry response")
        return json.loads(resp.read(2_000_000))


def audit_events(events, fetch_study=get_study):
    checked_at = datetime.now(timezone.utc).isoformat()
    cache = {}
    audit = []
    for event in events:
        key = str(event.get("event_key") or "").strip()
        if not key:
            continue
        supplied = str(event.get("nct_id") or "").upper()
        ids = list(dict.fromkeys(NCT_RE.findall(supplied)))
        # Refuse to assign one trial's registry results to other program IDs.
        all_valid = bool(ids) and re.fullmatch(r"NCT\d{8}(?:\s*[|,;]\s*NCT\d{8})*", supplied.strip()) is not None
        posted, unposted, unavailable, dates = [], [], [], []
        if all_valid:
            for nct in ids[:8]:
                if nct not in cache:
                    try:
                        payload = fetch_study(nct)
                        actual = (((payload.get("protocolSection") or {})
                                   .get("identificationModule") or {}).get("nctId") or "").upper()
                        if actual != nct:
                            raise ValueError("Registry returned an unexpected trial ID")
                        status = ((payload.get("protocolSection") or {})
                                  .get("statusModule") or {})
                        date = (status.get("resultsFirstPostDateStruct") or {}).get("date", "")
                        cache[nct] = ("POSTED" if (payload.get("hasResults") is True and date) else "NOT_POSTED", date)
                    except Exception as exc:
                        cache[nct] = ("SOURCE_UNAVAILABLE_" + type(exc).__name__, "")
                state, result_date = cache[nct]
                if state == "POSTED":
                    posted.append(nct)
                    dates.append(nct + ": " + result_date)
                elif state == "NOT_POSTED":
                    unposted.append(nct)
                else:
                    unavailable.append(nct)
        if not all_valid:
            status = "NCT_ID_MISSING_OR_INVALID"
            needed = "Verified exact Phase 3 trial ID, program identity and dated issuer results"
        elif unavailable:
            status = "CLINICAL_REGISTRY_PARTIAL_OR_BLOCKED"
            needed = "Retry unavailable registry trials; verify issuer readout date and outcome"
        elif posted:
            status = "POSTED_RESULTS_DISCOVERY_ONLY"
            needed = "Independently match drug, indication, issuer readout date, endpoints and trial"
        else:
            status = "NO_POSTED_REGISTRY_RESULTS"
            needed = "Find dated primary issuer topline results; trial completion alone is insufficient"
        audit.append({
            "event_key": key, "ticker": event.get("ticker", ""), "drug": event.get("drug", ""),
            "saved_phase3_status": event.get("phase3_status", ""),
            "saved_phase3_date": event.get("phase3_date", ""),
            "saved_trial_source": event.get("trial_evidence_url", ""),
            "nct_ids": " | ".join(ids), "nct_checked": len(posted) + len(unposted),
            "nct_results_posted": " | ".join(posted),
            "nct_without_results": " | ".join(unposted),
            "nct_unavailable": " | ".join(unavailable),
            "registry_results_post_dates": " | ".join(dates),
            "source_recheck_status": status,
            "verification_needed": needed, "checked_at_utc": checked_at,
            "gem_phase3_benchmark_upgraded": "NO",
        })
    return audit


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("data/gem_phase3_exact_recheck.csv"))
    parser.add_argument("--summary", type=Path, default=Path("reports/gem_daily/gem_phase3_exact_recheck_summary.json"))
    args = parser.parse_args(argv)
    with (args.data_dir / "pdufa_candidates.csv").open(newline="", encoding="utf-8-sig") as f:
        events = list(csv.DictReader(f))
    if not events:
        parser.error("Missing exact-event PDUFA candidate ledger")
    rows = audit_events(events)
    if len(rows) != sum(bool(x.get("event_key")) for x in events):
        parser.error("Not all exact-event program rows were audited")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    from collections import Counter
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "exact_programs_checked": len(rows),
        "states": dict(Counter(x["source_recheck_status"] for x in rows)),
        "gem_benchmarks_automatically_upgraded": 0,
        "note": "Registry results are leads. Issuer readout and source-verified Phase 3 events require exact-program adjudication.",
    }
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
