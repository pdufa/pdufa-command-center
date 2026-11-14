"""Append-only research revision history and opt-in registry change detection.

This module never calculates an approval, CRL or review-delay probability.
It does not replace owner review or retrospective calibration; no outside approval is required.
Registry fingerprints alone cannot detect SEC, FDA or publication updates.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from sqlalchemy import text

LOG = logging.getLogger(__name__)
LEVEL_NAMES = (
    "CRL_HISTORY", "MULTIDISCIPLINARY_REVIEW", "STATISTICAL_FORENSICS",
    "MANUFACTURING_CMC", "REGULATORY_PRECEDENT", "CLINICAL_BENEFIT_RISK",
    "TRIAL_INTEGRITY", "SCIENTIFIC_CONTRADICTIONS", "FDA_COMMUNICATIONS",
    "REGULATORY_PATHWAY", "REVIEW_DELAY", "BACKTEST_CALIBRATION",
)
# Source-collection stages are LEADS, not verified fulfillment of a review domain.
RELATED_STAGES = (
    (10,), (4, 6, 7, 8), (1, 7), (9,), (10,),
    (1, 6, 8), (0, 7, 8), (3, 7), (2, 4), (0, 4),
    (4, 9, 10), (),
)
WATCH_INTERVAL_SECONDS = 6 * 60 * 60
_WATCH_STOP = threading.Event()
_WATCH_THREAD = None


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_prediction_revisions (
            run_id TEXT PRIMARY KEY REFERENCES medical_continuous_runs(run_id),
            nct_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
            source_digest TEXT NOT NULL, evidence_changed BOOLEAN NOT NULL,
            report TEXT NOT NULL, recorded_at TEXT NOT NULL,
            UNIQUE(nct_id,ordinal))"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_prediction_history_by_trial
            ON medical_prediction_revisions(nct_id,ordinal)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_registry_watch (
            nct_id TEXT PRIMARY KEY, evidence_digest TEXT NOT NULL,
            last_checked_at TEXT NOT NULL, last_triggered_at TEXT)"""))


