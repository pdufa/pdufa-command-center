"""Opt-in Level 7 adapter for FOCUS nightly monitor reports.

Stores monitor-derived observations, NOT the underlying registry response.
No membership, prediction, or nightly worker mutation.
"""
from __future__ import annotations
import json
import re
from level7_evidence import make_record
from level7_store import EvidenceStore

_NCT = re.compile(r"NCT[0-9]{8}\Z")

def persist_focus_monitor_report(store: EvidenceStore, report: dict) -> dict:
    if report.get("kind") != "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS":
        raise ValueError("Unexpected FOCUS monitor report kind")
    stamp = report.get("runAtUTC")
    if not isinstance(stamp, str):
        raise ValueError("Missing run timestamp")
    trials = report.get("trials")
    if not isinstance(trials, list):
        raise ValueError("Missing trial observations")
    store.initialize()
    added, unchanged = 0, 0
    seen = set()
    for trial in trials:
        nct = trial.get("nct")
        if not isinstance(nct, str) or not _NCT.fullmatch(nct) or nct in seen:
            raise ValueError("Invalid or duplicate NCT in monitor report")
        seen.add(nct)
        status = trial.get("sourceStatus")
        if status not in ("OFFICIAL_REGISTRY_RETRIEVED", "OFFICIAL_SOURCE_UNAVAILABLE"):
            raise ValueError("Unexpected source status")
        # A monitor summary is not the original registry response. Its
        # sourceHash remains metadata, never a digest of the summary.
        observation = {
            "nct": nct, "sourceStatus": status,
            "registrySourceHash": trial.get("sourceHash"),
            "delta": trial.get("delta"),
            "registryUpdated": trial.get("registryUpdated"),
        }
        content = (json.dumps(observation, sort_keys=True).encode("utf-8")
                   if status == "OFFICIAL_REGISTRY_RETRIEVED" else None)
        record = make_record(
            trial_id=nct, source_id="FOCUS_NIGHTLY_MONITOR_OBSERVATION",
            source_url="https://clinicaltrials.gov/study/" + nct,
            publisher="FOCUS nightly monitor (derived observation)",
            source_version=stamp, retrieved_at=stamp, content=content,
            status="unverified" if content is not None else "inaccessible",
            notes="Derived monitor metadata; not a verified primary registry document",
        )
        if store.add(record):
            added += 1
        else:
            unchanged += 1
    return {"added": added, "unchanged": unchanged, "trials": len(seen)}
