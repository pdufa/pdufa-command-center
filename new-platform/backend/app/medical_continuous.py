"""Persistent, source-first sequential medical evidence collection.

This service runs after an explicit operator POST, continues independently of the browser,
records each stage in the database, and resumes unfinished runs after service restart.
It records evidence leads and source observations, NOT an FDA or physician decision.
No legacy scoring, survey inputs, POOL/FOCUS writes, or approval probability.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

LOG = logging.getLogger(__name__)
NCT = re.compile(r"NCT\d{8}\Z")
RUN = re.compile(r"[0-9a-f-]{36}\Z")
STAGES = (
    "Trial identity and phase",
    "ClinicalTrials.gov results",
    "Sponsor disclosures and SEC evidence",
    "Published medical research",
    "FDA regulatory and designation evidence",
    "Disease biology and medical context",
    "Clinical subspecialty evidence",
    "Trial design and statistics",
    "Safety and benefit-risk evidence",
    "Manufacturing, CMC and inspections",
    "Historical FDA precedents",
    "Independent evidence-readiness report",
)
END = {"COMPLETE", "FAILED", "STOPPED"}
STAGE_DONE = {"SOURCE_RECORDED", "LEADS_ONLY", "EVIDENCE_GAP", "SOURCE_UNAVAILABLE"}
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="medical-stages")
_IN_PROCESS = threading.RLock()
ROOT = Path(__file__).resolve().parents[2]
FOCUS = Path(__file__).resolve().parent / "data" / "focus_snapshot.json"
APPLICATIONS = Path(__file__).resolve().parent / "data" / "focus_application_snapshot.json"


def now():
    return datetime.now(timezone.utc).isoformat()


def roster():
    data = json.loads(FOCUS.read_text(encoding="utf-8"))
    rows = data.get("records", [])
    if not 1 <= len(rows) <= 200:
        raise ValueError("FOCUS source roster unavailable")
    return {r["nct"]: r for r in rows if NCT.fullmatch(str(r.get("nct", "")))}


def check_nct(nct):
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("An exact NCT identifier is required")
    item = roster().get(nct)
    if item is None:
        raise ValueError("NCT not present on the dated FOCUS roster")
    return item


def initialize(engine):
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_continuous_runs (
            run_id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
            nct_id TEXT NOT NULL, status TEXT NOT NULL, stage_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, stop_requested BOOLEAN NOT NULL DEFAULT FALSE)"""))
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_continuous_stages (
            run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            stage_index INTEGER NOT NULL, state TEXT NOT NULL, document TEXT NOT NULL,
            finished_at TEXT NOT NULL, PRIMARY KEY(run_id,stage_index))"""))
        c.execute(text("CREATE INDEX IF NOT EXISTS medical_continuous_by_nct ON medical_continuous_runs(nct_id,created_at)"))
        c.execute(text("""CREATE UNIQUE INDEX IF NOT EXISTS medical_continuous_one_active
            ON medical_continuous_runs(nct_id) WHERE status IN ('PENDING','RUNNING')"""))
    from .medical_advanced_runtime import initialize as initialize_advanced
    initialize_advanced(engine)
    from .medical_on_demand import initialize as initialize_analyze_now
    initialize_analyze_now(engine)
    from .medical_official_news import initialize as initialize_official_news
    initialize_official_news(engine)


def _read(engine, run_id):
    if not RUN.fullmatch(str(run_id)):
        raise ValueError("Invalid medical research run identifier")
    with engine.connect() as c:
        row = c.execute(text("SELECT * FROM medical_continuous_runs WHERE run_id=:id"), {"id": run_id}).mappings().first()
    if row is None:
        raise LookupError("Saved medical research run not found")
    return dict(row)


def snapshot(engine, nct, run_id):
    check_nct(nct)
    run = _read(engine, run_id)
    if run["nct_id"] != nct:
        raise LookupError("Run does not belong to this NCT")
    with engine.connect() as c:
        entries = list(c.execute(text("""SELECT stage_index,state,document,finished_at
          FROM medical_continuous_stages WHERE run_id=:id ORDER BY stage_index"""), {"id": run_id}).mappings())
    completed = {int(x["stage_index"]): x for x in entries}
    stages = [{"number": i + 1, "title": name,
               "state": completed[i]["state"] if i in completed else
                        ("RUNNING" if run["status"] == "RUNNING" and i == run["stage_index"] else "QUEUED"),
               "details": json.loads(completed[i]["document"]) if i in completed else None,
               "finishedAt": completed[i]["finished_at"] if i in completed else None}
              for i, name in enumerate(STAGES)]
    return {"runId": run_id, "nct": nct, "status": run["status"],
            "stageNumber": min(12, int(run["stage_index"]) + 1),
            "completedStages": len(completed), "totalStages": len(STAGES),
            "stopRequested": bool(run["stop_requested"]),
            "startedAt": run["created_at"], "updatedAt": run["updated_at"],
            "stages": stages,
            "decision": "ABSTAIN", "approvalProbability": None,
            "note": "Stage completion means a source check ran, not that a clinical/FDA assessment passed."}


def latest(engine, nct):
    check_nct(nct)
    with engine.connect() as c:
        run_id = c.execute(text("""SELECT run_id FROM medical_continuous_runs
            WHERE nct_id=:nct ORDER BY created_at DESC,run_id DESC LIMIT 1"""), {"nct": nct}).scalar()
    if not run_id:
        raise LookupError("No saved continuous medical research run")
    return snapshot(engine, nct, run_id)


def create(engine, nct, request_key, *, submit=True):
    check_nct(nct)
    if not isinstance(request_key, str) or not RUN.fullmatch(request_key):
        raise ValueError("UUID request key required")
    with _IN_PROCESS:
        with engine.begin() as c:
            existing = c.execute(text("SELECT run_id,nct_id FROM medical_continuous_runs WHERE request_key=:key"),
                                 {"key": request_key}).first()
            if existing:
                if existing[1] != nct:
                    raise ValueError("Request key already belongs to another trial")
                return snapshot(engine, nct, existing[0])
            active = c.execute(text("""SELECT run_id FROM medical_continuous_runs WHERE nct_id=:nct
                 AND status IN ('PENDING','RUNNING') ORDER BY created_at DESC LIMIT 1"""), {"nct": nct}).scalar()
            if active:
                return snapshot(engine, nct, active)
            run_id = str(uuid.uuid4())
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES(:id,:key,:nct,'PENDING',0,:time,:time,FALSE)"""),
                {"id": run_id, "key": request_key, "nct": nct, "time": now()})
    if submit:
        _POOL.submit(worker, engine, run_id)
    return snapshot(engine, nct, run_id)


