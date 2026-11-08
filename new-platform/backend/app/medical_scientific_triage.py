"""Stage 4: reproducible scientific evidence triage, not clinical-grade adjudication.

Read the 12 immutable source stages, map them to the 40 x 20 review questions,
and append ONE reproducible research-triage snapshot per source/catalog revision.
Raw primary-source existence is not proof of efficacy, safety or FDA success.
Never create reviewer grades, adverse-event findings or regulatory probabilities.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from . import medical_assessment_ledger as ledger
from . import medical_phase_matrix as phase_matrix

LOG = logging.getLogger(__name__)
VERSION = "SOURCE_TRIAGE_V1"
NCT = re.compile(r"^NCT[0-9]{8}$")
YES = {"true", "1", "yes"}

# Precise, static source lead routes for all 40 assessments. All stages remain
# eligible for a method-level review; this index only suggests where to look.
ASSESSMENT_STAGE_LEADS = {
    "1.1": (5, 6, 3), "1.2": (5, 3, 0), "1.3": (5, 3, 1),
    "1.4": (5, 10, 3), "1.5": (0, 5, 1),
    "2.1": (6, 3, 2), "2.2": (6, 3, 2), "2.3": (6, 1, 3),
    "2.4": (6, 3, 8), "2.5": (6, 3, 8),
    "3.1": (6, 3, 1), "3.2": (6, 1, 7), "3.3": (6, 8, 1),
    "3.4": (6, 8, 3), "3.5": (6, 3, 1),
    "4.1": (0, 1, 7), "4.2": (0, 1, 7), "4.3": (7, 1, 0),
    "4.4": (0, 1, 7), "4.5": (0, 8, 1),
    "5.1": (1, 7, 6), "5.2": (1, 7, 6), "5.3": (8, 1, 3),
    "5.4": (1, 7, 8), "5.5": (8, 1, 3),
    "6.1": (10, 3, 1), "6.2": (3, 10, 1), "6.3": (10, 1, 3),
    "6.4": (10, 4, 3), "6.5": (10, 3, 6),
    "7.1": (4, 10, 2), "7.2": (4, 10, 2), "7.3": (4, 9, 2),
    "7.4": (4, 9, 10), "7.5": (4, 10, 1),
    "8.1": (0, 1, 7, 8), "8.2": (3, 7, 8, 1),
    "8.3": (1, 7, 6), "8.4": (1, 7, 8, 9),
    "8.5": tuple(range(12)),
}

# A science method changes the investigation lens, not the underlying
# truthfulness of an issuer release or unadjudicated registry record.
METHOD_STAGE_HINTS = {
    1: (0, 2, 3), 2: (5, 6), 3: (5, 6), 4: (1, 7, 8),
    5: (1, 7, 8), 6: (5, 6, 7), 7: (4, 9, 10), 8: (1, 7, 8),
    9: (1, 7), 10: (5, 6), 11: (3, 7, 8), 12: (1, 7, 8),
    13: (2, 4, 9, 10), 14: (3, 5, 6), 15: (0, 1, 7),
    16: (2, 4, 10), 17: (5, 6, 3), 18: (1, 7, 8),
    19: (0, 1, 7, 8), 20: tuple(range(12)),
}
RECORD_STAGES = frozenset((1, 7, 8))
CLASSES = ("SOURCE_RECORD_UNADJUDICATED", "RESEARCH_LEADS_ONLY",
           "IDENTITY_ONLY_NO_CLINICAL_DATA", "SOURCE_GAP", "NO_MATCHING_SAVED_SOURCE")


def _digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _exact_catalog() -> dict:
    c = phase_matrix.catalog()
    ids = {a["id"] for a in c["assessments"]}
    if ids != set(ASSESSMENT_STAGE_LEADS) or set(METHOD_STAGE_HINTS) != set(range(1, 21)):
        raise RuntimeError("Scientific source map does not cover 40 assessments and 20 methods")
    if any(not stages or any(type(i) is not int or i not in range(12) for i in stages)
           for stages in list(ASSESSMENT_STAGE_LEADS.values()) + list(METHOD_STAGE_HINTS.values())):
        raise RuntimeError("Scientific source map has invalid stage indices")
    return c


def initialize(engine, *, test_only=False):
    """New table only. No writes to existing research, review or phase ledgers."""
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("Stage 4 snapshots require durable PostgreSQL")
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE IF NOT EXISTS medical_scientific_triage_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            nct_id TEXT NOT NULL REFERENCES medical_assessment_trial_roster(nct_id),
            source_run_id TEXT NOT NULL REFERENCES medical_continuous_runs(run_id),
            algorithm_version TEXT NOT NULL,
            source_input_sha256 TEXT NOT NULL,
            catalog_sha256 TEXT NOT NULL,
            output_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(nct_id,source_run_id,algorithm_version,source_input_sha256,catalog_sha256))"""))
        c.execute(text("""CREATE INDEX IF NOT EXISTS medical_scientific_triage_nct_history
            ON medical_scientific_triage_snapshots(nct_id,created_at)"""))


