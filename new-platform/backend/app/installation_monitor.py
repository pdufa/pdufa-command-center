"""Read-only installation telemetry with optional durable health alerts.

New monitoring runs alongside the existing POOL/FOCUS/medical workers; it
never starts scans, changes an analysis, assigns an FDA probability or modifies
the source spreadsheets. All counts are observed, not fabricated.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import hashlib
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from sqlalchemy import inspect, text

LOG = logging.getLogger(__name__)
_STOP = threading.Event()
_THREAD = None
INTERVAL_SECONDS = 300


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def configured() -> bool:
    return bool(os.getenv("PDUFA_TELEGRAM_BOT_TOKEN", "").strip()
                and os.getenv("PDUFA_TELEGRAM_CHAT_ID", "").strip())


def _tables(engine):
    return set(inspect(engine).get_table_names())


def _medical_installation(engine, tables, *, storage_ready):
    """Observe the existing assessment ledger without seeding or reviewing it.

    Task IDs are stable across polls. Source counts and revision counts are not
    method grades, and a completed assessment never implies clinical signoff.
    """
    definitions = {
        "VERIFIED": "The named task's acceptance condition is observed in this snapshot.",
        "ACTIVE": "Dependencies are observed; work remains on this task.",
        "BLOCKED": "A named dependency is unavailable or has not been validated.",
        "UNKNOWN": "The required observation is unavailable; no zero or completion is inferred.",
        "sourceFreshness": "Source collection dates identify saved snapshots, not current source validity. Original publication and update dates require source-specific review.",
        "evidenceExpiry": "No universal expiry or automatic grade renewal is assumed. Reverified phase events require fresh method review; current-phase grades alone do not prove source freshness.",
        "gapEvents": "Recorded gap events are history. Without a gap-resolution adjudication they cannot be counted as resolved or as distinct unresolved scientific questions.",
        "independence": "Recorded reviewer events are distinct from an independently authorized clinical signoff. Source collection and methodology positions never count as graded methods.",
    }
    out = {"state": "UNKNOWN", "counts": None, "tasks": [],
           "currentTaskId": None, "definitions": definitions,
           "fdaPredictions": {"APPROVAL": "ABSTAIN", "CRL": "ABSTAIN", "REVIEW_DELAY": "ABSTAIN"},
           "certainty": "NOT_VALIDATED", "clinicalSignoff": "NOT_VERIFIED"}
    required = {"medical_assessment_trial_roster", "medical_assessment_phase_events",
                "medical_assessment_review_events", "medical_assessment_gap_events",
                "medical_continuous_runs", "medical_continuous_stages"}
    if not storage_ready:
        out.update(state="BLOCKED", reason="Persistent PostgreSQL telemetry is unavailable")
        return out
    missing = sorted(required - tables)
    if missing:
        out.update(reason="Assessment ledger tables are not all available", missingTables=missing)
        return out
    from . import medical_assessment_ledger as ledger
    from . import medical_continuous as source
    from .medical_method_projection import project_trial_history
    try:
        coverage = ledger.coverage(engine)
        totals = {key: 0 for key in ("SCORED", "NOT_APPLICABLE", "RETRACTED",
                                    "STALE_PHASE", "UNREVIEWED", "VERIFY_PHASE")}
        complete_assessments = 0
        verified_trials = 0
        dates = []
        observed_ncts = 0
        for nct in sorted(source.roster()):
            try:
                history = ledger.trial_history(engine, nct)
            except LookupError:
                continue
            projected = project_trial_history(history)
            observed_ncts += 1
            verified_trials += projected["verifiedPhase"] is not None
            for key in totals:
                totals[key] += projected["counts"][key]
            complete_assessments += sum(a["status"] == "COMPLETE" for a in projected["assessments"])
            dates.append(history["sourceCompletedAt"])
        canonical = coverage["canonicalTrials"]
        potential = coverage["potentialMethodPositions"]
        # Unseeded trials have no ledger observation. They remain explicitly
        # unobserved rather than appearing as 800 reviewed or failed methods.
        unobserved = (canonical - observed_ncts) * ledger.ASSESSMENTS * ledger.METHODS
        pending = sum(totals[k] for k in ("RETRACTED", "STALE_PHASE", "UNREVIEWED", "VERIFY_PHASE"))
        counts = {"canonicalTrials": canonical, "observedTrialLedgers": observed_ncts,
                  "sourceCompleteTrials": coverage["sourceComplete"],
                  "sourceStages": coverage["sourceStageCount"],
                  "phaseVerifiedTrials": verified_trials,
                  "potentialMethodPositions": potential,
                  "recordedCurrentPhaseGrades": totals["SCORED"],
                  "excludedMethods": totals["NOT_APPLICABLE"],
                  "pendingObservedMethods": pending, "unobservedMethodPositions": unobserved,
                  "methodStates": totals, "completedAssessments": complete_assessments,
                  "historicalReviewEvents": coverage["reviewEvents"],
                  "recordedGapEvents": coverage["explicitGapEvents"],
                  "independentlySignedClinicalReviews": None}
        sources_ok = coverage["status"] == "READY_FOR_REVIEW"
        phases_ok = sources_ok and verified_trials == canonical
        methods_ok = phases_ok and pending == 0 and unobserved == 0
        def task(ident, title, status, completed, remaining, dependency, evidence):
            return {"id": ident, "title": title, "status": status,
                    "completed": completed, "remaining": remaining,
                    "dependency": dependency, "evidence": evidence}
        tasks = [
            task("medical.sources", "Attach completed original-source runs", "VERIFIED" if sources_ok else "ACTIVE",
                 coverage["sourceComplete"], canonical - coverage["sourceComplete"],
                 None if sources_ok else "Complete exact-NCT 12-stage source runs and preserve roster attachments",
                 "medical_assessment_trial_roster and medical_continuous_stages"),
            task("medical.phase-verification", "Verify the current phase",
                 "VERIFIED" if phases_ok else "ACTIVE" if sources_ok else "BLOCKED",
                 verified_trials, canonical - verified_trials,
                 None if phases_ok else "Named independent phase review of original registry evidence; prior completed phases need separate evidence",
                 "medical_assessment_phase_events (current phase only; previous completion not inferred)"),
            task("medical.prior-phase-review", "Verify previously completed phases", "UNKNOWN", None, None,
                 "Original completed-phase evidence and independent adjudication; current registry phase cannot establish prior completion",
                 "No completed-phase adjudication ledger is installed"),
            task("medical.method-review", "Review phase-prioritized scientific methods",
                 "VERIFIED" if methods_ok else "ACTIVE" if verified_trials else "BLOCKED",
                 totals["SCORED"], pending + unobserved,
                 None if methods_ok else "Verified phase and independent source-linked method review; exclusions are tracked separately",
                 "Current phase-event method projection; immutable revisions retained"),
            task("medical.clinical-review", "Obtain authorized independent clinical review", "BLOCKED", None, None,
                 "Authorized multidisciplinary review and an installed signoff ledger; method grades do not establish signoff",
                 "No clinical signoff ledger is installed"),
            task("medical.fda-forecast", "Validate separate approval, CRL and delay forecasts", "BLOCKED", None, None,
                 "Independent evidence assessment and outcome-specific historical calibration release gates",
                 "All three outcomes remain ABSTAIN"),
            task("medical.certainty", "Validate independent certainty", "BLOCKED", None, None,
                 "Independent out-of-sample reliability validation and authorized release",
                 "NOT_VALIDATED"),
        ]
        current = next((t for t in tasks if t["status"] == "ACTIVE"),
                       next((t for t in tasks if t["status"] != "VERIFIED"), None))
        out.update(state="OBSERVED", counts=counts, tasks=tasks,
                   currentTaskId=current["id"] if current else None,
                   taskCounts={state: sum(t["status"] == state for t in tasks)
                               for state in ("VERIFIED", "ACTIVE", "BLOCKED", "UNKNOWN")},
                   sourceCollectionDates={"oldest": min(dates) if dates else None,
                                          "newest": max(dates) if dates else None,
                                          "freshnessValidation": "NOT_ADJUDICATED"})
    except Exception as exc:
        LOG.warning("Medical installation telemetry unavailable type=%s", type(exc).__name__)
        out.update(state="UNKNOWN", reason="Assessment ledger could not be fully projected; no completion is inferred")
    return out


def collect(engine, *, storage_ready, require_postgres=True):
    """Live snapshot. If PostgreSQL is missing, do not read ephemeral SQLite."""
    out = {
        "schemaVersion": 1, "observedAt": utc_now(),
        "storage": {"state": "READY" if storage_ready and
                    (not require_postgres or engine.dialect.name=="postgresql")
                    else "BLOCKED",
                    "kind": engine.dialect.name,
                    "postgresRequired": bool(require_postgres)},
        "services": {}, "sourceSnapshots": {}, "analysisNow": {}, "trialHistories": {},
        "scans": {}, "research": {},
        "medicalInstallation": _medical_installation(engine, set(), storage_ready=False),
        "alerts": {"telegramConfigured": configured(),
                   "monitorWorkerEnabled": os.getenv("PDUFA_INSTALL_MONITOR_ENABLED","").lower()
                       in ("1","true","yes"), "lastDelivery": None},
        "errors": [], "coverage": {"sourceTypes": ["ClinicalTrials.gov"],
            "missing": ["FDA", "SEC EDGAR", "PubMed/peer-reviewed publications",
                        "company disclosures", "external production scan scheduler"]},
    }
    # Package-file evidence is independently checkable even with a blocked DB.
    # This is source identity/coverage verification, never FDA approval status.
    try:
        from .medical_continuous import application_roster_status
        out["sourceSnapshots"]["applications"] = application_roster_status()
    except ImportError:
        out["sourceSnapshots"]["applications"] = {
            "state":"UNKNOWN", "detail":"Independent medical application map is not installed in this backend"
        }
    except Exception as exc:
        LOG.warning("Medical application source map invalid type=%s", type(exc).__name__)
        out["sourceSnapshots"]["applications"] = {
            "state":"INVALID", "detail":"Packaged source-linked application identity map failed validation"
        }
    # Render supplies exact running Git SHA, distinct from a merely queued build.
    running_sha=os.getenv("RENDER_GIT_COMMIT","").strip().lower()
    out["services"]["backendDeployment"]={
        "gitSha":running_sha if len(running_sha)==40 and all(c in "0123456789abcdef" for c in running_sha) else None,
        "branch":os.getenv("RENDER_GIT_BRANCH") or None,
        "environment":"backend_runtime",
        "source":"RENDER_GIT_COMMIT_RUNTIME"
    }
    if out["storage"]["state"]!="READY":
        out["medicalInstallation"] = _medical_installation(engine, set(), storage_ready=False)
        out["errors"].append("Persistent PostgreSQL is not connected or unavailable")
        for name in ("phase3Ingestion","nctStream"):
            out["scans"][name]={"state":"BLOCKED","detail":"Database telemetry unavailable"}
        out["research"]={"state":"BLOCKED","detail":"Database-backed research history unavailable"}
        out["analysisNow"]={"state":"BLOCKED","pilotTrial":"NCT06081894",
            "pilotSaved":False,"allTrialsEnabled":False,
            "reason":"Persistent PostgreSQL is not configured or available"}
        return out
    try:
        tables=_tables(engine)
        out["medicalInstallation"] = _medical_installation(engine, tables, storage_ready=True)
        with engine.connect() as c:
            if "phase3_ingestion_state" in tables:
                row=c.execute(text("SELECT document FROM phase3_ingestion_state LIMIT 1")).scalar()
                doc=json.loads(row) if row else {}
                out["scans"]["phase3Ingestion"]={
                    "state":str(doc.get("state") or "UNKNOWN"),
                    "lastSuccessAt":doc.get("last_success_at"),
                    "lastAutomaticExecutionAt":doc.get("last_automatic_execution_at"),
                    "lastUpdatedAt":doc.get("last_updated"),
                    "recordsSeen":doc.get("records_seen"),
                    "recordsImported":doc.get("records_imported"),
                    "errorCode":doc.get("error_code"),
                    "detail":"Observed backend Phase 3 ingestion state; not proof of the external nightly PIPELINE scan."
                }
            else:
                out["scans"]["phase3Ingestion"]={"state":"UNKNOWN","detail":"No Phase 3 ingestion table"}
            if "nct_stream_runs" in tables:
                result=c.execute(text("""SELECT status,COUNT(*) AS total
                    FROM nct_stream_runs GROUP BY status""")).mappings()
                counts={r["status"]:int(r["total"]) for r in result}
                out["scans"]["nctStream"]={"state":"OBSERVED","counts":counts,
                    "totalRuns":sum(counts.values()),"failedRuns":counts.get("FAILED",0),
                    "detail":"Persisted NCT evidence-stream runs; source coverage may be incomplete."}
            else:
                out["scans"]["nctStream"]={"state":"UNKNOWN","detail":"No source stream table"}
            if "medical_continuous_runs" in tables:
                result=c.execute(text("""SELECT status,COUNT(*) AS total
                    FROM medical_continuous_runs GROUP BY status""")).mappings()
                counts={r["status"]:int(r["total"]) for r in result}
                last=c.execute(text("SELECT MAX(updated_at) FROM medical_continuous_runs")).scalar()
                revisions=int(c.execute(text("SELECT COUNT(*) FROM medical_prediction_revisions")).scalar() or 0) if "medical_prediction_revisions" in tables else 0
                stage_rows=int(c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar() or 0) if "medical_continuous_stages" in tables else 0
                changed_revisions=int(c.execute(text("SELECT COUNT(*) FROM medical_prediction_revisions WHERE ordinal>1 AND evidence_changed=TRUE")).scalar() or 0) if "medical_prediction_revisions" in tables else 0
                out["research"]={"state":"OBSERVED","runsByStatus":counts,
                    "finishedSourceRuns":counts.get("COMPLETE",0),
                    "failedSourceRuns":counts.get("FAILED",0),
                    "activeSourceRuns":counts.get("RUNNING",0)+counts.get("PENDING",0),
                    "savedSourceStages":stage_rows,"immutableRevisions":revisions,
                    "newSourceEvidenceRevisions":changed_revisions,
                    "latestRunAt":last,"completedIndependentReviews":None,
                    "probabilityForecastsValidated":False,
                    "certaintyReliabilityValidated":False,
                    "detail":"Recorded 12-stage source checks do not constitute 12 completed clinical reviews."}
            else:
                out["research"]={"state":"UNKNOWN","detail":"No medical research table"}
            if "medical_analyze_requests" in tables:
                pilot=os.getenv("PDUFA_ANALYZE_NOW_CANARY_NCT","NCT06081894")
                counts=c.execute(text("""SELECT COUNT(*) AS total,
                    SUM(CASE WHEN r.status='COMPLETE' THEN 1 ELSE 0 END) AS finished
                    FROM medical_analyze_requests a
                    JOIN medical_continuous_runs r ON r.run_id=a.run_id""")).mappings().first()
                recorded=c.execute(text("""SELECT r.run_id,r.updated_at,p.report
                    FROM medical_analyze_requests a
                    JOIN medical_continuous_runs r ON r.run_id=a.run_id
                    JOIN medical_prediction_revisions p ON p.run_id=r.run_id
                    WHERE a.nct_id=:nct AND r.status='COMPLETE'
                    ORDER BY p.ordinal DESC LIMIT 1"""),{"nct":pilot}).mappings().first()
                has_report=bool(recorded and isinstance(json.loads(recorded["report"]).get("analyzeNow"),dict))
                watch_count=int(c.execute(text("SELECT COUNT(*) FROM medical_component_watch")).scalar() or 0) if "medical_component_watch" in tables else 0
                out["analysisNow"]={"state":"OBSERVED","pilotTrial":pilot,
                    "pilotSaved":has_report,
                    "pilotRunId":recorded["run_id"] if has_report else None,
                    "pilotSavedAt":recorded["updated_at"] if has_report else None,
                    "totalRequested":int(counts["total"] or 0),
                    "completedSavedRuns":int(counts["finished"] or 0),
                    "allTrialsEnabled":os.getenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","").lower() in ("1","true","yes"),
                    "componentWatchBaselines":watch_count,
                    "autoRerunEnabled":os.getenv("PDUFA_MEDICAL_AUTO_WATCH","").lower() in ("1","true","yes"),
                    "detail":"Pilot is verified only if an exact-NCT completed run has a persisted Analyze Now report. Source completion does not validate FDA probabilities."}
            else:
                out["analysisNow"]={"state":"UNKNOWN","pilotSaved":False,
                    "detail":"Analyze Now request tables not initialized"}
            if "medical_registry_watch" in tables:
                stats=c.execute(text("""SELECT COUNT(*) AS total,
                    MAX(last_checked_at) AS checked,MAX(last_triggered_at) AS triggered
                    FROM medical_registry_watch""")).mappings().first()
                out["scans"]["registryWatch"]={"state":"OBSERVED",
                    "trackedNcts":int(stats["total"] or 0),"lastCheckedAt":stats["checked"],
                    "lastTriggeredAt":stats["triggered"],
                    "enabled":os.getenv("PDUFA_MEDICAL_AUTO_WATCH","").lower() in ("1","true","yes"),
                    "detail":"Only ClinicalTrials.gov change monitoring, not FDA/SEC/publications."}
            else:
                out["scans"]["registryWatch"]={"state":"UNKNOWN","enabled":False}
            # Read-only, bounded exact-NCT revision history for the dashboard.
            # A missing table remains UNKNOWN; no placeholder revision is created.
            if "medical_prediction_revisions" in tables:
                source_revisions=c.execute(text("""SELECT nct_id,run_id,ordinal,recorded_at,evidence_changed
                    FROM medical_prediction_revisions ORDER BY recorded_at DESC LIMIT 500""")).mappings()
                by_nct={}
                for row in source_revisions:
                    nct=str(row["nct_id"])
                    if not __import__("re").fullmatch(r"NCT[0-9]{8}",nct):
                        continue
                    item=by_nct.setdefault(nct,{"state":"OBSERVED","latestStatus":"UNKNOWN",
                        "sourceStages":None,"failedRuns":0,"revisions":[]})
                    if len(item["revisions"])<20:
                        item["revisions"].append({"runId":str(row["run_id"]),
                            "ordinal":int(row["ordinal"]), "recordedAt":str(row["recorded_at"]),
                            "evidenceChanged":bool(row["evidence_changed"])})
                if "medical_continuous_runs" in tables:
                    latest_runs=c.execute(text("""SELECT nct_id,status,updated_at FROM medical_continuous_runs
                        ORDER BY updated_at DESC LIMIT 600""")).mappings()
                    for row in latest_runs:
                        item=by_nct.get(str(row["nct_id"]))
                        if item:
                            if item["latestStatus"]=="UNKNOWN":
                                item["latestStatus"]=str(row["status"])
                            if row["status"]=="FAILED":
                                item["failedRuns"]+=1
                if "medical_continuous_stages" in tables and "medical_continuous_runs" in tables:
                    counts=c.execute(text("""SELECT r.nct_id,COUNT(*) AS stages
                        FROM medical_continuous_stages s
                        JOIN medical_continuous_runs r ON r.run_id=s.run_id
                        GROUP BY r.nct_id""")).mappings()
                    for row in counts:
                        item=by_nct.get(str(row["nct_id"]))
                        if item:
                            item["sourceStages"]=int(row["stages"])
                out["trialHistories"]=by_nct
            if "installation_monitor_alerts" in tables:
                last=c.execute(text("""SELECT kind,delivery_state,sent_at
                    FROM installation_monitor_alerts
                    ORDER BY created_at DESC LIMIT 1""")).mappings().first()
                if last:
                    out["alerts"]["lastDelivery"]={
                        "kind":last["kind"],"state":last["delivery_state"],"sentAt":last["sent_at"]}
    except Exception as exc:
        LOG.warning("Installation monitor database snapshot unavailable: type=%s",type(exc).__name__)
        out["errors"].append("Live telemetry query failed; completion cannot be verified")
        out["storage"]["state"]="DEGRADED"
    return out


def initialize(engine):
    """Persist only monitor notifications, never change existing scanner tables."""
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS installation_monitor_alerts (
            event_key TEXT PRIMARY KEY, kind TEXT NOT NULL, message TEXT NOT NULL,
            delivery_state TEXT NOT NULL, created_at TEXT NOT NULL,
            sent_at TEXT, last_attempt_at TEXT, attempts INTEGER NOT NULL DEFAULT 0)"""))


