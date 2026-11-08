"""Analyze Now: independent, immediately available source analysis plus optional historical RAAS context.

Reuses the existing 12-stage durable worker. No duplicate medical pipeline, no
dependency on RAAS or surveys for research completion, and no invented score,
FDA probability or reliability percentage. Trial history is keyed by exact NCT,
not by current spreadsheet membership.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

LOG = logging.getLogger(__name__)
LEGACY = Path(__file__).resolve().parent / "data" / "focus_legacy_score_snapshot.json"
STATUS = ("SOURCE_RECORDED", "LEADS_ONLY", "EVIDENCE_GAP", "SOURCE_UNAVAILABLE")
# These are explicitly OPERATIONAL component versions; unfinished 12 advanced
# clinical levels and uncalibrated forecast models are never part of this set.
OPERATIONAL_SOURCE_VERSION = "medical-continuous-source-12-v1"
REPORT_VERSION = "analyze-now-v1"
WATCH_GENERATION_KEY = "operational_components_v1"


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def optional_legacy(nct):
    """Pure read-only import of existing historical RAAS/five-factor evidence.

    If the optional archive isn't present, the medical engine still operates.
    A five-factor clinical research rating is NOT the full 30-metric RAAS score.
    """
    from .medical_continuous import NCT
    if not NCT.fullmatch(str(nct)):
        raise ValueError("Exact NCT required")
    try:
        data=json.loads(LEGACY.read_text(encoding="utf-8"))
        if data.get("schemaVersion")!=1 or data.get("scope")!="OPTIONAL_READ_ONLY_LEGACY_RAAS_MIRROR":
            raise ValueError("Unrecognized legacy archive")
        item=next((x for x in data.get("records",[]) if x.get("nct")==nct),None)
        if not item:
            return {"status":"NOT_AVAILABLE","raasOverall":None,"clinicalFive":None,
                    "sources":[],"sourceAsOf":None}
        raas=item.get("raas30",{})
        clinical=item.get("clinicalFive",{})
        numeric=clinical.get("score") if isinstance(clinical.get("score"),(int,float)) else None
        graded=clinical.get("graded",[])
        verified_grades=isinstance(graded,list) and len(graded)==5 and all(
            isinstance(x,dict) and x.get("metricId") and
            (x.get("score") is None or isinstance(x.get("score"),(int,float)))
            for x in graded)
        valid_five=(numeric is not None and verified_grades and
                    clinical.get("scoredFactors")==5 and 0<=numeric<=100)
        raas30=raas.get("score")
        if not isinstance(raas30,(int,float)) or not 0<=raas30<=100:
            raas30=None
        return {
            "status":"ARCHIVED_READ_ONLY","raasOverall":raas30,
            "raasScoreKind":raas.get("status","UNSCORED"),
            "raasVersion":raas.get("version"),
            "clinicalFive":numeric if valid_five else None,
            "clinicalFiveStatus":"SOURCE_ACCEPTED_RESEARCH_FIVE_FACTORS" if valid_five else
                "NOT_ALL_FIVE_FACTORS_SCORED",
            "clinicalScoredFactors":sum(isinstance(x.get("score"),(int,float)) for x in graded) if verified_grades else 0,
            "clinicalFactors":[{"id":x["metricId"],"grade":x["score"],"sourceUrl":x.get("sourceUrl")}
                               for x in graded] if verified_grades else [],
            "clinicalEventId":clinical.get("eventId"),
            "clinicalRecordedAt":clinical.get("recordedAt"),
            "sources":[u for u in item.get("sources",[]) if isinstance(u,str) and u.startswith("https://")][:12],
            "sourceAsOf":data.get("asOf"),
            "historicalRaasEventIds":item.get("priorEventIds",[]),
            "historicalFiveFactorEventIds":item.get("archivedFiveEventIds",[]),
            "disclaimer":"Read-only preserved research grade, NOT independently FDA-calibrated approval probability or complete 30-metric RAAS."
        }
    except (OSError,ValueError,TypeError,KeyError,AttributeError):
        return {"status":"ARCHIVE_UNAVAILABLE","raasOverall":None,"clinicalFive":None,
                "sources":[],"sourceAsOf":None}


def operational_fingerprint():
    """Changes when enabled source tools or the optional evidence archive change.

    New advanced modules are not considered operational merely by being defined.
    Deployment of an explicitly configured component generation changes the
    fingerprint; an unchanged deployment does not trigger repeated work.
    """
    try:
        digest=hashlib.sha256(LEGACY.read_bytes()).hexdigest()
    except OSError:
        digest="unavailable"
    components={"sourceWorker":OPERATIONAL_SOURCE_VERSION,
                "optionalHistoricalRaas":digest,
                "generation":os.getenv("PDUFA_ANALYZE_COMPONENT_GENERATION","v1"),
                "componentStatus":{"sourceCollection":"OPERATIONAL",
                    "historicalRaas":"OPTIONAL_READ_ONLY",
                    "FDA_prediction":"NOT_OPERATIONAL",
                    "certainty":"NOT_OPERATIONAL",
                    "advancedClinical":"NOT_OPERATIONAL"}}
    packed=json.dumps(components,sort_keys=True,separators=(",",":"))
    return hashlib.sha256(packed.encode("utf-8")).hexdigest()


def initialize(engine):
    """Only add run provenance and operational fingerprint; reuse old run tables."""
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_analyze_requests (
            run_id TEXT PRIMARY KEY REFERENCES medical_continuous_runs(run_id),
            nct_id TEXT NOT NULL, trigger_kind TEXT NOT NULL, requested_at TEXT NOT NULL,
            source_sheet TEXT NOT NULL, component_fingerprint TEXT NOT NULL)"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_analyze_by_nct
            ON medical_analyze_requests(nct_id,requested_at)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_component_watch (
            nct_id TEXT PRIMARY KEY, component_fingerprint TEXT NOT NULL,
            checked_at TEXT NOT NULL, triggered_at TEXT)"""))


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


