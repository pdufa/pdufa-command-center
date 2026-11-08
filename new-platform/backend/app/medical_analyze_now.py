"""Analyze Now: one per-trial readout of already operational medical source stages.

Uses the existing medical_continuous worker. This module does NOT calculate RAAS
or FDA odds, restore surveys, or require unfinished advanced review levels.
Score and archived history mirrors are read-only and dated. Analysis results
are stored in PostgreSQL by exact NCT, surviving any spreadsheet move.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from sqlalchemy import text

ARCHIVE = Path(__file__).resolve().parent / "data" / "focus_legacy_score_snapshot.json"
VERSION = "ANALYZE_NOW_OPERATIONAL_SOURCE_V1"
TRIGGERS = {"MANUAL", "REGISTRY_EVIDENCE_UPDATE", "OPERATIONAL_COMPONENT_UPGRADE",
            "EXISTING_MEDICAL_RUN"}
OUTCOMES = ("APPROVAL", "CRL", "REVIEW_DELAY")
PHASES = ("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4")


def _utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _archive(nct):
    from .medical_continuous import check_nct
    check_nct(nct)
    obj = json.loads(ARCHIVE.read_text(encoding="utf-8"))
    if obj.get("schemaVersion") != 1 or obj.get("asOf") != "2026-11-07":
        raise ValueError("Read-only RAAS/clinical archive schema is not recognized")
    records = obj.get("records", [])
    matching = [r for r in records if r.get("nct") == nct]
    if len(matching) != 1:
        raise ValueError("Exact NCT archive entry missing or ambiguous")
    return matching[0]


def capability_signature(nct):
    """Per-NCT fingerprint; changes do not implicate other clinical programs."""
    from .medical_continuous import STAGES
    row = _archive(nct)
    # Only components actually implemented are represented; unreleased science
    # never changes this signature or triggers a fake recalibration.
    facts = {"version": VERSION, "sourceStages": list(STAGES),
             "historicalClinicalFive": row["clinicalFive"],
             "archivedRaas30": row["raas30"]}
    return hashlib.sha256(json.dumps(facts, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode("utf-8")).hexdigest()


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_analyze_now_reports (
            run_id TEXT PRIMARY KEY REFERENCES medical_continuous_runs(run_id),
            nct_id TEXT NOT NULL, trigger_reason TEXT NOT NULL,
            capability_digest TEXT NOT NULL, captured_at TEXT NOT NULL,
            initial_report TEXT NOT NULL, final_report TEXT, finalized_at TEXT)"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_analyze_now_by_nct
            ON medical_analyze_now_reports(nct_id,captured_at)"""))


def _source_links(value, limit=60):
    """Extract URL *leads*; never mark an issuer source FDA-verified."""
    found = set()
    def visit(obj, depth):
        if len(found) >= limit or depth > 8:
            return
        if isinstance(obj, str):
            if obj.startswith("https://") and len(obj) <= 1800 and all(ch not in obj for ch in "\n\r\t "):
                found.add(obj)
        elif isinstance(obj, list):
            for item in obj[:80]:
                visit(item, depth + 1)
        elif isinstance(obj, dict):
            for key, item in list(obj.items())[:100]:
                if isinstance(key, str) and (key.lower().endswith("url") or
                     key.lower() in ("source", "sourceurl", "results", "references",
                                     "evidence", "publications", "links", "articles")):
                    visit(item, depth + 1)
                elif isinstance(item, (list, dict)):
                    visit(item, depth + 1)
    visit(value, 0)
    return sorted(found)