def _saved_stages(engine, nct, run_id):
    with engine.connect() as c:
        rows = list(c.execute(text("""SELECT s.stage_index,s.state,s.document,s.finished_at
            FROM medical_continuous_stages s
            JOIN medical_continuous_runs r ON r.run_id=s.run_id
            WHERE r.nct_id=:nct AND r.run_id=:run AND r.status='COMPLETE'
            ORDER BY s.stage_index"""), {"nct":nct, "run":run_id}).mappings())
    if len(rows) != 12 or [int(x["stage_index"]) for x in rows] != list(range(12)):
        raise RuntimeError("Exactly 12 immutable completed research stages are required")
    return [dict(row) for row in rows]


def _safe_url(value):
    if not isinstance(value, str) or not value.startswith("https://"):
        return None
    url = urlsplit(value)
    if not url.hostname or url.username or url.password:
        return None
    return value[:2048]


def _public_source_facts(stage_index, document):
    """Only original, bounded source-count facts; no clinical interpretation."""
    if stage_index == 0:
        return {"registryPhases": document.get("phases", [])[:4]
                if isinstance(document.get("phases"), list) else []}
    if stage_index == 1:
        return {"registryOutcomeGroupsPosted": document.get("outcomesPosted", 0),
                "resultsSectionFound": bool(document.get("hasResults", False))}
    if stage_index == 7:
        return {"reportedComparisons": document.get("reportedComparisons", 0)}
    if stage_index == 8:
        return {"reportedSafetyGroups": document.get("reportedGroups", 0),
                "reportedSeriousEventTerms": document.get("reportedSeriousEventTerms", 0)}
    if stage_index in (3, 5, 6):
        leads = document.get("publications", document.get("publicationLeads", []))
        return {"bibliographicLeads":len(leads) if isinstance(leads, list) else 0}
    return {}


def _lead_from_stage(stage):
    i = int(stage["stage_index"])
    document = json.loads(stage["document"])
    if not isinstance(document, dict):
        raise RuntimeError("Research stage document must be a structured source record")
    return {
        "stageNumber":i + 1,
        "stageIndex":i,
        "state":stage["state"],
        "originalSourceUrl":_safe_url(document.get("source")),
        "documentSha256":hashlib.sha256(stage["document"].encode("utf-8")).hexdigest(),
        "sourceFacts":_public_source_facts(i, document),
        "requiresIndependentReview":True,
        "evidenceGap":str(document.get("gap", ""))[:700] or None,
    }


def _method_source_class(leads):
    # Identity-only stage 0 is not a biological, clinical, safety or FDA finding.
    if any(r["stageIndex"] in RECORD_STAGES and r["state"] == "SOURCE_RECORDED"
           for r in leads):
        return "SOURCE_RECORD_UNADJUDICATED"
    if any(r["state"] == "LEADS_ONLY" for r in leads):
        return "RESEARCH_LEADS_ONLY"
    if any(r["stageIndex"] == 0 and r["state"] == "SOURCE_RECORDED"
           for r in leads):
        return "IDENTITY_ONLY_NO_CLINICAL_DATA"
    if any(r["state"] in ("EVIDENCE_GAP", "SOURCE_RECORDED") for r in leads):
        return "SOURCE_GAP"
    return "NO_MATCHING_SAVED_SOURCE"


