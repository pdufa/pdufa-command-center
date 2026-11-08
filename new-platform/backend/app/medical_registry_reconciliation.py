"""Exact-NCT ClinicalTrials.gov phase and posted-result reconciliation.

Stage 4b: source AUTHENTICATION and freshness verification, not clinical or FDA
signoff. Never auto-write medical_assessment_phase_events or reviewer grades.
Live registry data is sponsor-submitted; no evidence of independent efficacy.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from . import medical_continuous as source
from . import medical_phase_matrix as phase_matrix
from . import medical_assessment_ledger as ledger

LOG = logging.getLogger(__name__)
NCT_RE = re.compile(r"^NCT[0-9]{8}$")
CAMPAIGN = re.compile(r"^[A-Za-z0-9_-]{8,72}$")
TRUE = {"true", "1", "yes"}
VERSION = "REGISTRY_RECONCILIATION_V1"
ALLOWED_PHASES = frozenset(("EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"))
SAFE_STATUSES = frozenset((
    "MATCHED_SINGLE_PHASE", "SOURCE_PHASE_DRIFT_REVIEW",
    "MULTIPHASE_REVIEW_REQUIRED", "NO_REGISTRY_PHASE_REVIEW",
))
LIMIT_OUTCOMES = 20


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short(s, limit=600):
    return s[:limit] if isinstance(s,str) else ""


def initialize(engine, *, test_only=False):
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("Registry reconciliation requires durable PostgreSQL")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_registry_reconciliation_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL REFERENCES medical_assessment_trial_roster(nct_id),
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            algorithm_version TEXT NOT NULL,
            registry_source_sha256 TEXT NOT NULL,
            saved_stage_sha256 TEXT NOT NULL,
            report_json TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            UNIQUE(nct_id,source_run_id,algorithm_version,registry_source_sha256,saved_stage_sha256))"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_registry_reconciliation_nct
            ON medical_registry_reconciliation_snapshots(nct_id,recorded_at)"""))


def _saved_identity(engine, nct):
    historical=ledger.trial_history(engine,nct)
    run=historical["sourceRunId"]
    with engine.connect() as c:
        row=c.execute(text("""SELECT s.document,r.status,
            (SELECT COUNT(*) FROM medical_continuous_stages
             WHERE run_id=:run) AS stage_count
            FROM medical_continuous_stages s
            JOIN medical_continuous_runs r ON r.run_id=s.run_id
            WHERE s.run_id=:run AND s.stage_index=0 AND r.nct_id=:nct"""),
            {"run":run,"nct":nct}).first()
    if not row or row[1]!="COMPLETE" or int(row[2])!=12:
        raise RuntimeError("Completed immutable 12-stage source run required")
    doc=json.loads(row[0])
    if doc.get("nct")!=nct or doc.get("source")!=f"https://clinicaltrials.gov/study/{nct}":
        raise RuntimeError("Saved source identity does not match original trial")
    phases=doc.get("phases",[])
    if not isinstance(phases,list) or any(not isinstance(x,str) for x in phases):
        raise RuntimeError("Saved source phases must be a list")
    return run,phases,hashlib.sha256(row[0].encode("utf-8")).hexdigest()