def _build(connection, nct, run_id, *, status, trigger):
    from .medical_continuous import STAGES
    archived = _archive(nct)
    stage_rows = list(connection.execute(text("""SELECT stage_index,state,document,finished_at
        FROM medical_continuous_stages WHERE run_id=:run ORDER BY stage_index"""),
        {"run": run_id}).mappings())
    stages = []
    links = set(archived.get("sources", []))
    missing = []
    for s in stage_rows:
        doc = json.loads(s["document"])
        stages.append({"number": int(s["stage_index"]) + 1,
            "name": STAGES[int(s["stage_index"])], "status": s["state"],
            "finishedAt": s["finished_at"], "sourceLeads": _source_links(doc),
            "researchDetails": doc})
        links.update(_source_links(doc))
        if s["state"] in ("SOURCE_UNAVAILABLE", "EVIDENCE_GAP"):
            missing.append({"stage": int(s["stage_index"]) + 1,
                "requirement": "Resolve source-access or missing evidence; do not infer absence of approval blockers."})
    attempted = {int(s["stage_index"]) for s in stage_rows}
    for i, name in enumerate(STAGES):
        if i not in attempted:
            missing.append({"stage": i + 1,
                "requirement": "Not yet attempted: " + name})
    archived_raas = archived["raas30"]
    clinical = archived["clinicalFive"]
    if archived_raas["score"] is None:
        missing.append({"component": "RAAS_30", "requirement":
            "No independently completed 30-metric RAAS overall score exists for this exact NCT. Historical metric leads are not a zero score."})
    if clinical["score"] is None:
        missing.append({"component": "CLINICAL_FIVE", "requirement":
            "Fewer than five clinical research factors have dated source-backed grades."})
    missing.extend([
        {"component": "SCIENTIFIC_ADJUDICATION", "requirement":
            "Source leads are not complete independently reviewed statistical, efficacy, safety and CMC assessments."},
        {"component": "FDA_PREDICTIONS", "requirement":
            "Approval, CRL and review-delay models lack validated out-of-time historical calibration."},
        {"component": "CERTAINTY", "requirement":
            "No independently calibrated forecast reliability and uncertainty rating is available."},
    ])
    return {
        "schemaVersion": 1, "version": VERSION, "nct": nct, "runId": run_id,
        "trigger": trigger, "recordedAt": _utc(), "sourceSnapshotAsOf": "2026-11-07",
        "runStatus": status, "stageCount": len(STAGES),
        "stagesAttempted": len(stages),
        "completedIndependentMedicalReviews": 0,
        "score": {
            "raas": {"value": archived_raas["score"],
                     "status": "ARCHIVED_ONLY" if archived_raas["score"] is not None else "UNAVAILABLE",
                     "source": "READ_ONLY_LEGACY_RAAS_30", "version": archived_raas["version"],
                     "lastEventId": archived_raas["lastEventId"]},
            "clinicalFive": {"value": clinical["score"],
                "status": clinical["status"], "recordedAt": clinical["recordedAt"],
                "eventId": clinical["eventId"],
                "gradedFactors": clinical["graded"],
                "sourceType": "HISTORICAL_SOURCE_ACCEPTED_RESEARCH_NOT_FDA_PROBABILITY"}
        },
        "scientificAssessment": {
            "status": "SOURCE_COLLECTION_ONLY" if stages else "NOT_YET_ATTEMPTED",
            "independentlyValidated": False,
            "availableSourceStages": sum(s["status"] == "SOURCE_RECORDED" for s in stages),
            "stages": stages,
        },
        "predictions": [{"outcome": x, "status": "ABSTAIN", "probability": None,
            "reason": "Independent current-cycle scientific adjudication and historical calibration are not operational."}
            for x in OUTCOMES],
        "certainty": {"status": "NOT_VALIDATED", "rating": None,
            "reason": "Do not confuse source availability or historical clinical research grade with forecast reliability."},
        "supportingEvidence": [{"url": u, "status": "SOURCE_POINTER_NOT_INDEPENDENTLY_CERTIFIED"}
                               for u in sorted(x for x in links if isinstance(x, str) and x.startswith("https://"))[:100]],
        "missing": missing,
        "legacyHistory": {
            "raasEventIds": archived["priorEventIds"],
            "clinicalFiveEventIds": archived["archivedFiveEventIds"],
            "retainedAcrossSpreadsheetMoves": True, "identityKey": "EXACT_NCT"
        },
        "automation": {"sourceChanges": "CLINICALTRIALS_GOV_OPT_IN",
                       "componentUpgrades": "POSTGRES_MONITOR_OPT_IN",
                       "fdaSecPublications": "NOT_YET_MONITORED"},
        "note": "This report uses available source-collection stages and dated legacy research grades, independent of unfinished advanced analyses. It does not issue a new RAAS score, FDA approval probability or certainty rating."
    }


