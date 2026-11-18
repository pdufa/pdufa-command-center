"""Read-only Level 7 FOCUS coverage report for an explicitly supplied roster.

This is evidence provenance coverage, NOT clinical scoring or FDA prediction.
No roster mutations, database writes, or network calls.
"""
from __future__ import annotations
import re
from level7_store import EvidenceStore

_NCT = re.compile(r"NCT[0-9]{8}\Z")

def focus_level7_coverage(store: EvidenceStore, members: list[dict]) -> dict:
    if not isinstance(members, list) or not members:
        raise ValueError("Nonempty reconciled FOCUS roster required")
    seen = set()
    trials = []
    for member in members:
        if not isinstance(member, dict):
            raise ValueError("Invalid roster member")
        nct = member.get("nct")
        if not isinstance(nct, str) or not _NCT.fullmatch(nct) or nct in seen:
            raise ValueError("Invalid or duplicate FOCUS NCT")
        seen.add(nct)
        records = store.history(nct)
        latest = {}
        for record in records:
            previous = latest.get(record.source_id)
            if previous is None or (record.retrieved_at, record.source_version) > (
                previous.retrieved_at, previous.source_version
            ):
                latest[record.source_id] = record
        statuses = {key: sum(r.status == key for r in latest.values())
                    for key in ("verified", "unverified", "missing", "inaccessible", "conflicting")}
        trials.append({
            "nct": nct,
            "sourceVersions": len(records),
            "distinctSources": len(latest),
            "statusCounts": statuses,
            "readiness": ("CONFLICT_REVIEW" if statuses["conflicting"] else
                          "SOURCE_COVERAGE_PRESENT" if latest else "NO_LEVEL7_EVIDENCE"),
            "assessmentStatus": "NOT_SCORED",
            "fdaPrediction": None,
        })
    return {
        "kind": "FOCUS_LEVEL7_EVIDENCE_COVERAGE_NOT_FDA_PREDICTIONS",
        "total": len(trials),
        "trialsWithEvidence": sum(bool(t["sourceVersions"]) for t in trials),
        "trials": trials,
    }
