"""Independent per-trial medical source analysis using the one existing worker.

Only current evidence stages are analyzed. Historical scoring data remain in
read-only archive files and are not read by this module.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text, inspect

LOG = logging.getLogger(__name__)
STATUS = ("SOURCE_RECORDED", "LEADS_ONLY", "EVIDENCE_GAP", "SOURCE_UNAVAILABLE")
# Only source tools are operational; advanced reviews and forecast
# probabilities require independent clinical and historical validation.
OPERATIONAL_SOURCE_VERSION = "medical-continuous-source-12-v1"
REPORT_VERSION = "analyze-now-source-only-v2"
WATCH_GENERATION_KEY = "operational_components_v2"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def operational_fingerprint():
    """Monitor the independent operational evidence services only."""
    components = {
        "sourceWorker": OPERATIONAL_SOURCE_VERSION,
        "reportVersion": REPORT_VERSION,
        "generation": os.getenv("PDUFA_ANALYZE_COMPONENT_GENERATION", "v2"),
        "componentStatus": {
            "sourceCollection": "OPERATIONAL",
            "independentScientificReview": "NOT_COMPLETE",
            "FDA_prediction": "NOT_VALIDATED",
            "certainty": "NOT_VALIDATED",
            "advancedClinical": "NOT_OPERATIONAL"
        }
    }
    packed = json.dumps(components, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def initialize(engine):
    """Only add run provenance and operational fingerprint; reuse old run tables."""
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_analyze_requests (
            run_id TEXT PRIMARY KEY REFERENCES medical_continuous_runs(run_id),
            nct_id TEXT NOT NULL, trigger_kind TEXT NOT NULL, requested_at TEXT NOT NULL,
            source_sheet TEXT NOT NULL, component_fingerprint TEXT NOT NULL,
            initial_report TEXT)"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_analyze_by_nct
            ON medical_analyze_requests(nct_id,requested_at)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_component_watch (
            nct_id TEXT PRIMARY KEY, component_fingerprint TEXT NOT NULL,
            checked_at TEXT NOT NULL, triggered_at TEXT)"""))
    # Non-destructive forward migration for preview DBs that already created
    # the provenance table before immediate initial snapshots were introduced.
    columns={item["name"] for item in inspect(engine).get_columns("medical_analyze_requests")}
    if "initial_report" not in columns:
        with engine.begin() as c:
            c.execute(text("ALTER TABLE medical_analyze_requests ADD COLUMN initial_report TEXT"))


def register_request(connection, run_id, nct, trigger):
    """Only log source-run provenance; the medical worker remains the one executor."""
    if trigger not in ("MANUAL","REGISTRY_CHANGE","COMPONENT_CHANGE"):
        raise ValueError("Unknown analysis trigger")
    connection.execute(text("""INSERT INTO medical_analyze_requests
        (run_id,nct_id,trigger_kind,requested_at,source_sheet,component_fingerprint)
        VALUES(:run,:nct,:trigger,:now,'FOCUS',:version)
        ON CONFLICT(run_id) DO NOTHING"""), {
          "run":run_id,"nct":nct,"trigger":trigger,"now":utcnow(),
          "version":operational_fingerprint()})
    # Save the *initial*, uncalibrated report at request time even if a network
    # outage prevents a complete 12-stage research run.
    initial=build_saved_analysis(connection,run_id,nct,[])
    connection.execute(text("""UPDATE medical_analyze_requests
        SET initial_report=:report WHERE run_id=:run AND initial_report IS NULL"""),
        {"report":json.dumps(initial,allow_nan=False),"run":run_id})


def eligible_for_analysis(nct):
    """Only the original canary or a rigorously checked three-NCT cohort."""
    if nct == os.getenv("PDUFA_ANALYZE_NOW_CANARY_NCT", "NCT06081894"):
        return True
    if os.getenv("PDUFA_ANALYZE_NOW_ALL_ENABLED", "").lower() in ("1", "true", "yes"):
        return True
    from .medical_pilot_batch import allowed_ncts
    return nct in allowed_ncts()