def stop(engine, nct, run_id):
    check_nct(nct)
    run = _read(engine, run_id)
    if run["nct_id"] != nct:
        raise LookupError("Run identity mismatch")
    with engine.begin() as c:
        c.execute(text("""UPDATE medical_continuous_runs SET stop_requested=TRUE,updated_at=:time
           WHERE run_id=:id AND status IN ('PENDING','RUNNING')"""), {"time": now(), "id": run_id})
    return snapshot(engine, nct, run_id)


def resume(engine, nct, run_id):
    check_nct(nct)
    with _IN_PROCESS:
        run = _read(engine, run_id)
        if run["nct_id"] != nct:
            raise LookupError("Run identity mismatch")
        if run["status"] != "STOPPED":
            return snapshot(engine, nct, run_id)
        with engine.begin() as c:
            c.execute(text("""UPDATE medical_continuous_runs
               SET status='PENDING',stop_requested=FALSE,updated_at=:time WHERE run_id=:id"""),
               {"time": now(), "id": run_id})
    _POOL.submit(worker, engine, run_id)
    return snapshot(engine, nct, run_id)


def source_json(url, *, limit=2000000):
    req = Request(url, headers={"Accept": "application/json", "User-Agent": "PDUFA-IndependentMedicalResearch/1.0"})
    with urlopen(req, timeout=18) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        # NCBI E-utilities sometimes labels JSON results as text/plain.
        # Only trust that type from the fixed E-utilities API host.
        ncbi_json = url.startswith("https://eutils.ncbi.nlm.nih.gov/") and "text/plain" in content_type
        if response.status != 200 or ("json" not in content_type and not ncbi_json):
            raise ValueError("Unexpected source response")
        raw = response.read(limit + 1)
        if len(raw) > limit:
            raise ValueError("Source exceeded maximum permitted size")
        return json.loads(raw)


