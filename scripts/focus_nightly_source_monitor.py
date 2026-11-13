#!/usr/bin/env python3
"""Nightly exact-NCT FOCUS evidence deltas; never a clinical signoff or FDA prediction."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener, HTTPRedirectHandler
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ROSTER_PATH = ROOT / "new-platform/frontend/data/p3PostDataActive.json"
APPLICATIONS_PATH = ROOT / "new-platform/backend/app/data/focus_application_snapshot.json"
CURRENT_PATH = ROOT / "data/focus_nightly_evidence_current.json"
NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")
MAX_BYTES = 2_500_000
SOURCE_FIELDS = ("statusModule", "designModule", "armsInterventionsModule", "outcomesModule",
                 "eligibilityModule", "sponsorCollaboratorsModule")

def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def digest(data):
    return hashlib.sha256(canonical(data).encode("utf-8")).hexdigest()

def load_json(path, missing_ok=False):
    if missing_ok and not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))

def roster_and_cycles(roster, applications):
    rows, leads = roster.get("records"), applications.get("records")
    if not isinstance(rows, list) or not rows or not isinstance(leads, list):
        raise ValueError("Canonical FOCUS roster or application index unavailable")
    by_nct = {}
    for row in rows:
        nct, ticker = row.get("nct"), row.get("ticker")
        if (not isinstance(nct, str) or not NCT_PATTERN.fullmatch(nct)
                or not isinstance(ticker, str) or not ticker or nct in by_nct):
            raise ValueError("FOCUS exact-NCT identity missing or duplicated")
        by_nct[nct] = row
    links = {nct: [] for nct in by_nct}  # Preserve unmapped current studies.
    observed = set()
    for lead in leads:
        nct = lead.get("nct")
        if nct in observed or nct not in by_nct:
            raise ValueError("FOCUS application index has duplicate or foreign NCT")
        observed.add(nct)
        candidates = lead.get("candidateApplications")
        if not isinstance(candidates, list) or not candidates:
            raise ValueError("FOCUS application cycle unresolved")
        accepted = []
        for app in candidates:
            cycle = app.get("cycleId")
            if not cycle or app.get("ticker") != by_nct[nct]["ticker"]:
                raise ValueError("FOCUS FDA-cycle mapping disagrees with ticker")
            accepted.append(cycle)
        links[nct] = sorted(set(accepted))
    return by_nct, links

def fetch_registry(nct):
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    url = "https://clinicaltrials.gov/api/v2/studies/" + nct
    req = Request(url, headers={"Accept": "application/json",
                    "User-Agent": "PDUFA-FocusSourceResearch/1.0 (public registry research)"})
    with build_opener(NoRedirect()).open(req, timeout=22) as response:
        if response.status != 200 or "json" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Official registry response invalid")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Official registry response too large")
    return json.loads(raw)

def summarize_registry(nct, payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("protocolSection"), dict):
        raise ValueError("Official registry missing protocol")
    p = payload["protocolSection"]
    if (p.get("identificationModule") or {}).get("nctId") != nct:
        raise ValueError("Official registry NCT identity mismatch")
    status = p.get("statusModule") or {}
    design = p.get("designModule") or {}
    results = payload.get("resultsSection") or {}
    if not isinstance(results, dict):
        raise ValueError("Official registry results invalid")
    evidence = {"protocol": {key: p.get(key) for key in SOURCE_FIELDS},
                "results": results, "documents": payload.get("documentSection") or {}}
    return {"sourceHash": digest(evidence), "phase": list(design.get("phases") or []),
            "registryStatus": status.get("overallStatus"),
            "registryUpdated": (status.get("studyLastUpdatePostDateStruct") or {}).get("date"),
            "primaryCompletion": (status.get("primaryCompletionDateStruct") or {}).get("date"),
            "postedRegistryResults": bool(results),
            "registeredPrimaryOutcomeCount": len((p.get("outcomesModule") or {}).get("primaryOutcomes") or []),
            "registeredSeriousAdverseEventModule": bool(results.get("adverseEventsModule")),
            "sourceUrl": "https://clinicaltrials.gov/study/" + nct}

def build_report(roster, applications, prior, fetcher, now=None):
    rows, links = roster_and_cycles(roster, applications)
    previous = {x["nct"]: x for x in prior.get("trials", [])
                if isinstance(x, dict) and isinstance(x.get("nct"), str)}
    now = now or datetime.now(timezone.utc)
    trials, changed, retrieved = [], [], 0
    for nct, row in sorted(rows.items()):
        old = previous.get(nct) or {}
        trial = {"nct": nct, "ticker": row["ticker"], "company": row.get("company"),
                 "applicationCycles": links[nct],
                 "sourceUrl": "https://clinicaltrials.gov/study/" + nct,
                 "issuerEvidenceUrlAsRecorded": row.get("regulatoryUrl"),
                 "issuerEvidenceVerification": "NOT_CHECKED_IN_REGISTRY_MONITOR",
                 "fdaOutcome": "NOT_ADJUDICATED", "scientificSignoff": False,
                 "calibratedProbability": None}
        try:
            trial.update(summarize_registry(nct, fetcher(nct)))
            trial["sourceStatus"] = "OFFICIAL_REGISTRY_RETRIEVED"
            retrieved += 1
            trial["delta"] = ("FIRST_SOURCE_OBSERVATION" if not old.get("sourceHash")
                              else "REGISTRY_EVIDENCE_CHANGED" if trial["sourceHash"] != old["sourceHash"]
                              else "NO_REGISTRY_EVIDENCE_CHANGE")
            if trial["delta"] != "NO_REGISTRY_EVIDENCE_CHANGE":
                changed.append(nct)
        except (HTTPError, URLError, ValueError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            trial.update(sourceStatus="OFFICIAL_SOURCE_UNAVAILABLE",
                         sourceErrorType=type(exc).__name__, sourceHash=old.get("sourceHash"),
                         lastVerifiedRegistryDate=old.get("registryUpdated"), delta="SOURCE_RECOVERY_REQUIRED")
        trials.append(trial)
    cycles = sorted({c for nct in rows for c in links[nct]})
    queue = sorted({c for nct in changed for c in links[nct]})
    unlinked = sorted(nct for nct in rows if not links[nct])
    unavailable = len(trials) - retrieved
    return {"schemaVersion": 1,
            "kind": "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS",
            "runAtUTC": now.astimezone(timezone.utc).isoformat(),
            "pacificDate": now.astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat(),
            "rosterSnapshotAsOf": roster.get("asOf"),
            "applicationCrosswalkAsOf": applications.get("asOf"),
            "applicationCrosswalkState": "PARTIAL" if unlinked else "COMPLETE_RECORD_COVERAGE",
            "sourceAuthority": "ClinicalTrials.gov API v2; exact-NCT public records",
            "researchPolicy": {"phaseFirst": True, "independentMedicalReviewComplete": False,
                               "FDAOutcomeDetermined": False, "probabilitiesUpdated": False,
                               "trialMembershipOrSheetWrites": False,
                               "issuerFDARegulatoryResearchRequiredSeparately": True,
                               "unchangedEvidenceNotNewValidation": True},
            "summary": {"focusTrials": len(trials), "applicationCycles": len(cycles),
                        "sourceRetrieved": retrieved, "sourceUnavailable": unavailable,
                        "newOrChangedEvidenceTrials": len(changed),
                        "reassessmentQueueCycles": len(queue),
                        "unmappedApplicationNcts": len(unlinked),
                        "status": "SOURCE_MONITOR_COMPLETE" if unavailable == 0 else "PARTIAL_SOURCE_MONITOR",
                        "scientificAssessmentsRevalidated": 0, "predictionProbabilitiesUpdated": 0},
            "reassessmentQueue": [
                {"cycleId": c, "ncts": sorted(n for n in changed if c in links[n]),
                 "reason": "NEW_OR_CHANGED_REGISTRY_EVIDENCE",
                 "action": "INDEPENDENT_PHASE_FIRST_SCIENCE_AND_FDA_REGULATORY_REVIEW"}
                for c in queue],
            "unmappedApplicationReviewQueue": [{"nct": nct, "ticker": rows[nct]["ticker"],
                "reason":"CURRENT_FOCUS_TRIAL_HAS_NO_MAPPED_APPLICATION_CYCLE",
                "action":"INDEPENDENT_DRUG_INDICATION_AND_FDA_CYCLE_RECONCILIATION"} for nct in unlinked],
            "sourceRecoveryQueue": [t["nct"] for t in trials if t["sourceStatus"] == "OFFICIAL_SOURCE_UNAVAILABLE"],
            "trials": trials}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, default=CURRENT_PATH)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(load_json(ROSTER_PATH), load_json(APPLICATIONS_PATH),
                          load_json(args.current, missing_ok=True), fetch_registry)
    summary = report["summary"]
    if summary["sourceRetrieved"] == 0:
        raise SystemExit("Zero official source reads; refusing to publish")
    if args.archive.exists():
        raise SystemExit("Refuse to overwrite immutable run archive")
    args.archive.parent.mkdir(parents=True, exist_ok=True)
    args.current.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(report, indent=2, sort_keys=True) + "\n"
    args.archive.write_text(data, encoding="utf-8")
    args.current.write_text(data, encoding="utf-8")
    print("FOCUS nightly:", canonical(summary))
    if os.getenv("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("## FOCUS nightly source monitor\n\n")
            for k, v in summary.items():
                f.write(f"- {k}: {v}\n")
            f.write("\nRegistry evidence monitoring only. No medical signoffs or new FDA predictions.\n")
    if summary["sourceUnavailable"]:
        print("::warning::Partial FOCUS registry coverage: inspect source recovery queue")

if __name__ == "__main__":
    main()