def build_report(engine, nct, primary_source=None):
    if not isinstance(nct,str) or not NCT_RE.fullmatch(nct):
        raise ValueError("Exact NCT identifier is required")
    source.check_nct(nct)
    run,older,old_digest=_saved_identity(engine,nct)
    live = source.registry(nct) if primary_source is None else primary_source
    protocol = live.get("protocolSection",{})
    identity=protocol.get("identificationModule",{})
    if identity.get("nctId")!=nct:
        raise ValueError("Live official registry identity must exactly match saved NCT")
    design=protocol.get("designModule",{})
    status=protocol.get("statusModule",{})
    outcomes=protocol.get("outcomesModule",{})
    sponsor=protocol.get("sponsorCollaboratorsModule",{})
    results=live.get("resultsSection",{}) or {}
    live_phases=design.get("phases",[])
    if not isinstance(live_phases,list) or any(x not in ALLOWED_PHASES for x in live_phases):
        raise ValueError("Unrecognized official phase vocabulary; do not guess")
    if len(live_phases)!=len(set(live_phases)):
        raise ValueError("Official registry cannot provide duplicate phases")
    if not live_phases:
        state="NO_REGISTRY_PHASE_REVIEW"
    elif len(live_phases)>1:
        state="MULTIPHASE_REVIEW_REQUIRED"
    elif set(live_phases)!=set(older):
        state="SOURCE_PHASE_DRIFT_REVIEW"
    else:
        state="MATCHED_SINGLE_PHASE"
    if state not in SAFE_STATUSES:
        raise RuntimeError("Registry reconciliation status is unknown")
    primary=outcomes.get("primaryOutcomes",[])
    if not isinstance(primary,list):
        raise ValueError("Unexpected official primary-outcome shape")
    posted_outcomes=results.get("outcomeMeasuresModule",{}).get("outcomeMeasures",[])
    if not isinstance(posted_outcomes,list):
        raise ValueError("Unexpected posted outcome shape")
    primary_posted=sum(
        1 for x in posted_outcomes if isinstance(x,dict) and
        (x.get("type")=="PRIMARY" or x.get("type")=="Primary")
    )
    if len(primary)>LIMIT_OUTCOMES:
        # A bounded projection must never silently discard primary measures.
        raise ValueError("More than 20 registered primary measures require manual review")
    original=url=f"https://clinicaltrials.gov/study/{nct}"
    # The primary outcome *definitions* and the actual posted results differ.
    primary_definitions=[{
        "measure":_short(x.get("measure"),450),
        "timeFrame":_short(x.get("timeFrame"),300),
        "description":_short(x.get("description"),650),
    } for x in primary if isinstance(x,dict)]
    last_update=status.get("studyFirstPostDateStruct",{})
    phase_rationale={
        "MATCHED_SINGLE_PHASE":"Saved registry phase agrees with the current exact-NCT record; human clinical review remains pending.",
        "SOURCE_PHASE_DRIFT_REVIEW":"Current registry phase differs from saved snapshot; reconcile version history before scientific review.",
        "MULTIPHASE_REVIEW_REQUIRED":"Registry labels multiple phases; do not force a single clinical current/last-completed phase.",
        "NO_REGISTRY_PHASE_REVIEW":"Exact-NCT official record contains no supported trial phase.",
    }[state]
    return {
        "schema":VERSION,"nct":nct,"sourceRunId":run,
        "registryUrl":original,
        "registryApiUrl":f"https://clinicaltrials.gov/api/v2/studies/{nct}",
        "sourceType":"OFFICIAL_REGISTRY_SPONSOR_SUBMITTED",
        "sourceHashSha256":_digest(live),
        "savedStageHashSha256":old_digest,
        "retrievedAt":_now(),
        "savedRegistryPhases":older,
        "currentRegistryPhases":live_phases,
        "phaseAgreement":state,
        "phaseAgreementExplanation":phase_rationale,
        "machineSourceIdentityVerified":True,
        "reviewerVerifiedCurrentPhase":False,
        "lastCompletedPhaseIndependentlyVerified":False,
        "phaseReassessmentNeeded":state!="MATCHED_SINGLE_PHASE",
        "title":_short(identity.get("briefTitle"),500),
        "sponsor":_short(sponsor.get("leadSponsor",{}).get("name"),240),
        "overallStatus":_short(status.get("overallStatus"),90),
        "lastUpdatePosted":_short((status.get("studyFirstPostDateStruct") or {}).get("date"),40),
        "latestRecordUpdatePosted":_short((status.get("lastUpdatePostDateStruct") or {}).get("date"),40),
        "primaryCompletion":status.get("primaryCompletionDateStruct"),
        "studyCompletion":status.get("completionDateStruct"),
        "currentPrimaryOutcomeDefinitions":primary_definitions,
        "registeredPrimaryOutcomeCount":len(primary),
        "resultsSectionPresent":bool(results),
        "registryPostedOutcomeMeasures":len(posted_outcomes),
        "registryPostedPrimaryOutcomeMeasures":primary_posted,
        "resultsInterpretation":"POSTED_SPONSOR_REPORTED_NOT_CLINICALLY_ADJUDICATED"
            if posted_outcomes else "NO_POSTED_RESULTS_IN_RECORD",
        "primarySourceChecks":{
            "registryIdentity":"MATCH",
            "savedRegistryPhase":"MATCH" if set(live_phases)==set(older) else "DIFFERS",
            "primaryOutcomeDefinitions":"PRESENT" if primary_definitions else "MISSING",
            "postedPrimaryOutcomeResults":"PRESENT_UNADJUDICATED" if primary_posted else "MISSING",
            "protocolAndSapIndependentlyVerified":False,
            "fullTextPeerReviewedReadoutVerified":False,
            "fdaReviewDocumentsVerified":False,
        },
        "scientificGradesWritten":0,"scientificSignoff":False,
        "fdaPredictions":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN","REVIEW_DELAY":"ABSTAIN"},
        "certainty":"NOT_VALIDATED",
        "note":"Exact primary-registry fact capture; primary completion is NOT a released clinical readout. "
               "Do not score efficacy, safety, statistical significance or FDA likelihood from this record.",
    }


