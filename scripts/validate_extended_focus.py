"""Exercise Levels 7–20 against captured FOCUS registry bytes in local SQLite."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from uuid import uuid4

from sqlalchemy import URL, create_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "new-platform/backend")]

from app import assessment_runtime as runtime
from level7_store import EvidenceStore
from scripts.focus_nightly_source_monitor import summarize_registry


def registry_snapshot(store, nct, *, source_event=None):
    candidates = [record for record in store.history(nct)
                  if record.source_id == "CLINICALTRIALS_GOV_REGISTRY" and record.status == "verified"]
    for record in sorted(candidates, key=lambda item: datetime.fromisoformat(item.retrieved_at), reverse=True):
        if record.source_url != f"https://clinicaltrials.gov/api/v2/studies/{nct}":
            raise ValueError(f"{nct} has a conflicting registry origin")
        raw = store.document(record.sha256_digest)
        if raw is None or hashlib.sha256(raw).hexdigest() != record.sha256_digest:
            raise ValueError(f"{nct} lacks matching registry bytes")
        payload = json.loads(raw)
        if source_event is None or summarize_registry(nct, payload)["sourceHash"] == source_event:
            break
    else:
        raise ValueError(f"{nct} lacks a verified registry capture matching the request")
    captured_at = datetime.fromisoformat(record.retrieved_at).astimezone(timezone.utc).isoformat()
    cleaned = runtime.sanitize(payload, nct, captured_at)
    published_at = cleaned["protocolSection"]["statusModule"]["lastUpdatePostDateStruct"]["date"]
    if published_at != record.document_date:
        raise ValueError(f"{nct} has conflicting registry revision dates")
    return {"nct_id": nct, "captured_at": captured_at, "published_at": published_at,
            "source_url": record.source_url, "raw_sha256": record.sha256_digest,
            "input_sha256": runtime.sha(cleaned), "document_json": runtime.packed(cleaned)}


def queued_events(report, members):
    if report.get("kind") != "FOCUS_NIGHTLY_PRIMARY_SOURCE_MONITOR_NOT_FDA_PREDICTIONS":
        raise ValueError("Expected an archived FOCUS source monitor report")
    events = {}
    expected_levels = list(range(7, 21))
    for row in report["extendedAssessmentQueue"]:
        nct = row["nct"]
        if (nct not in members or nct in events or row["levels"] != expected_levels
                or row.get("publish") is not False
                or row["status"] != "QUEUED_FOR_DEVELOPMENT_REASSESSMENT"):
            raise ValueError("Invalid local reassessment queue entry")
        events[nct] = row["sourceHash"]
    return events


def validate(source_db, result_db, queue_report=None):
    source_db, result_db = source_db.resolve(), result_db.resolve()
    if (result_db == source_db or result_db.is_relative_to(ROOT)
            or result_db.suffix not in {".db", ".sqlite", ".sqlite3"}):
        raise ValueError("Use a separate local SQLite file outside the repository for validation results")
    records = json.loads((ROOT / "new-platform/frontend/data/p3PostDataActive.json").read_text())["records"]
    members = {row["nct"] for row in records}
    if len(records) != 32 or len(members) != 32 or not all(runtime.NCT.fullmatch(nct) for nct in members):
        raise ValueError("Expected the exact 32-trial packaged FOCUS roster")
    source = EvidenceStore(source_db, read_only=True)
    events = ({nct: None for nct in members} if queue_report is None
              else queued_events(json.loads(queue_report.read_text()), members))
    snapshots = {nct: registry_snapshot(source, nct, source_event=events[nct]) for nct in sorted(events)}
    engine = create_engine(URL.create("sqlite", database=str(result_db)))
    counts = {level: Counter() for level in range(7, 21)}
    try:
        for nct, snapshot in snapshots.items():
            for level, tally in counts.items():
                request = runtime.RunInput(nct=nct, level=level, mode="CURRENT_EVIDENCE",
                                           contract="EXTENDED_7_20")
                run_id = runtime.create(engine, request, source_event=events[nct])
                runtime.execute(engine, run_id,
                                collector=lambda _: {**snapshot, "snapshot_id": str(uuid4())},
                                document_collector=lambda source, _: source)
                outcome = runtime.status(engine, nct, run_id)
                result = outcome["report"]
                if (outcome["status"] != "COMPLETED" or result is None or result["level"] != level
                        or result["nct"] != nct or result["fdaPrediction"]["outcome"] != "ABSTAIN"
                        or result["fdaPrediction"]["probability"] is not None
                        or result["score"]["value"] is not None):
                    raise ValueError(f"Unexpected Level {level} result for {nct}: {outcome['error']}")
                tally[result["evidenceStatus"]] += 1
    finally:
        engine.dispose()
    return {"cohortSize": len(members), "assessedTrials": len(events), "savedRuns": sum(sum(t.values()) for t in counts.values()),
            "mode": "CAPTURED_REGISTRY_ONLY", "scoredPredictions": 0,
            "levels": {key: dict(tally) for key, tally in counts.items()}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-db", type=Path, required=True)
    parser.add_argument("--results-db", type=Path, required=True)
    parser.add_argument("--queue-report", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.evidence_db, args.results_db, args.queue_report), sort_keys=True, indent=2))
