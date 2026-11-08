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


def collect(engine, *, storage_ready, require_postgres=True):
    """Live snapshot. If PostgreSQL is missing, do not read ephemeral SQLite."""
    out = {
        "schemaVersion": 1, "observedAt": utc_now(),
        "storage": {"state": "READY" if storage_ready and
                    (not require_postgres or engine.dialect.name=="postgresql")
                    else "BLOCKED",
                    "kind": engine.dialect.name,
                    "postgresRequired": bool(require_postgres)},
        "services": {}, "sourceSnapshots": {},
        "scans": {}, "research": {},
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
    except Exception as exc:
        LOG.warning("Medical application source map invalid type=%s", type(exc).__name__)
        out["sourceSnapshots"]["applications"] = {
            "state":"INVALID", "detail":"Packaged source-linked application identity map failed validation"
        }
    if out["storage"]["state"]!="READY":
        out["errors"].append("Persistent PostgreSQL is not connected or unavailable")
        for name in ("phase3Ingestion","nctStream"):
            out["scans"][name]={"state":"BLOCKED","detail":"Database telemetry unavailable"}
        out["research"]={"state":"BLOCKED","detail":"Database-backed research history unavailable"}
        return out
    try:
        tables=_tables(engine)
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
                    "latestRunAt":last,"completedIndependentReviews":0,
                    "probabilityForecastsValidated":False,
                    "certaintyReliabilityValidated":False,
                    "detail":"Recorded 12-stage source checks do not constitute 12 completed clinical reviews."}
            else:
                out["research"]={"state":"UNKNOWN","detail":"No medical research table"}
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
