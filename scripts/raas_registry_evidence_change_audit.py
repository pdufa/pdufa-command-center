#!/usr/bin/env python3
"""Append-only exact-NCT registry source-change audit for the nightly RAAS scan.

Compares two *frozen* ClinicalTrials.gov index snapshots captured on the two
sides of a completed source harvest. The hash represents API source bytes;
registry result posting is not a verified public Phase 3 topline readout or
FDA outcome. This script NEVER grades a metric or changes a historical score.
"""
from __future__ import annotations

# Permanent retirement: historical functions are importable for read-only audits only.
if __name__ == "__main__":
    raise SystemExit("RAAS_PERMANENTLY_RETIRED: this archived command cannot run or modify historical records.")


import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BEFORE = ROOT / "new-platform/frontend/public/raas-registry-evidence-index.json"
AFTER = BEFORE
HISTORY = ROOT / "new-platform/frontend/data/raas-registry-evidence-change-history.json"
STATUS = ROOT / "new-platform/frontend/data/raas-registry-evidence-change-status.json"
RECEIPTS = ROOT / "data/raas_registry_live_evidence.json"
NCT = re.compile(r"NCT\d{8}\Z")
HEX = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = "RAAS_EXACT_NCT_REGISTRY_SOURCE_CHANGE_HISTORY_UNGRADED"
STATUS_SCOPE = "RAAS_NIGHTLY_REGISTRY_CHANGE_AUDIT_RESEARCH_ONLY"
REVIEW_TRIGGERS = {
    "RESULTS_FIRST_POSTED", "RESULTS_POSTING_REVERSED",
    "PRIMARY_OUTCOME_RESULTS_CHANGED", "SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED",
    "PRIMARY_ENDPOINT_PROTOCOL_CHANGED", "TRIAL_DESIGN_CHANGED",
    "TRIAL_CONTEXT_CHANGED",
}
METRIC_ROUTING = {
    "RESULTS_FIRST_POSTED": ["post-1-1", "post-1-3", "post-1-5"],
    "RESULTS_POSTING_REVERSED": ["post-1-1", "post-1-3", "post-1-5"],
    "PRIMARY_OUTCOME_RESULTS_CHANGED": ["post-1-1", "post-1-3"],
    "SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED": ["post-1-5"],
    "PRIMARY_ENDPOINT_PROTOCOL_CHANGED": ["pre-1-2"],
    "TRIAL_DESIGN_CHANGED": ["pre-1-2"],
    "TRIAL_CONTEXT_CHANGED": ["pre-1-2"],
}

def instant(raw: str) -> datetime:
    if not isinstance(raw, str) or not raw:
        raise ValueError("RAAS_CHANGE_AUDIT_MISSING_SOURCE_TIME")
    try:
        ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("RAAS_CHANGE_AUDIT_INVALID_SOURCE_TIME") from error
    if ts.tzinfo is None:
        raise ValueError("RAAS_CHANGE_AUDIT_NAIVE_SOURCE_TIME")
    return ts.astimezone(timezone.utc)

def checksum(value: object) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False).encode("utf-8")).hexdigest()

def validate_index(raw: dict) -> dict[str, dict]:
    if (not isinstance(raw, dict) or raw.get("schemaVersion") != 1 or
        raw.get("scope") != "RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX" or
        not isinstance(raw.get("records"), list) or
        not isinstance(raw.get("summary"), dict) or
        raw["summary"].get("approvedOverallRaasScores") != 0):
        raise ValueError("RAAS_CHANGE_AUDIT_INDEX_INVALID")
    instant(raw.get("sourceAsOf"))
    mapping = {}
    for r in raw["records"]:
        if (not isinstance(r, dict) or not isinstance(r.get("nctId"), str) or
            not NCT.fullmatch(r["nctId"]) or r["nctId"] in mapping or
            not isinstance(r.get("ticker"), str) or not r["ticker"].strip() or
            r.get("sourceUrl") != "https://clinicaltrials.gov/study/" + r["nctId"] or
            not isinstance(r.get("sourceHash"), str) or
            not HEX.fullmatch(r["sourceHash"]) or
            not isinstance(r.get("postedResults"), bool) or
            r.get("evidenceState") != (
                "POSTED_RESULTS_UNGRADED" if r["postedResults"] else "PROTOCOL_ONLY"
            ) or (not r["postedResults"] and (
                r.get("postedPrimaryOutcomeCount") or r.get("seriousAdverseEventTermCount")
                or r.get("primaryResults") or r.get("seriousEventDetails")
            ))):
            raise ValueError("RAAS_CHANGE_AUDIT_ROW_IDENTITY_OR_RESULTS_INVALID")
        mapping[r["nctId"]] = r
    if (len(mapping) != raw["summary"].get("researchNcts") or
        len(mapping) != raw["summary"].get("registryRecords") or
        sum(bool(r["postedResults"]) for r in mapping.values()) !=
        raw["summary"].get("postedRegistryResults")):
        raise ValueError("RAAS_CHANGE_AUDIT_ROSTER_OR_RESULT_COUNT_INVALID")
    return mapping