def registry(nct):
    obj = source_json("https://clinicaltrials.gov/api/v2/studies/" + nct, limit=6000000)
    if obj.get("protocolSection", {}).get("identificationModule", {}).get("nctId") != nct:
        raise ValueError("ClinicalTrials.gov identity mismatch")
    return obj


def pm_search(term):
    """Collect original PubMed article leads. IDs are not clinical conclusions."""
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + urlencode(
        {"db": "pubmed", "term": term[:250], "retmax": 5, "retmode": "json"})
    obj = source_json(url)
    ids = [p for p in obj.get("esearchresult", {}).get("idlist", []) if str(p).isdigit()][:5]
    return [{"pmid": x, "url": "https://pubmed.ncbi.nlm.nih.gov/" + x + "/"} for x in ids]



def application_roster_status():
    """Verify packaged identity mapping, not the FDA's current application status."""
    expected = set(roster())
    data = json.loads(APPLICATIONS.read_text(encoding="utf-8"))
    rows = data.get("records", [])
    if data.get("schemaVersion") != 1 or data.get("asOf") != "2026-11-07" or not isinstance(rows, list):
        raise ValueError("Application map source version not recognized")
    by_nct = {row.get("nct"): row for row in rows if isinstance(row, dict)}
    if len(by_nct) != len(rows) or not set(by_nct).issubset(expected):
        raise ValueError("Application map has duplicate or foreign FOCUS identities")
    # Preserve source-linked older study research as an explicitly incomplete
    # subset of the current roster; never assert independent verification.
    missing = sorted(expected - set(by_nct))
    ids = set()
    ambiguous = []
    for nct, row in by_nct.items():
        apps = row.get("candidateApplications", [])
        if not isinstance(apps, list) or not apps or row.get("designations") != []:
            raise ValueError("Original-source application identities incomplete or designation claims unverified")
        indications = set()
        drugs = set()
        for app in apps:
            if not isinstance(app, dict) or not str(app.get("sourceUrl", "")).startswith("https://"):
                raise ValueError("An FDA application lead lacks a dated secure source")
            if not isinstance(app.get("sourceDate"), str) or app["sourceDate"] > data["asOf"]:
                raise ValueError("An FDA application lead is future dated or undated")
            if not str(app.get("cycleId", "")):
                raise ValueError("Application cycle identity absent")
            ids.add(app["cycleId"])
            indications.add(app.get("indication"))
            drugs.add(app.get("drug"))
        if len(indications) != 1 or len(drugs) != 1:
            ambiguous.append(nct)
            if row.get("indication") or row.get("drug"):
                raise ValueError("Shared study attributed to a specific unverified application")
        elif row.get("indication") not in indications or row.get("drug") not in drugs:
            raise ValueError("Study-level labels do not match exact application records")
    return {"state": "VALID" if not missing else "PARTIAL", "asOf": data["asOf"],
            "focusNctCount":len(expected),"coveredNctCount":len(by_nct),
            "missingNctIds":missing,
            "applicationCycleCount":len(ids),
            "sharedIndicationUnresolvedNcts":ambiguous,
            "regulatorySourceType":"SPONSOR_SEC_RECONSTRUCTION",
            "fdaApplicationStatusVerified":False,
            "clinicalResearchSignoff":False}



def program_record(nct):
    """Dated source-linked application context; not FDA-confirmed status.

    The Docker image intentionally carries its own exact-NCT snapshot.
    A shared study supporting multiple indications must not silently inherit
    the drug/indication from an arbitrary application.
    """
    check_nct(nct)
    try:
        data = json.loads(APPLICATIONS.read_text(encoding="utf-8"))
        if data.get("schemaVersion") != 1 or data.get("asOf") != "2026-11-07":
            return None
        row = next((r for r in data.get("records", []) if r.get("nct") == nct), None)
        if not row or not row.get("candidateApplications"):
            return None
        if not isinstance(row.get("designations"), list):
            return None
        return row
    except (OSError, ValueError, TypeError):
        return None