def persist(engine,nct,*,live=None,test_only=False):
    if engine.dialect.name!="postgresql" and not test_only:
        raise RuntimeError("Registry fact snapshots require durable PostgreSQL")
    report=build_report(engine,nct,live)
    event_id=str(uuid.uuid4())
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_registry_reconciliation_snapshots
          (snapshot_id,nct_id,source_run_id,algorithm_version,registry_source_sha256,
           saved_stage_sha256,report_json,recorded_at)
          VALUES(:id,:nct,:run,:version,:source,:saved,:report,:stamp)
          ON CONFLICT(nct_id,source_run_id,algorithm_version,registry_source_sha256,
                      saved_stage_sha256) DO NOTHING"""),{
          "id":event_id,"nct":nct,"run":report["sourceRunId"],"version":VERSION,
          "source":report["sourceHashSha256"],"saved":report["savedStageHashSha256"],
          "report":json.dumps(report,sort_keys=True,separators=(",",":")),
          "stamp":_now(),
        })
    return latest(engine,nct)


def latest(engine,nct):
    source.check_nct(nct)
    with engine.connect() as c:
        row=c.execute(text("""SELECT snapshot_id,report_json,recorded_at
            FROM medical_registry_reconciliation_snapshots
            WHERE nct_id=:nct ORDER BY recorded_at DESC,snapshot_id DESC LIMIT 1"""),
            {"nct":nct}).mappings().first()
    if not row:
        raise LookupError("No saved registry reconciliation for this NCT")
    return {"snapshotId":row["snapshot_id"],"savedAt":row["recorded_at"],
            **json.loads(row["report_json"])}


def coverage(engine):
    from . import medical_continuous as core
    canonical=set(core.roster())
    with engine.connect() as c:
        rows=list(c.execute(text("""SELECT nct_id,COUNT(*) AS count
            FROM medical_registry_reconciliation_snapshots
            GROUP BY nct_id ORDER BY nct_id""")).mappings())
        state_rows=list(c.execute(text("""SELECT s.nct_id,s.report_json
            FROM medical_registry_reconciliation_snapshots s
            JOIN (SELECT nct_id,MAX(recorded_at) latest_at
                  FROM medical_registry_reconciliation_snapshots GROUP BY nct_id) t
              ON s.nct_id=t.nct_id AND s.recorded_at=t.latest_at""")).mappings())
    unique={x["nct_id"] for x in rows}
    status_counts={}
    for row in state_rows:
        state=json.loads(row["report_json"])["phaseAgreement"]
        status_counts[state]=status_counts.get(state,0)+1
    missing=sorted(canonical-unique)
    unexpected=sorted(unique-canonical)
    return {"status":"COMPLETE_REGISTRY_FACT_CAPTURE" if not missing and not unexpected else "IN_PROGRESS",
            "canonicalTrials":len(canonical),
            "savedNcts":len(unique&canonical),
            "missingNcts":missing,"unexpectedNcts":unexpected,
            "registryFactSnapshots":sum(int(x["count"]) for x in rows),
            "phaseAgreementCounts":status_counts,
            "humanVerifiedClinicalPhases":ledger.coverage(engine)["phaseVerifiedNcts"],
            "scientificSignoff":False,"fdaPrediction":"ABSTAIN","certainty":"NOT_VALIDATED"}


def _selection():
    if os.getenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_AUTORUN","").lower() not in TRUE:
        return None
    campaign=os.getenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_CAMPAIGN","")
    raw=os.getenv("PDUFA_MEDICAL_REGISTRY_RECONCILE_NCTS","")
    ncts=tuple(v.strip() for v in raw.split(","))
    if not CAMPAIGN.fullmatch(campaign) or not 1<=len(ncts)<=3 or len(set(ncts))!=len(ncts):
        raise ValueError("Registry reconciliation requires a named 1–3 unique-NCT campaign")
    from . import medical_continuous as core
    roster=core.roster()
    if any(nct not in roster for nct in ncts):
        raise ValueError("Every exact NCT must belong to the canonical FOCUS roster")
    if os.getenv("PDUFA_MEDICAL_BATCH_AUTORUN","").lower() in TRUE or os.getenv(
            "PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_AUTORUN","").lower() in TRUE:
        raise RuntimeError("Live registry reconciliation cannot overlap source collection")
    return campaign,ncts


def run_selected(engine, *, test_only=False, fetch=None):
    selection=_selection()
    if selection is None:
        return []
    if engine.dialect.name!="postgresql" and not test_only:
        raise RuntimeError("Live registry reconciliation requires durable PostgreSQL")
    campaign,ncts=selection
    # Fetch and validate all original source identities BEFORE any database write.
    originals={nct:(fetch(nct) if fetch else source.registry(nct)) for nct in ncts}
    for nct in ncts:
        build_report(engine,nct,originals[nct])
    result=[]
    for nct in ncts:
        saved=persist(engine,nct,live=originals[nct],test_only=test_only)
        if saved["nct"]!=nct or saved["certainty"]!="NOT_VALIDATED":
            raise RuntimeError("Saved exact-source registry readback failed")
        LOG.warning("PDUFA_MEDICAL_REGISTRY_RECONCILE_TRIAL status=PASS campaign=%s "
                    "nct=%s phases=%s phaseAgreement=%s registeredPrimary=%d "
                    "postedPrimary=%d scientificGrades=0 prediction=ABSTAIN",
                    campaign,nct,",".join(saved["currentRegistryPhases"]),
                    saved["phaseAgreement"],saved["registeredPrimaryOutcomeCount"],
                    saved["registryPostedPrimaryOutcomeMeasures"])
        result.append(saved)
    summary=coverage(engine)
    LOG.warning("PDUFA_MEDICAL_REGISTRY_RECONCILE status=COMPLETE campaign=%s "
                "completed=%d target=%d saved=%d/%d scientificSignoff=False "
                "prediction=ABSTAIN certainty=NOT_VALIDATED",campaign,len(result),len(ncts),
                summary["savedNcts"],summary["canonicalTrials"])
    return result


def install_routes(app,engine_provider,require_key,require_storage):
    router=APIRouter(prefix="/api/internal/medical-registry-reconciliation",
                     dependencies=[Depends(require_key),Depends(require_storage)])
    @router.get("/coverage")
    def get_coverage():
        return coverage(engine_provider())
    @router.get("/{nct}/latest")
    def get_latest(nct:str):
        try:
            return latest(engine_provider(),nct)
        except ValueError:
            raise HTTPException(422,"Exact FOCUS NCT is required")
        except LookupError:
            raise HTTPException(404,"No saved registry audit")
    app.include_router(router)