def analyze(engine, nct: str) -> dict:
    """Read only; deterministic 800-position source triage on 1 original NCT."""
    if not isinstance(nct, str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT required")
    from . import medical_continuous as core
    core.check_nct(nct)
    c = _exact_catalog()
    projection = phase_matrix.matrix(engine, nct)
    run_id = projection["sourceRunId"]
    saved = _saved_stages(engine, nct, run_id)
    leads = {int(row["stage_index"]): _lead_from_stage(row) for row in saved}
    counts = {name:0 for name in CLASSES}
    assessments = []
    for assessment in projection["assessments"]:
        aid = assessment["assessmentId"]
        stage_set = ASSESSMENT_STAGE_LEADS[aid]
        methods = []
        for method in assessment["methods"]:
            mid = method["methodIndex"]
            # Prefer the intersection; if absent, assess the whole
            # disease/assessment source route without pretending that
            # a method has its own completed scientific evidence.
            indices = [i for i in stage_set if i in METHOD_STAGE_HINTS[mid]] or list(stage_set)
            records = [leads[i] for i in indices]
            classification = _method_source_class(records)
            counts[classification] += 1
            methods.append({
                "methodIndex":mid,
                "methodId":method["id"],
                "investigationPriorityRank":method["priorityRank"],
                "investigationPriorityTier":method["priorityTier"],
                "phaseApplicability":method["phaseApplicability"],
                "sourceClassification":classification,
                "sourceLeads":records,
                "sourceCount":len(records),
                "scientificGrade":method["grade"],
                "scientificGradeStatus":method["gradeStatus"],
                "missingRequiredReview":"Independent phase-appropriate source appraisal and contradictory evidence",
                "observedClinicalFinding":None,
            })
        assessments.append({
            "assessmentId":aid, "layerId":assessment["layerId"],
            "title":assessment["label"],
            "objective":assessment["objective"],
            "requiredSources":assessment["requiredSources"],
            "gradeStatus":assessment["gradeStatus"],
            "finalScientificScore":assessment["finalScore"],
            "provisionalScientificScore":assessment["provisionalScore"],
            "methods":methods,
        })
    if sum(counts.values()) != 800 or len(assessments) != 40:
        raise RuntimeError("Every 40 × 20 position must be accounted for")
    return {
        "schema":VERSION, "nct":nct, "sourceRunId":run_id,
        "sourceCompletedAt":projection["sourceCompletedAt"],
        "phase":projection["phase"], "phaseBasis":projection["phaseBasis"],
        "phaseReviewed":projection["phaseBasis"] == "REVIEWER_VERIFIED",
        "priorCompletedPhaseBenchmark":projection["priorCompletedPhaseBenchmark"],
        "sourceStageCount":12,
        "sourceInputSha256":_digest([{"stageIndex":row["stage_index"],
                                      "state":row["state"],"document":row["document"]}
                                     for row in saved]),
        "catalogSha256":_digest(c),
        "assessmentCount":40, "methodPositions":800,
        "sourceClassCounts":counts,
        "methodsWithIndependentGrade":sum(x["scoredMethods"] for x in projection["assessments"]),
        "methodsMarkedNotApplicable":sum(x["excludedMethods"] for x in projection["assessments"]),
        "scientificSignoff":False,
        "fdaPredictions":{"APPROVAL":"ABSTAIN","CRL":"ABSTAIN",
                          "REVIEW_DELAY":"ABSTAIN"},
        "certainty":"NOT_VALIDATED",
        "phaseRiskQuestions":projection["phaseRiskQuestions"],
        "observedClinicalRiskFindings":[],
        "priorityPolicy":"INVESTIGATION_ORDER_NOT_AN_OBSERVED_RISK",
        "assessments":assessments,
        "note":"Source counts and recorded primary-source leads do NOT establish "
               "clinical trial success, adverse drug effects, FDA outcome or a grade.",
    }


def persist(engine, nct: str, *, test_only=False) -> dict:
    """Idempotent append-only snapshot; no reviewer/phase/source ledger edits."""
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("Scientific triage snapshots require durable PostgreSQL")
    report = analyze(engine, nct)
    snapshot_id = str(uuid.uuid4())
    stamp = _now()
    with engine.begin() as c:
        c.execute(text("""INSERT INTO medical_scientific_triage_snapshots
            (snapshot_id,nct_id,source_run_id,algorithm_version,source_input_sha256,
             catalog_sha256,output_json,created_at)
            VALUES(:id,:nct,:run,:version,:source,:catalog,:output,:stamp)
            ON CONFLICT(nct_id,source_run_id,algorithm_version,
                        source_input_sha256,catalog_sha256) DO NOTHING"""),
            {"id":snapshot_id, "nct":nct, "run":report["sourceRunId"],
             "version":VERSION, "source":report["sourceInputSha256"],
             "catalog":report["catalogSha256"],
             "output":json.dumps(report,sort_keys=True,separators=(",",":")),
             "stamp":stamp})
    return latest(engine, nct)


def latest(engine, nct: str) -> dict:
    if not isinstance(nct,str) or not NCT.fullmatch(nct):
        raise ValueError("Exact NCT required")
    from . import medical_continuous as core
    core.check_nct(nct)
    with engine.connect() as c:
        row = c.execute(text("""SELECT snapshot_id,output_json,created_at
           FROM medical_scientific_triage_snapshots
           WHERE nct_id=:nct ORDER BY created_at DESC,snapshot_id DESC LIMIT 1"""),
           {"nct":nct}).mappings().first()
    if row is None:
        raise LookupError("No persisted scientific source triage for this exact trial")
    return {"snapshotId":row["snapshot_id"],"createdAt":row["created_at"],
            **json.loads(row["output_json"])}


def history(engine, nct: str) -> dict:
    from . import medical_continuous as core
    core.check_nct(nct)
    with engine.connect() as c:
        items = list(c.execute(text("""SELECT snapshot_id,source_run_id,
            algorithm_version,source_input_sha256,catalog_sha256,created_at
            FROM medical_scientific_triage_snapshots WHERE nct_id=:nct
            ORDER BY created_at,snapshot_id"""),{"nct":nct}).mappings())
    return {"nct":nct, "total":len(items), "records":[dict(row) for row in items]}


def run_canary(engine) -> dict | None:
    """One exact original canary only; no global all-trial analysis."""
    if os.getenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_CANARY_AUTORUN", "").lower() not in YES:
        return None
    if os.getenv("PDUFA_MEDICAL_BATCH_AUTORUN", "").lower() in YES:
        raise RuntimeError("Scientific triage cannot overlap active research batch rollout")
    nct = os.getenv("PDUFA_ANALYZE_NOW_CANARY_NCT", "NCT06081894")
    if nct != "NCT06081894":
        raise RuntimeError("This first scientific triage is limited to the original NCT canary")
    report = persist(engine, nct)
    LOG.warning("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE status=PASS nct=%s "
                "stages=%d assessments=%d methods=%d sourceRecord=%d "
                "leadsOnly=%d sourceGaps=%d independentGrades=%d "
                "phaseReviewed=%s scientificSignoff=False "
                "prediction=ABSTAIN certainty=NOT_VALIDATED",
                nct,report["sourceStageCount"],report["assessmentCount"],
                report["methodPositions"],
                report["sourceClassCounts"]["SOURCE_RECORD_UNADJUDICATED"],
                report["sourceClassCounts"]["RESEARCH_LEADS_ONLY"],
                report["sourceClassCounts"]["SOURCE_GAP"],
                report["methodsWithIndependentGrade"],report["phaseReviewed"])
    return report



CAMPAIGN = re.compile(r"^[A-Za-z0-9_-]{8,72}$")


def requested_batch() -> tuple[str,tuple[str,...]] | None:
    """Explicit 1–3 unique FOCUS NCTs. The original canary never joins a tail."""
    if os.getenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_AUTORUN", "").lower() not in YES:
        return None
    campaign = os.getenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_CAMPAIGN", "")
    raw = os.getenv("PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH_NCTS", "")
    ncts = tuple(x.strip() for x in raw.split(","))
    if (not CAMPAIGN.fullmatch(campaign) or not 1 <= len(ncts) <= 3
            or len(set(ncts)) != len(ncts)
            or any(not NCT.fullmatch(x) for x in ncts)):
        raise ValueError("Source triage batches require an exact campaign and 1–3 unique NCTs")
    if os.getenv("PDUFA_MEDICAL_BATCH_AUTORUN", "").lower() in YES:
        raise RuntimeError("Source research and scientific triage batches cannot overlap")
    if os.getenv("PDUFA_ANALYZE_NOW_ALL_ENABLED", "").lower() in YES:
        raise RuntimeError("Global all-trial medical analysis must remain disabled")
    if "NCT06081894" in ncts:
        raise ValueError("Original completed canary must not be rerun as a tail batch")
    from . import medical_continuous as core
    roster = core.roster()
    if any(nct not in roster for nct in ncts):
        raise ValueError("Every selected exact NCT must belong to the dated FOCUS roster")
    return campaign, ncts


def run_batch(engine, *, test_only=False) -> list[dict]:
    """Preflight EVERY trial before appending; preserve source/grade ledgers."""
    selected = requested_batch()
    if selected is None:
        return []
    campaign, ncts = selected
    if engine.dialect.name != "postgresql" and not test_only:
        raise RuntimeError("Controlled research triage tail requires durable PostgreSQL")
    # No table writes before every source/assessment projection checks out.
    prepared = {nct: analyze(engine, nct) for nct in ncts}
    if any(x["methodPositions"] != 800 or sum(x["sourceClassCounts"].values()) != 800
           or x["scientificSignoff"] is not False for x in prepared.values()):
        raise RuntimeError("Batch source coverage is not internally consistent")
    results = []
    for nct in ncts:
        row = persist(engine, nct, test_only=test_only)
        original = prepared[nct]
        if (row["sourceInputSha256"] != original["sourceInputSha256"]
                or row["catalogSha256"] != original["catalogSha256"]
                or row["sourceRunId"] != original["sourceRunId"]):
            raise RuntimeError("Source changed between preflight and saved triage readback")
        if (row["methodPositions"] != 800 or row["scientificSignoff"] is not False
                or row["certainty"] != "NOT_VALIDATED"):
            raise RuntimeError("Saved method triage does not match safety contract")
        LOG.warning(
            "PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_TRIAL status=PASS campaign=%s "
            "nct=%s sourceStages=12 methods=800 sourceRecords=%d leadsOnly=%d "
            "sourceGaps=%d independentGrades=%d prediction=ABSTAIN",
            campaign, nct,
            row["sourceClassCounts"]["SOURCE_RECORD_UNADJUDICATED"],
            row["sourceClassCounts"]["RESEARCH_LEADS_ONLY"],
            row["sourceClassCounts"]["SOURCE_GAP"],
            row["methodsWithIndependentGrade"])
        results.append(row)
    LOG.warning(
        "PDUFA_MEDICAL_SCIENTIFIC_TRIAGE_BATCH status=COMPLETE campaign=%s "
        "completed=%d target=%d scientificSignoff=False "
        "prediction=ABSTAIN certainty=NOT_VALIDATED",
        campaign,len(results),len(ncts))
    return results


def install_routes(app, engine_provider, require_key, require_storage):
    router = APIRouter(prefix="/api/internal/medical-scientific-triage",
                       dependencies=[Depends(require_key),Depends(require_storage)])
    @router.get("/{nct}/latest")
    def get_latest(nct: str):
        try:
            return latest(engine_provider(), nct)
        except ValueError:
            raise HTTPException(422,"Exact NCT required")
        except LookupError:
            raise HTTPException(404,"Saved scientific triage not found")
    @router.get("/{nct}/history")
    def get_history(nct: str):
        try:
            return history(engine_provider(), nct)
        except ValueError:
            raise HTTPException(422,"Exact NCT required")
    app.include_router(router)