def process_stage(index, nct, prior=None):
    """Source collection and gaps, not expert medical signoff or inferred FDA decisions."""
    p = registry(nct) if index in (0, 1, 7, 8) else None
    reg = p.get("protocolSection", {}) if p else {}
    results = p.get("resultsSection", {}) if p else {}
    item = check_nct(nct)
    label = item.get("ticker", "")
    source = "https://clinicaltrials.gov/study/" + nct
    identity = reg.get("identificationModule", {})
    design = reg.get("designModule", {})
    outcomes = reg.get("outcomesModule", {})
    indication = program_record(nct)
    if index == 0:
        return "SOURCE_RECORDED", {"source": source, "nct": nct,
           "title": identity.get("briefTitle"), "phases": design.get("phases", []),
           "sponsor": reg.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
           "conditions": reg.get("conditionsModule", {}).get("conditions", []),
           "caution": "The registered phase is not evidence of FDA application acceptance."}
    if index == 1:
        out = results.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
        return ("SOURCE_RECORDED" if out else "EVIDENCE_GAP"), {
           "source": source, "outcomesPosted": len(out), "hasResults": bool(results),
           "primaryEndpoints": [x.get("measure") for x in outcomes.get("primaryOutcomes", []) if isinstance(x, dict)][:20],
           "caution": "Posted outcomes are sponsor-reported, not independently adjudicated."}
    if index == 2:
        return "LEADS_ONLY", {"source": item.get("regulatoryUrl", ""), "ticker": label,
          "company": item.get("company", ""), "issuerEvidenceUrl": item.get("regulatoryUrl", ""),
          "trialResultsUrl": item.get("resultsUrl", ""),
          "gap": "Issuer and SEC full text, prior filings and current FDA communications require independent document examination."}
    if index == 3:
        term = '"' + nct + '"'
        leads = pm_search(term)
        return ("LEADS_ONLY" if leads else "EVIDENCE_GAP"), {"source": "https://pubmed.ncbi.nlm.nih.gov/",
            "query": term, "publications": leads,
            "gap": "Full text, supplementary datasets and contradictions are not assessed by an index lookup."}
    if index == 4:
        claims = indication.get("designations", []) if indication else []
        return ("LEADS_ONLY" if claims else "EVIDENCE_GAP"), {
           "source": "https://www.fda.gov/", "savedDesignationClaims": claims[:18],
           "gap": "Designations, review classifications, pathways and source dates require case-specific FDA confirmation. They do not establish approval likelihood."}
    if index == 5:
        disease = indication.get("indication", "") if indication else ""
        term = (disease or " ".join(item.get("company", "").split()[:3])) + " natural history"
        leads = pm_search(term)
        return ("LEADS_ONLY" if leads else "EVIDENCE_GAP"), {"source": "https://pubmed.ncbi.nlm.nih.gov/",
            "indication": disease or "Not reconciled", "query": term, "publicationLeads": leads,
            "gap": "Disease biology and patient-important outcomes not independently assessed."}
    if index == 6:
        drug = indication.get("drug", "") if indication else ""
        disease = indication.get("indication", "") if indication else ""
        term = " ".join(filter(None, [drug, disease, "clinical trial"]))
        leads = pm_search(term or nct)
        return ("LEADS_ONLY" if leads else "EVIDENCE_GAP"), {"source": "https://pubmed.ncbi.nlm.nih.gov/",
            "drug": drug or "Not reconciled", "indication": disease or "Not reconciled",
            "publicationLeads": leads,
            "gap": "A disease-subspecialist style interpretation is not completed merely by retrieving literature."}
    if index == 7:
        reported = results.get("outcomeMeasuresModule", {}).get("outcomeMeasures", [])
        comparison = [a for o in reported if isinstance(o, dict) for a in o.get("analyses", []) if isinstance(a, dict)]
        return ("SOURCE_RECORDED" if comparison else "EVIDENCE_GAP"), {
          "source": source, "reportedComparisons": len(comparison),
          "examples": [{"reportedP": a.get("pValue"), "method": a.get("statisticalMethod"),
                        "estimate": a.get("paramValue")} for a in comparison[:12]],
          "gap": "SAP prespecification, multiplicity, sensitivity analyses and FDA acceptance remain unverified."}
    if index == 8:
        a = results.get("adverseEventsModule", {})
        groups = a.get("eventGroups", [])
        return ("SOURCE_RECORDED" if groups else "EVIDENCE_GAP"), {
           "source": source, "reportedGroups": len(groups),
           "reportedSeriousEventTerms": len(a.get("seriousEvents", [])),
           "sample": [{"arm": g.get("title"), "seriousAffected": g.get("seriousNumAffected"),
                      "seriousAtRisk": g.get("seriousNumAtRisk")} for g in groups[:12] if isinstance(g, dict)],
           "gap": "Individual causality, integrated exposure, clinical significance and long-term risks remain to be assessed."}
    if index == 9:
        return "EVIDENCE_GAP", {"source": "https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations",
          "gap": "Exact manufacturer, facility identifiers, confidential CMC findings and preapproval inspection outcomes are not established.",
          "caution": "Absence of a public inspection finding does not establish CMC readiness."}
    if index == 10:
        return "LEADS_ONLY", {"source": "https://www.accessdata.fda.gov/scripts/cder/daf/",
          "indication": indication.get("indication") if indication else "Not reconciled",
          "gap": "Comparable FDA decisions and any prior CRLs require original approval packages, reviewer statements and exact application matching."}
    if index == 11:
        return "EVIDENCE_GAP", {"source": source, "decision": "ABSTAIN",
           "outcome": "INSUFFICIENT_EVIDENCE", "clinicalSignoff": False,
           "gap": "Public leads and registry facts do not complete the 40 assessments × 20 levels, FDA/CMC review or decision calibration.",
           "note": "A collected source is not a passed medical assessment or an FDA approval probability."}
    raise ValueError("Invalid stage index")