def record_revision(connection, run_id, nct):
    """Must run in the SAME transaction as marking a source run complete."""
    previous_for_run = connection.execute(text(
        "SELECT run_id FROM medical_prediction_revisions WHERE run_id=:run"
    ), {"run":run_id}).first()
    if previous_for_run:
        return
    rows = list(connection.execute(text("""SELECT stage_index,state,document
        FROM medical_continuous_stages WHERE run_id=:run ORDER BY stage_index"""),
        {"run":run_id}).mappings())
    if [int(x["stage_index"]) for x in rows] != list(range(12)):
        raise ValueError("Cannot record a partial medical source-collection run")
    details = []
    for item in rows:
        doc = json.loads(item["document"])
        details.append({"stage":int(item["stage_index"]),"state":item["state"],"data":doc})
    evidence_dump = json.dumps(details, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(evidence_dump.encode("utf-8")).hexdigest()
    old = connection.execute(text("""SELECT ordinal,source_digest
        FROM medical_prediction_revisions WHERE nct_id=:nct
        ORDER BY ordinal DESC LIMIT 1"""), {"nct":nct}).mappings().first()
    ordinal = int(old["ordinal"])+1 if old else 1
    changed = old is None or old["source_digest"] != digest
    levels = []
    for i,name in enumerate(LEVEL_NAMES):
        selected = [details[k] for k in RELATED_STAGES[i]]
        recorded = sum(x["state"] == "SOURCE_RECORDED" for x in selected)
        levels.append({"number":i+1, "id":name,
            "reviewStatus":"OWNER_NOT_REVIEWED",
            "externalVerificationRequired":False,
            "sourceStagesRecorded":recorded,
            "sourceStagesChecked":len(selected),
            "recordDisposition":"SOURCE_LEADS_ONLY" if selected else "HISTORICAL_CALIBRATION_MISSING",
            "evidenceGap":"A source check is not a confirmed FDA/CMC review or statistical validation."})
    report = {"modelVersion":"advanced-failure-first-v1",
        "runId":run_id,"nct":nct,"sourceDigest":digest,
        "outcomes":[{"outcome":k,"status":"ABSTAIN","probability":None,
                     "reason":"Owner source review is not completed and prospectively frozen historical calibration is unavailable; no external signoff is required."}
            for k in ("APPROVAL","CRL","REVIEW_DELAY")],
        "certainty":{"status":"NOT_VALIDATED","rating":None},
        "reviewLevels":levels,
        "completedIndependentReviews":0,  # Legacy historical count, never an active assessment gate
        "completedOwnerReviews":0,
        "ownerReviewStatus":"OWNER_NOT_REVIEWED",
        "externalReviewerRequirements":0,
        "externalSignoffsRequired":0,
        "sourceCollectionStages":12,
        "calibrationReleasePermitted":False,
        "sourceType":"RECORDED_PUBLIC_SOURCE_CHECKS",
        "warning":"Revisions track evidence collection, not validated FDA probability or signed clinical decisions."}
    # Analyze Now is an optional report adapter over this same immutable run.
    # Retired scoring histories remain isolated from this owner-only research report.
    from .medical_on_demand import build_saved_analysis
    report["analyzeNow"]=build_saved_analysis(connection,run_id,nct,details)
    connection.execute(text("""INSERT INTO medical_prediction_revisions
        (run_id,nct_id,ordinal,source_digest,evidence_changed,report,recorded_at)
        VALUES(:run,:nct,:ordinal,:digest,:changed,:report,:time)"""),
        {"run":run_id,"nct":nct,"ordinal":ordinal,"digest":digest,
         "changed":changed,"report":json.dumps(report,allow_nan=False),"time":utcnow()})


def list_revisions(engine, nct):
    from . import medical_continuous as core
    core.check_nct(nct)
    with engine.connect() as c:
        rows = c.execute(text("""SELECT run_id,ordinal,source_digest,evidence_changed,
            report,recorded_at FROM medical_prediction_revisions
            WHERE nct_id=:nct ORDER BY ordinal DESC LIMIT 50"""),
            {"nct":nct}).mappings()
        out=[{"runId":x["run_id"],"ordinal":x["ordinal"],
              "evidenceChanged":bool(x["evidence_changed"]),
              "sourceDigest":x["source_digest"],"recordedAt":x["recorded_at"],
              "report":json.loads(x["report"])} for x in rows]
    return {"nct":nct,"revisions":out,"totalShown":len(out),
      "historyKind":"SOURCE_EVIDENCE_AND_ABSTENTION_HISTORY",
      "note":"History is immutable and trial-specific. The absence of numeric changes is not evidence of calibration."}


def registry_digest(study, nct):
    """Exact NCT and canonical source data, without network or local timestamps."""
    identity=study.get("protocolSection",{}).get("identificationModule",{}).get("nctId")
    if identity!=nct:
        raise ValueError("External registry response does not match exact requested NCT")
    content={
        "protocol":study.get("protocolSection",{}),
        "results":study.get("resultsSection",{}),
        "derived":study.get("derivedSection",{}),
    }
    return hashlib.sha256(json.dumps(content,sort_keys=True,separators=(",",":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def check_registry_updates_once(engine, *, fetch=None):
    """Compare full exact-ID registry observations; create new runs only on change.

    The first observation is a baseline, not evidence of a new change.
    Runs are not started merely by opening a dashboard.
    No network failure advances a fingerprint or clears an earlier concern.
    """
    from . import medical_continuous as core
    fetch = fetch or core.registry
    counts={"checked":0,"baselined":0,"changed":0,"queued":0,"unavailable":0,"activeDeferred":0}
    for nct in sorted(core.roster()):
        try:
            digest=registry_digest(fetch(nct),nct)
            counts["checked"]+=1
            with engine.begin() as c:
                stored=c.execute(text("SELECT evidence_digest FROM medical_registry_watch WHERE nct_id=:nct"),
                                 {"nct":nct}).scalar()
                if stored is None:
                    c.execute(text("""INSERT INTO medical_registry_watch
                        (nct_id,evidence_digest,last_checked_at,last_triggered_at)
                        VALUES(:nct,:sha,:time,NULL)"""),
                        {"nct":nct,"sha":digest,"time":utcnow()})
                    counts["baselined"]+=1
                    continue
                if stored==digest:
                    c.execute(text("UPDATE medical_registry_watch SET last_checked_at=:time WHERE nct_id=:nct"),
                              {"nct":nct,"time":utcnow()})
                    continue
                active=c.execute(text("""SELECT run_id FROM medical_continuous_runs
                    WHERE nct_id=:nct AND status IN ('PENDING','RUNNING') LIMIT 1"""),
                    {"nct":nct}).first()
                if active:
                    counts["activeDeferred"]+=1
                    continue
            # Create outside the earlier transaction, avoiding a DB lock and
            # preserving the old fingerprint if job creation fails.
            from .medical_on_demand import start_now,eligible_for_analysis
            if not eligible_for_analysis(nct):
                counts["activeDeferred"]+=1
                continue
            start_now(engine,nct,str(uuid.uuid4()),trigger="REGISTRY_CHANGE")
            with engine.begin() as c:
                c.execute(text("""UPDATE medical_registry_watch
                    SET evidence_digest=:sha,last_checked_at=:time,last_triggered_at=:time
                    WHERE nct_id=:nct AND evidence_digest=:previous"""),
                    {"sha":digest,"time":utcnow(),"nct":nct,"previous":stored})
            counts["changed"]+=1
            counts["queued"]+=1
        except Exception as exc:
            counts["unavailable"]+=1
            LOG.warning("Medical registry change monitor source unavailable nct=%s error_type=%s",
                        nct,type(exc).__name__)
    return counts


def start_watch(engine):
    """Explicitly opt-in once backend has persistent PostgreSQL storage."""
    global _WATCH_THREAD
    if os.getenv("PDUFA_MEDICAL_AUTO_WATCH","").strip().lower() not in ("1","true","yes"):
        return False
    if engine.dialect.name!="postgresql":
        LOG.error("PDUFA_MEDICAL_AUTO_WATCH_REQUIRES_POSTGRES")
        return False
    if _WATCH_THREAD is not None and _WATCH_THREAD.is_alive():
        return True
    _WATCH_STOP.clear()
    def loop():
        # First check on start, then at six-hour intervals; each NCT checked
        # separately so individual source outages cannot falsely reset others.
        while not _WATCH_STOP.is_set():
            try:
                check_registry_updates_once(engine)
                # Source changes and newly operational components share this
                # existing opt-in worker; no second polling service or scan.
                from .medical_on_demand import check_operational_component_changes
                check_operational_component_changes(engine)
                # The same durable medical worker handles exact-drug primary
                # FDA news leads. A missing feed never changes prediction state.
                try:
                    from .medical_official_news import check_once as check_fda_news
                    check_fda_news(engine)
                except Exception as news_exc:
                    LOG.warning("Official FDA news watch unavailable type=%s",type(news_exc).__name__)
            except Exception as exc:
                LOG.warning("medical registry/component watch skipped error_type=%s",type(exc).__name__)
            _WATCH_STOP.wait(WATCH_INTERVAL_SECONDS)
    _WATCH_THREAD=threading.Thread(target=loop,daemon=True,name="medical-registry-watch")
    _WATCH_THREAD.start()
    return True


def stop_watch():
    _WATCH_STOP.set()