def start_now(engine,nct,request_key,*,submit=True,trigger="MANUAL"):
    """One Analyze Now invocation. Reuses any active research job, never clones it."""
    from . import medical_continuous as core
    core.check_nct(nct)  # only currently eligible roster is startable
    if not eligible_for_analysis(nct):
        raise ValueError("Analyze Now wider rollout is gated until a verified database-backed canary")
    saved=core.create(engine,nct,request_key,submit=False)
    with engine.begin() as c:
        origin=c.execute(text("SELECT request_key FROM medical_continuous_runs WHERE run_id=:run"),
                         {"run":saved["runId"]}).scalar()
        register_request(c,saved["runId"],nct,trigger)
    if submit and origin==request_key and saved["status"]=="PENDING":
        core._POOL.submit(core.worker,engine,saved["runId"])
    return get_run(engine,nct,saved["runId"])


def _check_identity(nct):
    from .medical_continuous import NCT
    if not isinstance(nct,str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT required")


def get_run(engine,nct,run_id):
    """Read history by immutable NCT even after a move out of FOCUS."""
    from . import medical_continuous as core
    _check_identity(nct)
    with engine.connect() as c:
        record=c.execute(text("""SELECT run_id,status,stage_index,created_at,updated_at
            FROM medical_continuous_runs WHERE nct_id=:nct AND run_id=:run"""),
            {"nct":nct,"run":run_id}).mappings().first()
        if not record:
            raise LookupError("Analysis not recorded for exact NCT")
        stored=c.execute(text("SELECT report,recorded_at,ordinal FROM medical_prediction_revisions WHERE run_id=:run"),
                         {"run":run_id}).mappings().first()
        captured=c.execute(text("SELECT initial_report FROM medical_analyze_requests WHERE run_id=:run"),
                           {"run":run_id}).scalar()
        stages=c.execute(text("""SELECT stage_index,state,document,finished_at
            FROM medical_continuous_stages WHERE run_id=:run ORDER BY stage_index"""),
            {"run":run_id}).mappings().all()
    return {"nct":nct,"runId":record["run_id"],"status":record["status"],
            "startedAt":record["created_at"],"updatedAt":record["updated_at"],
            "completedStages":len(stages),"totalStages":len(core.STAGES),
            "analysis":json.loads(stored["report"]).get("analyzeNow") if stored else
                       json.loads(captured) if captured else None,
            "revision":int(stored["ordinal"]) if stored else None,
            "savedAt":stored["recorded_at"] if stored else None,
            "stages":[{"number":int(s["stage_index"])+1,"state":s["state"],
                       "finishedAt":s["finished_at"],
                       "title":core.STAGES[int(s["stage_index"])]} for s in stages],
            "note":"Analysis is a dated saved evidence snapshot; source collection is not FDA prediction validation."}


def latest(engine,nct):
    _check_identity(nct)
    with engine.connect() as c:
        run_id=c.execute(text("""SELECT run_id FROM medical_continuous_runs
            WHERE nct_id=:nct ORDER BY created_at DESC,run_id DESC LIMIT 1"""),
            {"nct":nct}).scalar()
    if not run_id:
        raise LookupError("No saved analysis for exact NCT")
    return get_run(engine,nct,run_id)


def history(engine,nct):
    """All runs, including interrupted/failed, stay keyed to exact NCT.

    Existing completed revisions are preserved. Pending analyses use their
    immutable initial snapshots; no analysis is fabricated on a GET.
    """
    _check_identity(nct)
    with engine.connect() as c:
        entries=list(c.execute(text("""SELECT r.run_id,r.status,r.created_at,
            a.requested_at,a.initial_report,
            p.ordinal,p.report,p.recorded_at,p.evidence_changed
            FROM medical_continuous_runs r
            LEFT JOIN medical_analyze_requests a ON a.run_id=r.run_id
            LEFT JOIN medical_prediction_revisions p ON p.run_id=r.run_id
            WHERE r.nct_id=:nct ORDER BY r.created_at DESC,r.run_id DESC LIMIT 100"""),
            {"nct":nct}).mappings())
    reports=[]
    for row in entries:
        completed=json.loads(row["report"]) if row["report"] else None
        initial=json.loads(row["initial_report"]) if row["initial_report"] else None
        reports.append({"runId":row["run_id"],"status":row["status"],
            "revision":int(row["ordinal"]) if row["ordinal"] is not None else None,
            "savedAt":row["recorded_at"] or row["requested_at"] or row["created_at"],
            "evidenceChanged":bool(row["evidence_changed"]) if row["report"] else False,
            "analysis":completed.get("analyzeNow") if completed else initial,
            "researchPrediction":completed.get("outcomes") if completed else None,
            "certainty":completed.get("certainty") if completed else None})
    return {"nct":nct,"locationIndependent":True,"historyKey":"EXACT_NCT",
            "total":len(reports),"records":reports}



def build_saved_analysis(connection,run_id,nct,details):
    """Materialize ALL available outcomes on completion within original run txn."""
    from . import medical_continuous as core
    with_request=connection.execute(text("""SELECT trigger_kind,requested_at,source_sheet,
         component_fingerprint FROM medical_analyze_requests WHERE run_id=:run"""),
         {"run":run_id}).mappings().first()
    known=core.roster().get(nct,{})
    source_urls=[]
    source_checks=[]
    gaps=[]
    recorded=0
    for item in details:
        data=item["data"] if isinstance(item["data"],dict) else {}
        index=int(item["stage"])
        state=item["state"]
        if state=="SOURCE_RECORDED":
            recorded+=1
        for field in ("source","issuerEvidenceUrl","trialResultsUrl"):
            url=data.get(field)
            if isinstance(url,str) and url.startswith("https://") and url not in source_urls:
                source_urls.append(url)
        gap=data.get("gap")
        if isinstance(gap,str) and gap.strip():
            gaps.append({"stage":index+1,"missing":gap})
        if state in ("EVIDENCE_GAP","SOURCE_UNAVAILABLE"):
            gaps.append({"stage":index+1,"missing":"Research stage "+str(index+1)+": "+state.lower().replace("_"," ")})
        source_checks.append({"stage":index+1,"title":core.STAGES[index],
            "status":state,"source":data.get("source") if isinstance(data.get("source"),str) else None,
            "evaluatedAt":None})
    gaps.extend([
        {"stage":None,"missing":"Independent FDA multidisciplinary, statistical and CMC signoff unavailable."},
        {"stage":None,"missing":"No calibrated FDA approval, CRL or review-delay probability model is operational."},
        {"stage":None,"missing":"No validated independent prediction-certainty rating is operational."},
    ])
    return {
        "schema":"ANALYZE_NOW_V1","savedAt":utcnow(),"nct":nct,
        "identity":{"ticker":known.get("ticker"),"company":known.get("company"),
                    "lastKnownSheet":"FOCUS","historyAnchoredTo":"EXACT_NCT"},
        "trigger":with_request["trigger_kind"] if with_request else "EXISTING_SOURCE_REANALYSIS",
        "requestRecordedAt":with_request["requested_at"] if with_request else None,
        "operationalComponentFingerprint":with_request["component_fingerprint"] if with_request else operational_fingerprint(),
        "scientificAssessment":{
            "status":"SOURCE_RESEARCH_ONLY",
            "stagesAttempted":len(details),
            "sourceRecordedStages":recorded,
            "sourceChecks":source_checks,
            "independentScientificSignoff":False,
            "explanation":"Public-source observations only; no independently completed multidisciplinary FDA review."},
        "fdaPredictions":[{"outcome":name,"status":"ABSTAIN","probability":None,
            "reason":"Historical calibration and current-cycle regulator evidence remain insufficient."}
            for name in ("APPROVAL","CRL","REVIEW_DELAY")],
        "certainty":{"status":"NOT_VALIDATED","rating":None,
            "reason":"No historical reliability sample or out-of-time prediction calibration is established."},
        "missingEvidence":gaps,
        "supportingSourceUrls":source_urls[:80],
        "componentReadiness":{
            "sourceCollection":"OPERATIONAL_SOURCE_CHECKS",
            "independentClinicalAnalysis":"NOT_COMPLETE",
            "advanced12Levels":"NOT_REQUIRED_FOR_INITIAL_RUN",
            "fdaPrediction":"NOT_VALIDATED",
            "certainty":"NOT_VALIDATED"},
        "warning":"This source report does not calculate clinical readiness scores, FDA probabilities, or forecast reliability; ABSTAIN is mandatory without validation."
    }


def check_operational_component_changes(engine, *,generation=None):
    """Opt-in automatic reanalysis only after a newly operational input differs.

    First observation establishes baseline; source changes are separately
    detected by medical_advanced_runtime's exact registry watcher.
    """
    from . import medical_continuous as core
    key=generation or operational_fingerprint()
    tally={"checked":0,"baselined":0,"changed":0,"queued":0,"deferred":0}
    for nct in sorted(core.roster()):
        if not eligible_for_analysis(nct):
            continue
        tally["checked"]+=1
        with engine.begin() as c:
            prior=c.execute(text("SELECT component_fingerprint FROM medical_component_watch WHERE nct_id=:nct"),
                            {"nct":nct}).scalar()
            if prior is None:
                c.execute(text("""INSERT INTO medical_component_watch
                    (nct_id,component_fingerprint,checked_at,triggered_at)
                    VALUES(:nct,:key,:now,NULL)"""),{"nct":nct,"key":key,"now":utcnow()})
                tally["baselined"]+=1
                continue
            if prior==key:
                continue
            active=c.execute(text("""SELECT run_id FROM medical_continuous_runs WHERE nct_id=:nct
                AND status IN ('PENDING','RUNNING') LIMIT 1"""),{"nct":nct}).scalar()
            if active:
                tally["deferred"]+=1
                continue
        start_now(engine,nct,str(uuid.uuid4()),trigger="COMPONENT_CHANGE")
        with engine.begin() as c:
            c.execute(text("""UPDATE medical_component_watch
                SET component_fingerprint=:key,checked_at=:now,triggered_at=:now
                WHERE nct_id=:nct AND component_fingerprint=:prior"""),
                {"key":key,"now":utcnow(),"nct":nct,"prior":prior})
        tally["changed"]+=1
        tally["queued"]+=1
    return tally


class AnalyzePayload(BaseModel):
    request_key:str=Field(min_length=36,max_length=36)


def install_routes(app, engine_provider, require_key, require_storage):
    router=APIRouter(prefix="/api/analyze-now",
                     dependencies=[Depends(require_key),Depends(require_storage)])
    def failure(exc):
        if isinstance(exc,LookupError):
            raise HTTPException(404,"No analysis recorded for this exact NCT")
        if isinstance(exc,ValueError):
            raise HTTPException(422,"Invalid analysis request or exact trial")
        LOG.error("Analyze Now error class=%s",type(exc).__name__)
        raise HTTPException(503,"Durable Analyze Now processing unavailable")

    @router.post("/{nct}/runs")
    def launch(nct:str,payload:AnalyzePayload):
        try:
            return start_now(engine_provider(),nct,payload.request_key)
        except Exception as exc:
            failure(exc)

    @router.get("/{nct}/latest")
    def read_latest(nct:str):
        try:
            return latest(engine_provider(),nct)
        except Exception as exc:
            failure(exc)

    @router.get("/{nct}/history")
    def read_history(nct:str):
        try:
            return history(engine_provider(),nct)
        except Exception as exc:
            failure(exc)

    app.include_router(router)