def change_categories(before: dict, after: dict) -> list[str]:
    changed = []
    def diff(*names: str) -> bool:
        return any(before.get(name) != after.get(name) for name in names)
    if before["postedResults"] != after["postedResults"]:
        changed.append("RESULTS_FIRST_POSTED" if after["postedResults"]
                       else "RESULTS_POSTING_REVERSED")
    if diff("primaryResults", "postedPrimaryOutcomeCount", "postedOtherOutcomeCount"):
        changed.append("PRIMARY_OUTCOME_RESULTS_CHANGED")
    if diff("seriousEventDetails", "seriousAdverseEventTermCount"):
        changed.append("SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED")
    if diff("primaryDefinitions"):
        changed.append("PRIMARY_ENDPOINT_PROTOCOL_CHANGED")
    if diff("registeredDesign"):
        changed.append("TRIAL_DESIGN_CHANGED")
    if diff("registeredPhases", "registeredConditions", "registeredInterventions"):
        changed.append("TRIAL_CONTEXT_CHANGED")
    if diff("registryStatus"):
        changed.append("TRIAL_STATUS_CHANGED")
    if diff("resultsFirstPosted"):
        changed.append("RESULTS_PUBLICATION_DATE_CHANGED")
    if diff("registryLastUpdated"):
        changed.append("REGISTRY_LAST_UPDATED_DATE_CHANGED")
    if not changed and before["sourceHash"] != after["sourceHash"]:
        changed.append("OTHER_OFFICIAL_SOURCE_PACKET_UPDATE")
    return changed

def latest_summary(record: dict) -> dict:
    """Only aggregate provenance and counts, not individual adverse-event data."""
    return {
        "registeredPhase": list(record.get("registeredPhases") or []),
        "registryStatus": record.get("registryStatus"),
        "registryLastUpdated": record.get("registryLastUpdated"),
        "resultsFirstPosted": record.get("resultsFirstPosted"),
        "postedResults": record["postedResults"],
        "primaryResultCount": len(record.get("primaryResults") or []),
        "postedPrimaryOutcomeCount": record.get("postedPrimaryOutcomeCount"),
        "seriousAdverseEventTermCount": record.get("seriousAdverseEventTermCount"),
        "primaryResultsDigest": checksum(record.get("primaryResults") or []),
        "seriousEventsDigest": checksum(record.get("seriousEventDetails") or []),
        "registeredDesignDigest": checksum(record.get("registeredDesign") or {}),
    }

def empty_history() -> dict:
    return {"schemaVersion": 1, "scope": SCOPE, "events": []}

def validate_history(history: dict) -> None:
    if (not isinstance(history, dict) or history.get("schemaVersion") != 1 or
        history.get("scope") != SCOPE or not isinstance(history.get("events"), list)):
        raise ValueError("RAAS_CHANGE_AUDIT_HISTORY_INVALID")
    ids = set()
    last = None
    for event in history["events"]:
        if (not isinstance(event, dict) or not NCT.fullmatch(str(event.get("nctId"))) or
            not HEX.fullmatch(str(event.get("previousSourceHash"))) or
            not HEX.fullmatch(str(event.get("newSourceHash"))) or
            event.get("previousSourceHash") == event.get("newSourceHash") or
            not HEX.fullmatch(str(event.get("eventId"))) or
            event["eventId"] in ids or not isinstance(event.get("changeCategories"), list) or
            event.get("approvedRaasScore") is not None or
            event.get("calibratedFdaProbability") is not None):
            raise ValueError("RAAS_CHANGE_AUDIT_HISTORY_EVENT_INVALID")
        ts = instant(event.get("observedAt"))
        if last is not None and ts < last:
            raise ValueError("RAAS_CHANGE_AUDIT_HISTORY_NOT_CHRONOLOGICAL")
        last = ts
        ids.add(event["eventId"])