def start_now(engine,nct,request_key,*,submit=True,trigger="MANUAL"):
    """One Analyze Now invocation. Reuses any active research job, never clones it."""
    from . import medical_continuous as core
    core.check_nct(nct)  # only currently eligible roster is startable
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
        stages=c.execute(text("""SELECT stage_index,state,document,finished_at
            FROM medical_continuous_stages WHERE run_id=:run ORDER BY stage_index"""),
            {"run":run_id}).mappings().all()
    return {"nct":nct,"runId":record["run_id"],"status":record["status"],
            "startedAt":record["created_at"],"updatedAt":record["updated_at"],
            "completedStages":len(stages),"totalStages":len(core.STAGES),
            "analysis":json.loads(stored["report"]).get("analyzeNow") if stored else None,
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
    """Archive is independent of current FOCUS membership or spreadsheet location."""
    _check_identity(nct)
    with engine.connect() as c:
        entries=c.execute(text("""SELECT run_id,ordinal,report,recorded_at,evidence_changed
            FROM medical_prediction_revisions WHERE nct_id=:nct
            ORDER BY ordinal DESC"""),{"nct":nct}).mappings().all()
    return {"nct":nct,"locationIndependent":True,"historyKey":"EXACT_NCT",
            "total":len(entries),
            "records":[{"runId":x["run_id"],"revision":int(x["ordinal"]),
                        "savedAt":x["recorded_at"],"evidenceChanged":bool(x["evidence_changed"]),
                        "analysis":json.loads(x["report"]).get("analyzeNow"),
                        "researchPrediction":json.loads(x["report"]).get("outcomes"),
                        "certainty":json.loads(x["report"]).get("certainty")}
                       for x in entries]}


def build_saved_analysis(connection,run_id,nct,details):
    """Materialize ALL available outcomes on completion within original run txn."""
    from . import medical_continuous as core
    with_request=connection.execute(text("""SELECT trigger_kind,requested_at,source_sheet,
         component_fingerprint FROM medical_analyze_requests WHERE run_id=:run"""),
         {"run":run_id}).mappings().first()
    known=core.roster().get(nct,{})
    optional=optional_legacy(nct)
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
    if optional["raasOverall"] is None:
        gaps.append({"stage":None,"missing":"A validated full 30-metric RAAS score was not available in the preserved exact-NCT archive."})
    if optional["clinicalFive"] is None:
        gaps.append({"stage":None,"missing":"A complete five-factor scientific research score was not available; partial grades remain research leads."})
    gaps.extend([
        {"stage":None,"missing":"Independent FDA multidisciplinary, statistical and CMC signoff unavailable."},
        {"stage":None,"missing":"No calibrated FDA approval, CRL or review-delay probability model is operational."},
        {"stage":None,"missing":"No validated independent prediction-certainty rating is operational."},
    ])
    for url in optional["sources"]:
        if url not in source_urls:
            source_urls.append(url)
    return {
        "schema":"ANALYZE_NOW_V1","savedAt":utcnow(),"nct":nct,
        "identity":{"ticker":known.get("ticker"),"company":known.get("company"),
                    "lastKnownSheet":"FOCUS","historyAnchoredTo":"EXACT_NCT"},
        "trigger":with_request["trigger_kind"] if with_request else "EXISTING_SOURCE_REANALYSIS",
        "requestRecordedAt":with_request["requested_at"] if with_request else None,
        "operationalComponentFingerprint":with_request["component_fingerprint"] if with_request else operational_fingerprint(),
        "scores":{"raasOverallScore":optional["raasOverall"],
                  "raasStatus":optional.get("raasScoreKind","UNSCORED"),
                  "raasVersion":optional.get("raasVersion"),
                  "scientificFiveFactorScore":optional["clinicalFive"],
                  "scientificFiveFactorStatus":optional.get("clinicalFiveStatus"),
                  "scientificFiveFactorsGraded":optional.get("clinicalScoredFactors",0),
                  "scientificFactors":optional.get("clinicalFactors",[]),
                  "sourceArchiveAsOf":optional.get("sourceAsOf"),
                  "sourceEventId":optional.get("clinicalEventId"),
                  "historicalRaasEventIds":optional.get("historicalRaasEventIds",[]),
                  "historicalFiveFactorEventIds":optional.get("historicalFiveFactorEventIds",[])},
        "scientificAssessment":{
            "status":"SOURCE_RESEARCH_ONLY",
            "stagesAttempted":len(details),
            "sourceRecordedStages":recorded,
            "sourceChecks":source_checks,
            "independentScientificSignoff":False,
            "explanation":"Public-source observations and optional historical provisional clinical grades, not a completed new multidisciplinary FDA review."},
        "fdaPredictions":[{"outcome":name,"status":"ABSTAIN","probability":None,
            "reason":"Historical calibration and current-cycle regulator evidence remain insufficient."}
            for name in ("APPROVAL","CRL","REVIEW_DELAY")],
        "certainty":{"status":"NOT_VALIDATED","rating":None,
            "reason":"No historical reliability sample or out-of-time prediction calibration is established."},
        "missingEvidence":gaps,
        "supportingSourceUrls":source_urls[:80],
        "componentReadiness":{
            "sourceCollection":"OPERATIONAL_SOURCE_CHECKS",
            "legacyRaas":"OPTIONAL_ARCHIVED_RESEARCH",
            "independentClinicalAnalysis":"NOT_COMPLETE",
            "advanced12Levels":"NOT_REQUIRED_FOR_INITIAL_RUN",
            "fdaPrediction":"NOT_VALIDATED",
            "certainty":"NOT_VALIDATED"},
        "warning":"Never substitute a five-factor historical research score for full RAAS or interpret ABSTAIN as a numeric approval forecast."
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