def _claim(engine, run_id):
    """One server worker per run, including across backend instances."""
    if engine.dialect.name != "postgresql":
        return None, True
    conn = engine.connect()
    key = int(hashlib.sha256(("medical:" + run_id).encode()).hexdigest()[:14], 16)
    acquired = bool(conn.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key}).scalar())
    if not acquired:
        conn.close()
        return None, False
    return (conn, key), True


def worker(engine, run_id, *, step=process_stage):
    lock, acquired = _claim(engine, run_id)
    if not acquired:
        return
    try:
        while True:
            run = _read(engine, run_id)
            if run["status"] in END:
                return
            if run["stop_requested"]:
                with engine.begin() as c:
                    c.execute(text("""UPDATE medical_continuous_runs SET status='STOPPED',updated_at=:t
                        WHERE run_id=:id"""), {"t": now(), "id": run_id})
                return
            index = int(run["stage_index"])
            if index >= len(STAGES):
                # The history report and COMPLETE status commit atomically:
                # no completed run without a corresponding immutable source
                # revision and independent abstention/certainty disposition.
                from .medical_advanced_runtime import record_revision
                with engine.begin() as c:
                    record_revision(c, run_id, run["nct_id"])
                    c.execute(text("""UPDATE medical_continuous_runs SET status='COMPLETE',updated_at=:t
                        WHERE run_id=:id"""), {"t": now(), "id": run_id})
                return
            with engine.begin() as c:
                c.execute(text("UPDATE medical_continuous_runs SET status='RUNNING',updated_at=:t WHERE run_id=:id"),
                          {"t": now(), "id": run_id})
            try:
                state, document = step(index, run["nct_id"])
                if state not in STAGE_DONE:
                    raise ValueError("Invalid stage evidence disposition")
                document = {**document, "stage": STAGES[index],
                            "review": "SOURCE_COLLECTION_ONLY", "scientificSignoff": False}
                if len(json.dumps(document)) > 120000:
                    raise ValueError("Stage evidence exceeds size limit")
            except Exception as exc:
                LOG.warning("medical source stage failed: stage=%s error_type=%s", index + 1, type(exc).__name__)
                state = "SOURCE_UNAVAILABLE"
                document = {"stage": STAGES[index], "review": "SOURCE_COLLECTION_ONLY",
                   "scientificSignoff": False, "errorType": type(exc).__name__,
                   "gap": "Source retrieval or validation failed. This does not establish clinical failure."}
            with engine.begin() as c:
                c.execute(text("""INSERT INTO medical_continuous_stages(run_id,stage_index,state,document,finished_at)
                   VALUES(:id,:i,:state,:doc,:t)
                   ON CONFLICT(run_id,stage_index) DO NOTHING"""),
                   {"id": run_id, "i": index, "state": state, "doc": json.dumps(document, allow_nan=False), "t": now()})
                c.execute(text("""UPDATE medical_continuous_runs SET stage_index=:next,updated_at=:t
                   WHERE run_id=:id AND stage_index=:i"""),
                   {"next": index + 1, "t": now(), "id": run_id, "i": index})
            if index == 0 and state != "SOURCE_RECORDED":
                with engine.begin() as c:
                    c.execute(text("""UPDATE medical_continuous_runs SET status='FAILED',updated_at=:t
                         WHERE run_id=:id"""), {"t": now(), "id": run_id})
                return
    finally:
        if lock:
            connection, key = lock
            try:
                connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})
                connection.commit()
            finally:
                connection.close()