def validate_receipts(receipts: dict, now: dict) -> tuple[int, int, int, set[str]]:
    if (receipts.get("scope") != "RAAS_CT_GOV_LIVE_EVIDENCE" or
        receipts.get("schemaVersion") != 1 or
        receipts.get("latestAttemptAt") != now.get("sourceAsOf") or
        not isinstance(receipts.get("errors"), list) or
        not isinstance(receipts.get("summary"), dict)):
        raise ValueError("RAAS_CHANGE_AUDIT_RECEIPTS_MISMATCH")
    s = receipts["summary"]
    attempted, retrieved, failed = [s.get(k) for k in
                                   ("attemptedThisRun", "retrievedThisRun", "failedThisRun")]
    if (any(type(v) is not int or v < 0 for v in (attempted, retrieved, failed)) or
        attempted != retrieved + failed or attempted != len(now["records"])):
        raise ValueError("RAAS_CHANGE_AUDIT_RECEIPTS_COUNTS_INVALID")
    failures = set()
    for issue in receipts["errors"]:
        if (not isinstance(issue, dict) or not NCT.fullmatch(str(issue.get("nctId"))) or
            issue["nctId"] in failures):
            raise ValueError("RAAS_CHANGE_AUDIT_RECEIPTS_FAILURE_IDENTITY")
        failures.add(issue["nctId"])
    if len(failures) != failed:
        raise ValueError("RAAS_CHANGE_AUDIT_RECEIPTS_FAILURE_COUNT")
    return attempted, retrieved, failed, failures