def _telegram_send(message):
    token=os.getenv("PDUFA_TELEGRAM_BOT_TOKEN","").strip()
    chat_id=os.getenv("PDUFA_TELEGRAM_CHAT_ID","").strip()
    if not token or not chat_id:
        return False
    data=json.dumps({"chat_id":chat_id,"text":message[:3600],
                    "disable_web_page_preview":True}).encode("utf-8")
    req=Request("https://api.telegram.org/bot"+token+"/sendMessage",
                data=data,headers={"Content-Type":"application/json"},method="POST")
    with urlopen(req,timeout=7) as response:
        body=response.read(4096)
        return response.status==200 and json.loads(body).get("ok") is True


def _queue_event(engine,kind,key,message):
    # Unique event identities prevent restart/repeated polling duplicates.
    with engine.begin() as c:
        c.execute(text("""INSERT INTO installation_monitor_alerts
            (event_key,kind,message,delivery_state,created_at)
            VALUES(:key,:kind,:msg,'PENDING',:at)
            ON CONFLICT(event_key) DO NOTHING"""),
            {"key":key,"kind":kind,"msg":message[:3500],"at":utc_now()})


def monitor_once(engine, *, storage_ready, require_postgres=True):
    """Observe, persist milestone/failure alerts, and attempt safe delivery.

    Does not generate installation successes from source-code presence or send
    anything if storage is unavailable. Telegram delivery is opt-in.
    """
    report=collect(engine,storage_ready=storage_ready,require_postgres=require_postgres)
    if report["storage"]["state"]!="READY":
        return report
    initialize(engine)
    _queue_event(engine,"MILESTONE","first-persistent-monitor-ready",
                 "PDUFA installation health: isolated PostgreSQL monitor is connected and has returned a live source-status snapshot. This does not certify FDA forecasts.")
    runtime_sha=report.get("services",{}).get("backendDeployment",{}).get("gitSha")
    if runtime_sha:
        _queue_event(engine,"MILESTONE","backend-deployed:"+runtime_sha,
                     "PDUFA isolated medical backend is running commit "+runtime_sha[:12]+
                     " with PostgreSQL confirmed ready. This does not authorize clinical predictions.")
    if report.get("analysisNow",{}).get("pilotSaved"):
        _queue_event(engine,"MILESTONE","analyze-now-pilot-saved",
          "PDUFA Analyze Now canary: one exact-NCT analysis was saved with source checks, source gaps, separate ABSTAIN outcomes and unvalidated certainty. Wider rollout still requires operator verification.")
    medical=report["research"]
    if medical.get("finishedSourceRuns",0)>0:
        _queue_event(engine,"MILESTONE","medical-first-complete",
                     "PDUFA medical research: first 12-stage source collection completed. FDA forecasts still ABSTAIN.")
    if report["scans"].get("registryWatch",{}).get("lastCheckedAt"):
        _queue_event(engine,"MILESTONE","registry-first-check",
                     "PDUFA: first registry evidence-change baseline recorded. FDA/SEC/publication monitoring is not enabled.")
    ingest=report["scans"].get("phase3Ingestion",{})
    if str(ingest.get("state","")).upper() in ("FAILED","ERROR"):
        key="phase3-failure:"+str(ingest.get("lastUpdatedAt") or "unknown")
        _queue_event(engine,"FAILURE",key,
                     "PDUFA: Phase 3 ingestion reports a failure; inspect the backend ingestion status.")
    count=report["research"].get("failedSourceRuns",0)
    if count>0:
        # No repeated alerts on every poll. A new failure count creates a new event.
        _queue_event(engine,"FAILURE","medical-failed-count:"+str(count),
                     "PDUFA: medical source collection has "+str(count)+" failed runs; inspect run status.")
    # A second or later immutable revision can document changed source
    # observations. This event is not described as a validated FDA forecast.
    changed=[]
    if "medical_prediction_revisions" in _tables(engine):
        with engine.connect() as c:
            changed=list(c.execute(text("""SELECT run_id,nct_id,ordinal
                FROM medical_prediction_revisions
                WHERE ordinal>1 AND evidence_changed=TRUE
                ORDER BY recorded_at DESC LIMIT 20""")).mappings())
    for row in changed:
        _queue_event(engine,"EVIDENCE_UPDATE","medical-evidence:"+row["run_id"],
            "PDUFA medical evidence changed for "+row["nct_id"]+
            " (research revision "+str(row["ordinal"])+
            "). Source-digest change requires scientific review; FDA predictions remain evidence-gated.")
    if not configured():
        return report
    cutoff=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
    with engine.connect() as c:
        pending=list(c.execute(text("""SELECT event_key,message,attempts
            FROM installation_monitor_alerts
            WHERE delivery_state!='SENT'
            AND (last_attempt_at IS NULL OR last_attempt_at<:cutoff)
            ORDER BY created_at LIMIT 5"""),{"cutoff":cutoff}).mappings())
    for item in pending:
        success=False
        try:
            success=_telegram_send(item["message"])
        except Exception as exc:
            LOG.warning("PDUFA Telegram delivery failure type=%s",type(exc).__name__)
        with engine.begin() as c:
            c.execute(text("""UPDATE installation_monitor_alerts
                SET delivery_state=:state,
                    sent_at=CASE WHEN :state='SENT' THEN :now ELSE sent_at END,
                    last_attempt_at=:now,attempts=attempts+1
                WHERE event_key=:key AND delivery_state!='SENT'"""),
                {"state":"SENT" if success else "FAILED","now":utc_now(),
                 "key":item["event_key"]})
    return collect(engine,storage_ready=True,require_postgres=True)


def start(engine, *, ready_provider):
    global _THREAD
    if os.getenv("PDUFA_INSTALL_MONITOR_ENABLED","").lower() not in ("1","true","yes"):
        return False
    if engine.dialect.name!="postgresql":
        LOG.warning("PDUFA_INSTALL_MONITOR_NEEDS_PERSISTENT_POSTGRES")
        return False
    if _THREAD is not None and _THREAD.is_alive():
        return True
    _STOP.clear()
    def loop():
        while not _STOP.is_set():
            try:
                monitor_once(engine,storage_ready=bool(ready_provider()))
            except Exception as exc:
                LOG.warning("PDUFA installation monitor poll error type=%s",type(exc).__name__)
            _STOP.wait(INTERVAL_SECONDS)
    _THREAD=threading.Thread(target=loop,name="pdufa-install-health",daemon=True)
    _THREAD.start()
    return True


def stop():
    _STOP.set()