def capture_start(connection, run_id, nct, trigger="MANUAL"):
    if trigger not in TRIGGERS:
        raise ValueError("Unrecognized medical analysis trigger")
    existing = connection.execute(text(
        "SELECT run_id FROM medical_analyze_now_reports WHERE run_id=:id"
    ), {"id": run_id}).first()
    if existing:
        return
    report = _build(connection, nct, run_id, status="PENDING", trigger=trigger)
    connection.execute(text("""INSERT INTO medical_analyze_now_reports
        (run_id,nct_id,trigger_reason,capability_digest,captured_at,initial_report)
        VALUES(:run,:nct,:trigger,:capability,:at,:report)"""),
        {"run": run_id, "nct": nct, "trigger": trigger,
         "capability": capability_signature(nct), "at": report["recordedAt"],
         "report": json.dumps(report, allow_nan=False)})


def capture_finish(connection, run_id, nct, status):
    if status not in ("COMPLETE", "FAILED"):
        raise ValueError("Only terminal source collection is finalized")
    # Older runs are still eligible for history and must not be discarded.
    capture_start(connection, run_id, nct, "EXISTING_MEDICAL_RUN")
    prior = connection.execute(text(
        "SELECT final_report FROM medical_analyze_now_reports WHERE run_id=:id"
    ), {"id": run_id}).scalar()
    if prior is not None:
        return
    reason = connection.execute(text(
        "SELECT trigger_reason FROM medical_analyze_now_reports WHERE run_id=:id"
    ), {"id": run_id}).scalar_one()
    report = _build(connection, nct, run_id, status=status, trigger=reason)
    connection.execute(text("""UPDATE medical_analyze_now_reports
        SET final_report=:report,finalized_at=:at
        WHERE run_id=:run AND final_report IS NULL"""),
        {"run": run_id, "report": json.dumps(report, allow_nan=False),
         "at": report["recordedAt"]})


def history(engine, nct):
    from .medical_continuous import check_nct
    check_nct(nct)
    with engine.connect() as c:
        rows = list(c.execute(text("""SELECT a.run_id,a.trigger_reason,a.captured_at,
            a.finalized_at,a.initial_report,a.final_report,
            r.status AS current_status
            FROM medical_analyze_now_reports a
            JOIN medical_continuous_runs r ON a.run_id=r.run_id
            WHERE a.nct_id=:nct ORDER BY a.captured_at DESC,a.run_id DESC LIMIT 100"""),
            {"nct": nct}).mappings())
    return {"nct": nct, "identityKey": "EXACT_NCT", "history": [
       {"runId": row["run_id"], "trigger": row["trigger_reason"],
        "capturedAt": row["captured_at"], "finalizedAt": row["finalized_at"],
        "status": row["current_status"],
        "report": json.loads(row["final_report"] or row["initial_report"]),
        "initialReport": json.loads(row["initial_report"])}
       for row in rows],
       "archivedClinicalAndRaasHistoryAvailable": True,
       "sourceAsOf": "2026-11-07",
       "note": "Saved by exact NCT, regardless of FOCUS or other spreadsheet membership; results are not FDA probabilities."}


def check_operational_upgrades_once(engine):
    """Only previously analyzed NCTs, only when an *actual* operational input changed."""
    from . import medical_continuous as core
    counts = {"checked": 0, "changed": 0, "queued": 0, "activeDeferred": 0}
    if engine.dialect.name != "postgresql" or os.getenv(
        "PDUFA_ANALYZE_AUTO_UPGRADE", "").lower() not in ("1", "true", "yes"):
        return {"state": "DISABLED", **counts}
    for nct in sorted(core.roster()):
        with engine.connect() as c:
            latest = c.execute(text("""SELECT capability_digest FROM medical_analyze_now_reports
                WHERE nct_id=:nct ORDER BY captured_at DESC,run_id DESC LIMIT 1"""),
                {"nct": nct}).scalar()
            if latest is None:
                continue
            counts["checked"] += 1
            if latest == capability_signature(nct):
                continue
            active = c.execute(text("""SELECT run_id FROM medical_continuous_runs
                WHERE nct_id=:nct AND status IN ('PENDING','RUNNING') LIMIT 1"""),
                {"nct": nct}).first()
            if active:
                counts["activeDeferred"] += 1
                continue
        core.create(engine, nct, __import__("uuid").uuid4().__str__(),
                    trigger="OPERATIONAL_COMPONENT_UPGRADE")
        counts["changed"] += 1
        counts["queued"] += 1
    return {"state": "OBSERVED", **counts}