def reconcile(before: dict, after: dict, history: dict, receipts: dict,
              recorded_at: str) -> tuple[dict, dict]:
    previous = validate_index(before)
    latest = validate_index(after)
    validate_history(history)
    if set(previous) != set(latest) or len(latest) != 762:
        raise ValueError("RAAS_CHANGE_AUDIT_INCOMPLETE_OR_CHANGED_RESEARCH_COHORT")
    if instant(after["sourceAsOf"]) <= instant(before["sourceAsOf"]):
        raise ValueError("RAAS_CHANGE_AUDIT_STALE_OR_SAME_SCAN")
    time = instant(recorded_at)
    if time < instant(after["sourceAsOf"]):
        raise ValueError("RAAS_CHANGE_AUDIT_RECORDED_BEFORE_SOURCE")
    if history["events"] and time < instant(history["events"][-1]["observedAt"]):
        raise ValueError("RAAS_CHANGE_AUDIT_HISTORY_BACKDATING")
    attempted, retrieved, failed, failures = validate_receipts(receipts, after)
    events = list(history["events"])
    changed_ncts = 0
    review_needed = 0
    source_hash_changes = 0
    new_results = 0
    changed_results = 0
    changed_safety = 0
    changed_protocol = 0
    for nct in sorted(previous):
        old, cur = previous[nct], latest[nct]
        if old["ticker"].strip().upper() != cur["ticker"].strip().upper():
            raise ValueError("RAAS_CHANGE_AUDIT_TICKER_REASSIGNMENT")
        if nct in failures:
            if old["sourceHash"] != cur["sourceHash"]:
                raise ValueError("RAAS_CHANGE_AUDIT_FAILED_FETCH_WITH_NEW_HASH")
            continue
        if old["sourceHash"] == cur["sourceHash"]:
            # Source-derived facts may not drift without a source change.
            if change_categories(old, cur):
                raise ValueError("RAAS_CHANGE_AUDIT_SILENT_FACT_DRIFT")
            continue
        source_hash_changes += 1
        categories = change_categories(old, cur)
        if not categories:
            raise ValueError("RAAS_CHANGE_AUDIT_MISSING_CHANGE_CATEGORY")
        changed_ncts += 1
        review = bool(REVIEW_TRIGGERS.intersection(categories))
        review_needed += int(review)
        new_results += int("RESULTS_FIRST_POSTED" in categories)
        changed_results += int("PRIMARY_OUTCOME_RESULTS_CHANGED" in categories)
        changed_safety += int("SERIOUS_ADVERSE_EVENT_RESULTS_CHANGED" in categories)
        changed_protocol += int(bool({"PRIMARY_ENDPOINT_PROTOCOL_CHANGED",
                                      "TRIAL_DESIGN_CHANGED"} & set(categories)))
        metrics = sorted({metric for category in categories
                          for metric in METRIC_ROUTING.get(category, [])})
        event_id = sha256((nct+"|"+old["sourceHash"]+"|"+cur["sourceHash"]+"|"
                           +recorded_at).encode()).hexdigest()
        events.append({
            "eventId": event_id, "observedAt": recorded_at, "nctId": nct,
            "ticker": cur["ticker"], "sourceUrl": cur["sourceUrl"],
            "previousSourceHash": old["sourceHash"],
            "newSourceHash": cur["sourceHash"],
            "before": latest_summary(old), "after": latest_summary(cur),
            "changeCategories": categories,
            "reviewFlag": "CLINICAL_OR_DESIGN_REVIEW_REQUIRED" if review
                          else "OTHER_OFFICIAL_REGISTRY_UPDATE",
            "candidateResearchMetricIds": metrics,
            "approvedRaasScore": None, "calibratedFdaProbability": None,
            "note": "Only a newly observed registry source revision. Date of the underlying event and public Phase 3 readout are not verified. Existing RAAS score history is unchanged."
        })
    new_ledger = {"schemaVersion": 1, "scope": SCOPE, "events": events}
    status = {
        "schemaVersion": 1, "scope": STATUS_SCOPE,
        "auditState": "COMPLETED_WITH_SOURCE_ERRORS" if failed else "COMPLETE",
        "previousSourceAsOf": before["sourceAsOf"],
        "latestSourceAsOf": after["sourceAsOf"],
        "recordedAt": recorded_at, "trackedResearchNcts": 762,
        "sourceFetchAttempted": attempted, "sourceFetchSucceeded": retrieved,
        "sourceFetchFailed": failed, "sourceFetchFailureNcts": sorted(failures),
        "sourceHashChangedNcts": source_hash_changes,
        "changedNctsThisAudit": changed_ncts,
        "reviewNeededNctsThisAudit": review_needed,
        "firstPostedRegistryResultsThisAudit": new_results,
        "changedPrimaryResultsThisAudit": changed_results,
        "changedSafetyEvidenceThisAudit": changed_safety,
        "changedPrimaryProtocolOrDesignThisAudit": changed_protocol,
        "newEvents": len(events) - len(history["events"]),
        "totalRetainedHistoricalEvents": len(events),
        "approvedRaasScoreUpdates": 0,
        "calibratedFdaForecastUpdates": 0,
        "scopeNote": "Research-only ClinicalTrials.gov before/after source audit. A source update is not a dated public Phase 3 readout, FDA action, validated clinical result, RAAS 0-100 score, or automatic rating revision. Prior source hashes and all historical event records are retained."
    }
    validate_history(new_ledger)
    return new_ledger, status

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, default=RECEIPTS)
    parser.add_argument("--history", type=Path, default=HISTORY)
    parser.add_argument("--status", type=Path, default=STATUS)
    args = parser.parse_args()
    if args.before.resolve() == args.after.resolve():
        raise ValueError("RAAS_CHANGE_AUDIT_SAME_SNAPSHOT_PATH")
    prior = json.loads(args.before.read_text(encoding="utf-8"))
    latest = json.loads(args.after.read_text(encoding="utf-8"))
    receipts = json.loads(args.receipts.read_text(encoding="utf-8"))
    history = (json.loads(args.history.read_text(encoding="utf-8"))
               if args.history.exists() else empty_history())
    recorded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    new_ledger, status = reconcile(prior, latest, history, receipts, recorded_at)
    args.history.parent.mkdir(parents=True, exist_ok=True)
    args.status.parent.mkdir(parents=True, exist_ok=True)
    # Never partially publish a misleading completed status: all checks above first.
    args.history.write_text(json.dumps(new_ledger, indent=2, ensure_ascii=False)+"\n",
                            encoding="utf-8")
    args.status.write_text(json.dumps(status, indent=2, ensure_ascii=False)+"\n",
                           encoding="utf-8")
    print("RAAS registry exact-source revisions:", json.dumps({
        "changedNcts": status["changedNctsThisAudit"],
        "needsIndependentReview": status["reviewNeededNctsThisAudit"],
        "sourceFetchFailed": status["sourceFetchFailed"],
        "retainedHistoricalEvents": status["totalRetainedHistoricalEvents"]
    }, sort_keys=True))

if __name__ == "__main__":
    main()