def start(engine):
    initialize(engine)
    with engine.connect() as c:
        # The dated FOCUS roster currently has 29 NCTs. A hard 25-run cap left
        # the remaining jobs stranded after a service restart. The worker pool
        # bounds concurrency; enqueue every unfinished durable run instead.
        ids = list(c.execute(text("""SELECT run_id FROM medical_continuous_runs
            WHERE status IN ('PENDING','RUNNING') ORDER BY created_at,run_id""")).scalars())
    for run_id in ids:
        _POOL.submit(worker, engine, run_id)
    from .medical_advanced_runtime import start_watch
    start_watch(engine)


class StartPayload(BaseModel):
    request_key: str = Field(min_length=36, max_length=36)


def install_routes(app, engine_provider, require_key, require_storage):
    router = APIRouter(prefix="/api/medical-continuous",
                       dependencies=[Depends(require_key), Depends(require_storage)])

    def fail(exc):
        if isinstance(exc, LookupError):
            raise HTTPException(404, "Saved medical research run not found")
        if isinstance(exc, ValueError):
            raise HTTPException(422, "Invalid trial identity or request key")
        LOG.error("Medical continuous endpoint error_type=%s", type(exc).__name__)
        raise HTTPException(503, "Persistent medical stage storage unavailable")

    @router.post("/{nct}/runs")
    def create_job(nct: str, payload: StartPayload):
        try:
            return create(engine_provider(), nct, payload.request_key)
        except Exception as exc:
            fail(exc)

    @router.get("/{nct}/history")
    def read_history(nct: str):
        from .medical_advanced_runtime import list_revisions
        try:
            return list_revisions(engine_provider(), nct)
        except Exception as exc:
            fail(exc)

    @router.get("/{nct}/runs/latest")
    def read_latest(nct: str):
        try:
            return latest(engine_provider(), nct)
        except Exception as exc:
            fail(exc)

    @router.get("/{nct}/runs/{run_id}")
    def read_job(nct: str, run_id: str):
        try:
            return snapshot(engine_provider(), nct, run_id)
        except Exception as exc:
            fail(exc)

    @router.post("/{nct}/runs/{run_id}/stop")
    def stop_job(nct: str, run_id: str):
        try:
            return stop(engine_provider(), nct, run_id)
        except Exception as exc:
            fail(exc)

    @router.post("/{nct}/runs/{run_id}/resume")
    def resume_job(nct: str, run_id: str):
        try:
            return resume(engine_provider(), nct, run_id)
        except Exception as exc:
            fail(exc)

    app.include_router(router)
